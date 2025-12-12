import subprocess

from .config import get_adb_path, get_default_instance, resolve_path, get_adb_port

class Tapscreen:
    def __init__(self, adb_path=None, default_instance=None):
        self._adb_override = resolve_path(adb_path) if adb_path else None
        self._default_instance_override = default_instance

    def tap_screen(self, x=0, y=0, instance_num=None):
        adb_path = self._adb_override or get_adb_path(raise_on_missing=False)
        if adb_path is None:
            raise RuntimeError("ADB 路径未配置，请在设置页面填写 adb_path 后重试")
        if not adb_path.exists():
            raise RuntimeError(f"指定的 ADB 工具不存在: {adb_path}")

        port = get_adb_port()
        
        try:
            # 使用 capture_output=True, text=True 以确保 stdout/stderr 为 str（而非 bytes/None）
            subprocess.run(
                f'"{adb_path}" -s 127.0.0.1:{port} shell input tap {x} {y}',
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='ignore'
            )
            print(f"已在坐标({x}, {y})执行点击")
            return True
        except subprocess.CalledProcessError as e:
            # 安全提取 stdout/stderr（可能为 None 或 bytes/str）
            stdout = e.stdout or ''
            stderr = e.stderr or ''
            error_msg = stderr.strip() or stdout.strip() or f"returncode={getattr(e,'returncode',None)}"
            raise RuntimeError(f"点击失败: {error_msg}") from e