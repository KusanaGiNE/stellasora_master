"""Application bootstrap for the Stellasora Master automation suite."""
from __future__ import annotations

import importlib
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Explicit imports to ensure PyInstaller bundles them
import flask
import cv2
import numpy
try:
    import webapp.app
except ImportError:
    pass

PYPI_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
REQUIRED_PACKAGES = [
    "flask",
    "opencv-python",
    "numpy",
]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


def resource_root() -> Path:
    # 修改为适应“源码外置”模式
    # 如果是打包环境 (frozen)，资源根目录应该是 exe 所在的目录 (sys.executable 的父目录)
    # 因为我们将 webapp 和 core 文件夹放在了 exe 旁边
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    
    # 如果是源码运行环境，则使用当前文件所在目录
    return Path(__file__).resolve().parent


def ensure_sys_path(root: Path) -> None:
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def install_missing_packages(packages: list[str]) -> None:
    # Map package names to import names
    package_to_module = {
        "opencv-python": "cv2",
        "scrcpy-client": "scrcpy",
        "Pillow": "PIL",
    }

    missing: list[str] = []
    for pkg in packages:
        module_name = package_to_module.get(pkg, pkg)
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            missing.append(pkg)
    if not missing:
        return

    cmd = [sys.executable, "-m", "pip", "install", "-i", PYPI_MIRROR, *missing]
    subprocess.check_call(cmd)


def find_open_port(host: str, start_port: int) -> int:
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                port += 1


def launch_browser(host: str, port: int) -> None:
    url = f"http://{host}:{port}/"

    def _open() -> None:
        for _ in range(12):
            time.sleep(0.5)
            try:
                with socket.create_connection((host, port), timeout=0.2):
                    webbrowser.open(url, new=2)
                    return
            except OSError:
                continue

    threading.Thread(target=_open, daemon=True).start()


def main() -> None:
    root = resource_root()
    ensure_sys_path(root)

    # Only attempt to install dependencies when not running from PyInstaller bundle.
    if not getattr(sys, "_MEIPASS", None):
        install_missing_packages(REQUIRED_PACKAGES)

    os.chdir(root)

    from webapp.app import app

    port = find_open_port(DEFAULT_HOST, DEFAULT_PORT)
    launch_browser(DEFAULT_HOST, port)
    app.run(host=DEFAULT_HOST, port=port, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
