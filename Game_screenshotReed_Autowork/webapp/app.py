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
# 确保项目根目录在 sys.path 中，以便从 webapp 启动时能成功导入 `core`
sys.path.insert(0, str(PROJECT_ROOT))

from core import MumuScreenshot, Tapscreen, StartGame, IconDetector, Dailytasks
from threading import Event, Thread, Lock
from core.config import get_config, update_config

app = Flask(__name__, static_folder=str(BASE_DIR / 'static'), static_url_path='', template_folder=str(BASE_DIR / 'templates'))

# 实例化核心工具（复用已有逻辑）
TEMPLATE_PATH = os.path.normpath(str(PROJECT_ROOT / 'templates' / 'button_template.png'))
try:
    detector = IconDetector(TEMPLATE_PATH)
except Exception:
    detector = IconDetector()

screenshot_tool = MumuScreenshot()
tapscreen_tool = Tapscreen()
startgame_tool = StartGame()
dailytasks_tool = Dailytasks()

"""任务控制：支持启动 / 停止 / 暂停 / 恢复。"""
_task_stop_event: Event | None = None
_task_pause_event: Event | None = None
_task_thread: Thread | None = None
_task_lock = Lock()
_task_state = 'idle'  # idle | running | paused | stopped | finished
_task_name = None

def _interruptible_sleep(seconds: float, stop_event: Event | None) -> bool:
    """按切片睡眠；支持停止和暂停。"""
    if seconds <= 0:
        return not (stop_event and stop_event.is_set())
    end = time.time() + seconds
    while time.time() < end:
        if stop_event and stop_event.is_set():
            return False
        
        # 处理暂停：如果 _task_pause_event 被 clear，则 wait() 会阻塞，直到被 set()
        if _task_pause_event:
            _task_pause_event.wait()
        
        # 暂停恢复后再次检查停止信号
        if stop_event and stop_event.is_set():
            return False

        remaining = end - time.time()
        if remaining <= 0:
            break
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
            pass  # 占位（以后如果需要跟踪更多状态可在此处扩展）

@app.route('/task/start', methods=['POST'])
def task_start():
    global _task_thread, _task_stop_event, _task_pause_event, _task_state, _task_name
    data = request.get_json(silent=True) or {}
    task_type = data.get('type')
    if task_type not in ('start_game','dailytasks','combo','debug_sleep','debug_loop'):
        return jsonify({'ok': False, 'error': '未知任务类型'}), 400
    with _task_lock:
        if _task_thread and _task_thread.is_alive():
            return jsonify({'ok': False, 'error': '已有任务在执行'}), 409
        _task_stop_event = Event()
        _task_pause_event = Event()
        _task_pause_event.set()  # 初始状态为运行（非暂停）
        _task_state = 'running'
        _task_name = task_type
        _task_thread = Thread(target=_run_task, args=(task_type, _task_stop_event), daemon=True)
        _task_thread.start()
    return jsonify({'ok': True, 'message': '任务已启动', 'task': task_type})

@app.route('/task/stop', methods=['POST'])
def task_stop():
    global _task_stop_event, _task_state, _task_pause_event
    with _task_lock:
        if not _task_stop_event or _task_state in ('idle', 'finished', 'stopped'):
             # 允许重复停止，但不报错
             pass
        
        # 确保暂停的任务能解除阻塞并退出
        if _task_pause_event:
            _task_pause_event.set()
            
        if _task_stop_event:
            _task_stop_event.set()
            
        _task_state = 'stopped'
    return jsonify({'ok': True, 'message': '停止信号已发送'})

@app.route('/task/pause', methods=['POST'])
def task_pause():
    global _task_pause_event, _task_state
    with _task_lock:
        if not _task_thread or not _task_thread.is_alive():
            return jsonify({'ok': False, 'error': '没有运行中的任务'}), 400
        if _task_pause_event:
            _task_pause_event.clear() # 设置为 False，阻塞 wait()
            _task_state = 'paused'
    return jsonify({'ok': True, 'message': '任务已暂停'})

@app.route('/task/resume', methods=['POST'])
def task_resume():
    global _task_pause_event, _task_state
    with _task_lock:
        if not _task_thread or not _task_thread.is_alive():
            return jsonify({'ok': False, 'error': '没有运行中的任务'}), 400
        if _task_pause_event:
            _task_pause_event.set() # 设置为 True，解除 wait()
            _task_state = 'running'
    return jsonify({'ok': True, 'message': '任务已恢复'})


@app.route('/task/status')
def task_status():
    global _task_thread, _task_state, _task_name, _task_stop_event
    running = _task_thread.is_alive() if _task_thread else False
    return jsonify({'ok': True, 'status': {
        'state': _task_state,
        'task': _task_name,
        'running': running,
        'canStop': running,
        'canPause': running and _task_state == 'running',
        'canResume': running and _task_state == 'paused'
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
    """返回自给定日志索引之后的日志（通过查询参数 `since` 指定）。
    示例：/logs?since=42
    返回 JSON: { ok: True, logs: [...], last: <last_idx> }
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
    # 如果存在构建后的前端文件 static/index.html（例如执行 `npm run build` 后），则直接返回该静态文件。
    static_index = BASE_DIR / 'static' / 'index.html'
    if static_index.exists():
        return send_file(str(static_index))
    # 否则回退到模板渲染（用于开发或通过 CDN 加载前端资源的情况）
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
    # 在本地运行，监听 127.0.0.1:5000
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)

