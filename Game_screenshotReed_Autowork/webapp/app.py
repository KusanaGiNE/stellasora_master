import os
import io
import sys
import base64
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
import cv2
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
# Ensure project root is on sys.path so `import core` works when launching from webapp/
sys.path.insert(0, str(PROJECT_ROOT))

from core import MumuScreenshot, Tapscreen, Autorecruitment, StartGame, IconDetector,Dailytasks

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


if __name__ == '__main__':
    # Run on localhost:5000
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)
