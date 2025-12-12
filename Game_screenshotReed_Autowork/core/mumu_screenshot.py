import subprocess
import cv2
import numpy as np
import os
from pathlib import Path

from .config import get_adb_path, get_default_instance, resolve_path, get_adb_port

class MumuScreenshot:
    def __init__(self, adb_path=None, default_instance=None):
        self._adb_override = resolve_path(adb_path) if adb_path else None
        self._default_instance_override = default_instance

    def capture(self, instance_num=None, save_path=None):
        adb_path = self._adb_override or get_adb_path(raise_on_missing=False)
        if adb_path is None:
            raise RuntimeError("ADB 路径未配置，请在设置页面填写 adb_path 后重试")
        if not adb_path.exists():
            raise RuntimeError(f"指定的 ADB 工具不存在: {adb_path}")

        port = get_adb_port()
        
        try:
            subprocess.run(
                f'"{adb_path}" connect 127.0.0.1:{port}',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            result = subprocess.run(
                f'"{adb_path}" -s 127.0.0.1:{port} exec-out screencap -p',
                shell=True,
                capture_output=True,
                check=True
            )
            
            img_array = np.frombuffer(result.stdout, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                raise ValueError("截图数据解析失败")
                
            if save_path:
                save_path = str(Path(save_path))
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                if not cv2.imwrite(save_path, img):
                    raise RuntimeError(f"无法保存图像到: {save_path}")
            
            return img
            
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode('gbk', errors='ignore') if e.stderr else ''
            stdout = e.stdout.decode('gbk', errors='ignore') if e.stdout else ''
            error_msg = stderr or stdout or str(e)
            raise RuntimeError(f"ADB命令执行失败: {error_msg}") from e
        except Exception as e:
            raise RuntimeError(f"截图过程中发生错误: {str(e)}") from e