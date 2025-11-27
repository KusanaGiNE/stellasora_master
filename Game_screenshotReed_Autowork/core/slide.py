"""MuMu 模拟器触屏滑动封装."""

from __future__ import annotations

import subprocess

from .config import get_adb_path, get_default_instance, resolve_path


class Slide:
	"""封装 adb swipe 指令, 便于在 MuMu 模拟器上进行滑动操作."""

	def __init__(self, adb_path: str | None = None, default_instance: int | None = None) -> None:
		self._adb_override = resolve_path(adb_path) if adb_path else None
		self._default_instance_override = default_instance

	def _port_for(self, instance_num: int | None) -> int:
		base = self._port_base(instance_num)
		return 7554 + base

	def _run_adb(self, args: str, instance_num: int | None = None) -> None:
		port = self._port_for(instance_num)
		cmd = f'"{self._adb_path()}" -s 127.0.0.1:{port} {args}'
		subprocess.run(
			cmd,
			shell=True,
			check=True,
			capture_output=True,
			text=True,
			encoding="gbk",
			errors="ignore",
		)

	def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300, instance_num: int | None = None) -> None:
		"""在屏幕上从 (x1, y1) 滑动到 (x2, y2)."""

		args = f"shell input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration)}"
		try:
			self._run_adb(args, instance_num=instance_num)
		except subprocess.CalledProcessError as exc:  # pragma: no cover - 连接失败时报错
			stdout = exc.stdout or ""
			stderr = exc.stderr or ""
			if isinstance(stdout, (bytes, bytearray)):
				stdout = stdout.decode("gbk", errors="ignore")
			if isinstance(stderr, (bytes, bytearray)):
				stderr = stderr.decode("gbk", errors="ignore")
			msg = stderr.strip() or stdout.strip() or str(exc)
			raise RuntimeError(f"滑动失败: {msg}") from exc

	def _adb_path(self):
		path = self._adb_override or get_adb_path(raise_on_missing=False)
		if path is None:
			raise RuntimeError("ADB 路径未配置，请在设置页面填写 adb_path 后重试")
		if not path.exists():
			raise RuntimeError(f"指定的 ADB 工具不存在: {path}")
		return path

	def _port_base(self, instance_num: int | None) -> int:
		base = self._default_instance_override
		if base is None:
			base = get_default_instance()
		return instance_num if instance_num is not None else base

	def swipe_down(self, x: int | None = None, start_y: int = 350, end_y: int = 500, duration: int = 400, instance_num: int | None = None) -> None:
		"""默认在屏幕中部执行向下滑动."""

		x = 540 if x is None else x
		self.swipe(x, start_y, x, end_y, duration=duration, instance_num=instance_num)

	def swipe_up(self, x: int | None = None, start_y: int = 500, end_y: int = 100, duration: int = 400, instance_num: int | None = None) -> None:
		x = 540 if x is None else x
		self.swipe(x, start_y, x, end_y, duration=duration, instance_num=instance_num)

	def swipe_left(self, y: int | None = None, start_x: int = 900, end_x: int = 200, duration: int = 350, instance_num: int | None = None) -> None:
		y = 960 if y is None else y
		self.swipe(start_x, y, end_x, y, duration=duration, instance_num=instance_num)

	def swipe_right(self, y: int | None = None, start_x: int = 200, end_x: int = 900, duration: int = 350, instance_num: int | None = None) -> None:
		y = 960 if y is None else y
		self.swipe(start_x, y, end_x, y, duration=duration, instance_num=instance_num)

