import subprocess
import random

from .config import get_adb_path, get_default_instance, resolve_path, get_adb_port

class Tapscreen:
    def __init__(self, adb_path=None, default_instance=None):
        self._adb_override = resolve_path(adb_path) if adb_path else None
        self._default_instance_override = default_instance
        self.scale_x = 1.0
        self.scale_y = 1.0

    def set_scale(self, scale_x, scale_y):
        """设置坐标缩放比例"""
        self.scale_x = scale_x
        self.scale_y = scale_y
        print(f"点击坐标缩放比例已设置为: x={scale_x:.2f}, y={scale_y:.2f}")

    def tap_screen(self, x=0, y=0, instance_num=None, spread=2):
        """
        执行点击，增加随机偏移以模拟真人操作。
        :param spread: 随机偏移的标准差（像素），值越大点击范围越散
        """
        adb_path = self._adb_override or get_adb_path(raise_on_missing=False)
        if adb_path is None:
            raise RuntimeError("ADB 路径未配置，请在设置页面填写 adb_path 后重试")
        if not adb_path.exists():
            raise RuntimeError(f"指定的 ADB 工具不存在: {adb_path}")

        port = get_adb_port()
        
        # 1. 应用分辨率缩放 (将 1280x720 坐标映射到 真实分辨率)
        scaled_x = x * self.scale_x
        scaled_y = y * self.scale_y

        # 2. 生成高斯分布的随机偏移
        dx = int(random.gauss(0, spread))
        dy = int(random.gauss(0, spread))
        final_x = int(max(0, scaled_x + dx))
        final_y = int(max(0, scaled_y + dy))

        try:
            # 使用 capture_output=True, text=True 以确保 stdout/stderr 为 str（而非 bytes/None）
            subprocess.run(
                f'"{adb_path}" -s 127.0.0.1:{port} shell input tap {final_x} {final_y}',
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='ignore'
            )
            print(f"已在坐标({final_x}, {final_y})执行点击 (原坐标: {x}, {y})")
            return True
        except subprocess.CalledProcessError as e:
            # 安全提取 stdout/stderr（可能为 None 或 bytes/str）
            stdout = e.stdout or ''
            stderr = e.stderr or ''
            error_msg = stderr.strip() or stdout.strip() or f"returncode={getattr(e,'returncode',None)}"
            raise RuntimeError(f"点击失败: {error_msg}") from e