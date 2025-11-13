import os
import io
import sys
import base64
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
import cv2
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
# Ensure project root is on sys.path so `import core` works when launching from webapp/
sys.path.insert(0, str(PROJECT_ROOT))

from core import MumuScreenshot, Tapscreen, Autorecruitment, StartGame, IconDetector, Dailytasks
from threading import Event, Thread, Lock
from core.config import get_config, update_config

app = Flask(__name__, static_folder=str(BASE_DIR / 'static'), static_url_path='', template_folder=str(BASE_DIR / 'templates'))

# Instantiate core tools (reuse existing logic)
TEMPLATE_PATH = os.path.normpath(str(PROJECT_ROOT / 'templates' / 'button_template.png'))
try:
    detector = IconDetector(TEMPLATE_PATH)
except Exception:
    detector = IconDetector()

screenshot_tool = MumuScreenshot()
tapscreen_tool = Tapscreen()
autorecruit_tool = Autorecruitment()
startgame_tool = StartGame()
dailytasks_tool = Dailytasks()

"""任务控制：仅支持启动 / 停止。"""
_task_stop_event: Event | None = None
_task_thread: Thread | None = None
_task_lock = Lock()
_task_state = 'idle'  # idle | running | stopped | finished
_task_name = None

def _interruptible_sleep(seconds: float, stop_event: Event | None) -> bool:
    """按切片睡眠；支持停止。"""
    if seconds <= 0:
        return not (stop_event and stop_event.is_set())
    end = time.time() + seconds
    while time.time() < end:
        if stop_event and stop_event.is_set():
            return False
        remaining = end - time.time()
        time.sleep(min(0.2, remaining))
    return True

def _run_task(task_type: str, stop_event: Event):
    global _task_state
    try:
        if task_type == 'start_game':
            startgame_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep)
        elif task_type == 'dailytasks':
            dailytasks_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep)
        elif task_type == 'combo':
            startgame_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep)
            if not stop_event.is_set():
                dailytasks_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep)
        elif task_type == 'debug_sleep':
            print('进入 debug_sleep 任务 (用于本地暂停/恢复测试)')
            for i in range(300):  # ~150秒，更易测试暂停/恢复
                if stop_event.is_set():
                    print('debug_sleep: 收到停止')
                    break
                if not _interruptible_sleep(0.5, stop_event):
                    break
                if i % 20 == 0:
                    print(f'debug_sleep 进度 {i}%')
            print('debug_sleep 任务结束')
        elif task_type == 'debug_loop':
            print('进入 debug_loop 任务 (无限循环，需手动停止)')
            iteration = 0
            while not stop_event.is_set():
                if not _interruptible_sleep(0.5, stop_event):
                    break
                iteration += 1
                if iteration % 40 == 0:
                    print(f'debug_loop 心跳 iteration={iteration}')
            if stop_event.is_set():
                print('debug_loop 收到停止信号, 退出')
        _task_state = 'finished' if not stop_event.is_set() else 'stopped'
    except Exception as e:
        print('任务执行异常:', e)
        _task_state = 'stopped'
    finally:
        with _task_lock:
            pass  # placeholder if we later track more

@app.route('/task/start', methods=['POST'])
def task_start():
    global _task_thread, _task_stop_event, _task_state, _task_name
    data = request.get_json(silent=True) or {}
    task_type = data.get('type')
    if task_type not in ('start_game','dailytasks','combo','debug_sleep','debug_loop'):
        return jsonify({'ok': False, 'error': '未知任务类型'}), 400
    with _task_lock:
        if _task_thread and _task_thread.is_alive():
            return jsonify({'ok': False, 'error': '已有任务在执行'}), 409
        _task_stop_event = Event()
        _task_state = 'running'
        _task_name = task_type
        _task_thread = Thread(target=_run_task, args=(task_type, _task_stop_event), daemon=True)
        _task_thread.start()
    return jsonify({'ok': True, 'message': '任务已启动', 'task': task_type})

@app.route('/task/stop', methods=['POST'])
def task_stop():
    global _task_stop_event, _task_state
    with _task_lock:
        if not _task_stop_event or _task_state not in ('running'):
            return jsonify({'ok': False, 'error': '没有运行中的任务'}), 400
        _task_stop_event.set()
        _task_state = 'stopped'
    return jsonify({'ok': True, 'message': '停止信号已发送'})


@app.route('/task/status')
def task_status():
    global _task_thread, _task_state, _task_name, _task_stop_event
    running = _task_thread.is_alive() if _task_thread else False
    return jsonify({'ok': True, 'status': {
        'state': _task_state,
        'task': _task_name,
        'running': running,
        'canStop': running
    }})


def img_to_datauri(img):
    # img: OpenCV BGR numpy array
    _, buf = cv2.imencode('.png', img)
    b64 = base64.b64encode(buf.tobytes()).decode('ascii')
    return f"data:image/png;base64,{b64}"


# --- In-memory logging capture (capture prints and logging into a deque) ---
import logging
import collections
import time
import itertools
import builtins

_log_deque = collections.deque(maxlen=2000)
_log_counter = itertools.count(1)

class InMemoryHandler(logging.Handler):
    def emit(self, record):
        try:
            idx = next(_log_counter)
            msg = self.format(record)
            _log_deque.append({'idx': idx, 'ts': time.time(), 'level': record.levelname, 'msg': msg})
        except Exception:
            pass

# configure a module-level logger
_mem_handler = InMemoryHandler()
_mem_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger = logging.getLogger('webapp')
logger.setLevel(logging.INFO)
logger.addHandler(_mem_handler)

# Hook builtins.print to also log through the logger while preserving original behavior
_orig_print = builtins.print
def _hooked_print(*args, **kwargs):
    try:
        _orig_print(*args, **kwargs)
    except Exception:
        pass
    try:
        text = ' '.join(str(a) for a in args)
        logger.info(text)
    except Exception:
        pass

builtins.print = _hooked_print


@app.route('/logs')
def get_logs():
    """Return logs after `since` index (query param).
    Example: /logs?since=42
    Returns JSON: { ok: True, logs: [...], last: <last_idx> }
    """
    try:
        since = request.args.get('since', default=0, type=int)
        items = [l for l in list(_log_deque) if l['idx'] > since]
        last = items[-1]['idx'] if items else since
        return jsonify({'ok': True, 'logs': items, 'last': int(last)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})



@app.route('/')
def index():
    # If a built frontend exists at static/index.html (after `npm run build`), serve it.
    static_index = BASE_DIR / 'static' / 'index.html'
    if static_index.exists():
        return send_file(str(static_index))
    # Otherwise fall back to the template (development or CDN-based)
    return render_template('index.html')


@app.route('/health')
def health():
    return 'ok'



@app.route('/start_game', methods=['POST'])
def start_game():
    try:
        startgame_tool.run()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/start_dailytasks', methods=['POST'])
def start_dailytasks():
    try:
        dailytasks_tool.run()
        return jsonify({'ok': True})
    except Exception as e:
        import traceback
        print("Dailytasks 执行异常:", traceback.format_exc())
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/config', methods=['GET', 'POST'])
def config_endpoint():
    """Expose configuration for frontend settings page."""
    try:
        if request.method == 'GET':
            return jsonify({'ok': True, 'config': get_config()})

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({'ok': False, 'error': '请求体格式错误，应为 JSON 对象'}), 400

        updated = update_config(payload)
        return jsonify({'ok': True, 'config': updated})
    except Exception as exc:
        logger.exception('配置接口处理失败')
        return jsonify({'ok': False, 'error': str(exc)}), 500


if __name__ == '__main__':
    # Run on localhost:5000
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)

