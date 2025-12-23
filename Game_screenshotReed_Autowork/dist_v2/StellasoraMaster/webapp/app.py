import os
import io
import sys
import base64
import time
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response
import cv2
import numpy as np
import logging

# 禁用 Flask 默认的请求日志输出
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
# 确保项目根目录在 sys.path 中，以便从 webapp 启动时能成功导入 `core`
sys.path.insert(0, str(PROJECT_ROOT))

from core import MumuScreenshot, Tapscreen, StartGame, IconDetector, Dailytasks, TowerClimber
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
# 初始化时从配置加载截图方式
_cfg = get_config()
if 'screenshot_method' in _cfg:
    screenshot_tool.set_method(_cfg['screenshot_method'])

tapscreen_tool = Tapscreen()
startgame_tool = StartGame()
dailytasks_tool = Dailytasks()
towerclimber_tool = TowerClimber()

# === 环境自检代码 (新增) ===
print("="*60)
print(f"【环境检测】正在使用的 Python 解释器: {sys.executable}")
print(f"【环境检测】当前工作目录: {os.getcwd()}")
if "Game_screenshotReed_Autowork" in sys.executable:
    print("⚠️ 警告: 您正在使用内部的旧环境，建议切换到根目录环境！")
else:
    print("✅ 状态: 您正在使用根目录的统一环境。")
print("="*60)
# =========================

def generate_frames():
    """生成器函数，不断获取最新截图并编码为 MJPEG 流"""
    last_time = time.time()
    frame_count = 0
    fps = 0
    target_fps = 65
    frame_interval = 1.0 / target_fps
    
    # 新增：用于去重的变量
    last_frame_obj = None
    
    while True:
        loop_start = time.time()
        try:
            # 使用全局的 screenshot_tool 实例
            frame = screenshot_tool.capture()
            if frame is None:
                time.sleep(0.1)
                continue

            # === 核心修改：FPS 统计逻辑 ===
            # 只有当获取到的 frame 对象发生变化（内存地址不同）时，才视为有效的新帧
            # Scrcpy 模式下，如果有新帧解码，latest_frame 会被替换为新的 numpy 对象
            if frame is not last_frame_obj:
                frame_count += 1
                last_frame_obj = frame
            # ===========================

            # 计算 FPS
            current_time = time.time()
            if current_time - last_time >= 1.0:
                fps = frame_count / (current_time - last_time)
                frame_count = 0
                last_time = current_time

            # 缩放预览图以提高性能 (例如宽度固定为 640)
            # h, w = frame.shape[:2]
            # scale = 640 / w
            # if scale < 1:
            #     preview_frame = cv2.resize(frame, (640, int(h * scale)))
            # else:
            #     preview_frame = frame
            preview_frame = frame.copy() # Copy to avoid modifying original frame if used elsewhere

            # 在画面上绘制 FPS
            # 提示：如果 FPS 为 0，说明画面静止（可能是没操作，也可能是流断了）
            color = (0, 255, 0) if fps > 0 else (0, 0, 255) # 动则绿，静则红
            cv2.putText(preview_frame, f"FPS: {fps:.1f}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            # 将 numpy array 编码为 jpg
            ret, buffer = cv2.imencode('.jpg', preview_frame)
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            # 生成 MJPEG 帧格式
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # 控制帧率上限
            elapsed = time.time() - loop_start
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)

        except Exception as e:
            print(f"Stream error: {e}")
            time.sleep(1)

@app.route('/video_feed')
def video_feed():
    """视频流路由"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stream/start')
def start_stream():
    """手动开启截图流"""
    screenshot_tool.start_stream()
    return jsonify({'ok': True, 'msg': 'Stream started'})

@app.route('/stream/stop')
def stop_stream():
    """手动停止截图流"""
    screenshot_tool.stop_stream()
    return jsonify({'ok': True, 'msg': 'Stream stopped'})

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
def _run_task(task_type: str, stop_event: Event, **kwargs):
    global _task_state
    try:
        if task_type == 'start_game':
            startgame_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep)
        elif task_type == 'dailytasks':
            dailytasks_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep, selected_tasks=kwargs.get('selected_tasks'), invitation_characters=kwargs.get('invitation_characters'))
        elif task_type == 'tower_climbing':
            towerclimber_tool.run(
                attribute_type=kwargs.get('attribute_type'),
                max_runs=kwargs.get('max_runs', 0),
                stop_on_weekly=kwargs.get('stop_on_weekly', False),
                climb_type=kwargs.get('climb_type'),
                stop_event=stop_event,
                sleep_fn=_interruptible_sleep
            )
        elif task_type == 'combo':
            startgame_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep)
            if not stop_event.is_set():
                dailytasks_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep, selected_tasks=kwargs.get('selected_tasks'), invitation_characters=kwargs.get('invitation_characters'))
        elif task_type == 'daily_and_tower':
            dailytasks_tool.run(stop_event=stop_event, sleep_fn=_interruptible_sleep, selected_tasks=kwargs.get('selected_tasks'), invitation_characters=kwargs.get('invitation_characters'))
            if not stop_event.is_set():
                towerclimber_tool.run(
                    attribute_type=kwargs.get('attribute_type'),
                    max_runs=kwargs.get('max_runs', 0),
                    stop_on_weekly=kwargs.get('stop_on_weekly', False),
                    climb_type=kwargs.get('climb_type'),
                    stop_event=stop_event,
                    sleep_fn=_interruptible_sleep
                )
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
    attribute_type = data.get('attribute_type')
    max_runs = data.get('max_runs', 0)
    climb_type = data.get('climb_type')
    daily_sub_tasks = data.get('daily_sub_tasks')
    invitation_characters = data.get('invitation_characters')
    print(f"收到任务启动请求: type={task_type}, attribute={attribute_type}, max_runs={max_runs}, climb_type={climb_type}, daily_sub_tasks={daily_sub_tasks}, invitation_characters={invitation_characters}")

    if task_type not in ('start_game','dailytasks','combo','debug_sleep','debug_loop', 'tower_climbing', 'daily_and_tower'):
        return jsonify({'ok': False, 'error': '未知任务类型'}), 400
    with _task_lock:
        if _task_thread and _task_thread.is_alive():
            return jsonify({'ok': False, 'error': '已有任务在执行'}), 409
        _task_stop_event = Event()
        _task_pause_event = Event()
        _task_pause_event.set()  # 初始状态为运行（非暂停）
        _task_state = 'running'
        _task_name = task_type
        
        kwargs = {}
        if task_type in ('tower_climbing', 'daily_and_tower'):
            kwargs['attribute_type'] = attribute_type
            kwargs['max_runs'] = max_runs
            kwargs['climb_type'] = climb_type
            # 默认开启周常检测
            kwargs['stop_on_weekly'] = True
        
        if task_type in ('dailytasks', 'daily_and_tower', 'combo'):
            kwargs['selected_tasks'] = daily_sub_tasks
            kwargs['invitation_characters'] = invitation_characters

        _task_thread = Thread(target=_run_task, args=(task_type, _task_stop_event), kwargs=kwargs, daemon=True)
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


@app.route('/logs/export')
def export_logs():
    """导出当前内存中的所有日志"""
    try:
        # 将日志转换为文本格式
        log_lines = []
        for item in list(_log_deque):
            # 格式化时间戳
            dt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['ts']))
            log_lines.append(f"[{dt}] {item['level']}: {item['msg']}")
        
        content = "\n".join(log_lines)
        
        # 创建内存文件
        mem_file = io.BytesIO()
        mem_file.write(content.encode('utf-8'))
        mem_file.seek(0)
        
        return send_file(
            mem_file,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'stellasora_logs_{int(time.time())}.txt'
        )
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


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


@app.route('/stream/status')
def api_stream_status():
    """获取流状态"""
    return jsonify({
        "running": screenshot_tool.running,
        "method": screenshot_tool.screenshot_method
    })

@app.route('/api/test_latency', methods=['POST'])
def test_latency():
    """测试当前截图方式的延迟"""
    try:
        # 记录开始时间
        start_time = time.time()
        
        # 强制执行一次截图
        # 注意：如果流正在运行，capture() 返回的是缓存帧，延迟会非常低（接近0）
        # 如果流未运行，capture() 会执行真实的截图操作
        frame = screenshot_tool.capture()
        
        if frame is None:
            return jsonify({"success": False, "error": "截图失败"})
            
        # 计算耗时 (毫秒)
        latency_ms = (time.time() - start_time) * 1000
        
        return jsonify({
            "success": True, 
            "latency_ms": latency_ms,
            "method": screenshot_tool.screenshot_method,
            "is_stream_running": screenshot_tool.running
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

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
        
        # 如果配置中包含 screenshot_method，更新 screenshot_tool
        if 'screenshot_method' in updated:
            screenshot_tool.set_method(updated['screenshot_method'])
            
        return jsonify({'ok': True, 'config': updated})
    except Exception as exc:
        # logger.exception('配置接口处理失败') # logger not defined in this scope based on previous reads, using print
        print('配置接口处理失败:', exc)
        return jsonify({'ok': False, 'error': str(exc)}), 500

@app.route('/config/test_adb', methods=['POST'])
def test_adb_connection():
    data = request.get_json(silent=True) or {}
    adb_path_str = data.get('adb_path')
    adb_port = data.get('adb_port')
    
    if not adb_path_str:
        return jsonify({'ok': False, 'error': 'ADB路径为空'}), 400
        
    if not os.path.exists(adb_path_str):
         return jsonify({'ok': False, 'error': f'文件不存在: {adb_path_str}'}), 400

    try:
        # 1. Connect
        cmd_connect = f'"{adb_path_str}" connect 127.0.0.1:{adb_port}'
        # Windows usually uses gbk for console output
        proc_connect = subprocess.run(cmd_connect, shell=True, capture_output=True, text=True, encoding='gbk', errors='ignore')
        
        # 2. Check devices
        cmd_devices = f'"{adb_path_str}" devices'
        proc_devices = subprocess.run(cmd_devices, shell=True, capture_output=True, text=True, encoding='gbk', errors='ignore')
        
        output = (proc_connect.stdout or '') + "\n" + (proc_devices.stdout or '')
        
        # Check if connected
        target = f"127.0.0.1:{adb_port}"
        if target in (proc_devices.stdout or '') and "\tdevice" in (proc_devices.stdout or ''):
             return jsonify({'ok': True, 'message': '连接成功', 'detail': output})
        else:
             return jsonify({'ok': False, 'error': '连接失败或未授权', 'detail': output})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # 在本地运行，监听 127.0.0.1:5000
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)

