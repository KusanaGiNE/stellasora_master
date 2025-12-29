import subprocess
import cv2
import numpy as np
import os
import threading
import time
from pathlib import Path

try:
    import scrcpy
    from adbutils import adb
    HAS_SCRCPY = True
except ImportError as e:
    print(f"Scrcpy 导入失败: {e}")
    HAS_SCRCPY = False

from .config import get_adb_path, get_default_instance, resolve_path, get_adb_port

class MumuScreenshot:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # 单例模式，确保全局只有一个截图流
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(MumuScreenshot, cls).__new__(cls)
        return cls._instance

    def __init__(self, adb_path=None, default_instance=None, auto_connect: bool = True):
        if hasattr(self, '_initialized'):
            return
        self._adb_override = resolve_path(adb_path) if adb_path else None
        self._default_instance_override = default_instance

        # 流式截图相关
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.thread = None
        self.scrcpy_client = None
        self._initialized = True

        # 分辨率适配
        self.real_width = 0
        self.real_height = 0
        self.target_width = 1280
        self.target_height = 720

        # 截图方式: 'PNG', 'RAW', 'SCRCPY'
        self.screenshot_method = 'PNG'

        # Scrcpy稳定性控制
        self._warmup_frames = 0
        self._need_restart = False
        self._bad_frame_streak = 0

        # 帧监控：用于判断是否“卡在某一帧”
        self._last_frame_ts = 0.0

        # 任务启动时可预先探测一次 display_id（避免预览阶段触发 dumpsys）
        self._preferred_display_id = None

        # 初始化连接（可选）：Web 启动阶段允许跳过，避免启动时强制校验/连接 adb。
        if auto_connect:
            self._ensure_connected()

    def frame_age(self):
        """返回距离最后一次写入 latest_frame 的秒数；无数据返回 None"""
        ts = getattr(self, "_last_frame_ts", 0.0) or 0.0
        if ts <= 0:
            return None
        return time.time() - ts

    def set_method(self, method):
        """设置截图方式: 'PNG', 'RAW', 'SCRCPY'"""
        if method == 'SCRCPY' and not HAS_SCRCPY:
            print("Scrcpy 库未安装，无法使用 Scrcpy 模式")
            return

        if method in ['PNG', 'RAW', 'SCRCPY']:
            restart = self.running and self.screenshot_method != method
            if restart:
                self.stop_stream()

            self.screenshot_method = method
            print(f"截图方式已切换为: {method}")

            if restart:
                self.start_stream()

    def _is_garbled_green_frame(self, img: np.ndarray) -> bool:
        """识别 scrcpy 花屏/绿屏帧（稳定优先：尽量避免误判导致无限重启）。

        判定逻辑：
        - 绿屏通常是“绝大多数像素都偏绿”，而不是整体略偏绿。
        - 仅当“绿像素占比很高”并且“画面细节/方差很低”才视为坏帧。
        """
        if img is None or not hasattr(img, "shape"):
            return True
        if img.ndim != 3 or img.shape[2] < 3:
            return True

        try:
            h, w = img.shape[:2]
            # 下采样加速
            scale = 64 / max(h, w)
            if scale < 1.0:
                small = cv2.resize(img, (int(w * scale), int(h * scale)))
            else:
                small = img

            b = small[..., 0].astype(np.int16)
            g = small[..., 1].astype(np.int16)
            r = small[..., 2].astype(np.int16)

            # 绿像素：G 明显大于 R/B 且亮度不太低
            green_mask = (g > r + 40) & (g > b + 40) & (g > 80)
            green_ratio = float(green_mask.mean())

            if green_ratio < 0.85:
                return False

            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            detail = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            std = float(gray.std())

            # 极端绿屏通常“细节低 + 方差低”
            return (detail < 10.0) and (std < 25.0)
        except Exception:
            # 解析失败宁可认为坏帧，触发上层重连
            return True

    def start_stream(self, detect_display: bool = True):
        """开启后台连续截图"""
        if self.running:
            return
        self.running = True

        if self.screenshot_method == 'SCRCPY' and HAS_SCRCPY:
            self._start_scrcpy_stream(detect_display=detect_display)
        else:
            self.thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.thread.start()

        print(f"截图流已启动 (模式: {self.screenshot_method})")

    def stop_stream(self):
        """停止后台截图"""
        self.running = False

        if self.scrcpy_client:
            try:
                self.scrcpy_client.stop()
            except Exception as e:
                print(f"Scrcpy 停止错误: {e}")
            self.scrcpy_client = None

        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None
        print("截图流已停止")

    def _on_scrcpy_frame(self, frame):
        """Scrcpy 回调"""
        if frame is None:
            return

        # 预热丢帧，防止绿屏
        if self._warmup_frames > 0:
            self._warmup_frames -= 1
            return

        img = frame

        # 兼容 4 通道（部分环境可能返回 BGRA）
        try:
            if isinstance(img, np.ndarray) and img.ndim == 3 and img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception:
            return

        img = self._process_image(img)
        if img is None:
            return

        # 花屏检测：连续坏帧则触发重连
        if self._is_garbled_green_frame(img):
            self._bad_frame_streak += 1
            if self._bad_frame_streak >= 8:
                self._need_restart = True
            return
        else:
            self._bad_frame_streak = 0

        with self.frame_lock:
            self.latest_frame = img
            self._last_frame_ts = time.time()

    def _get_game_display_id(self, adb_path, serial):
        """获取游戏所在的显示器ID"""
        try:
            # 运行 dumpsys window displays
            cmd = f'"{adb_path}" -s {serial} shell dumpsys window displays'
            print(f"正在检测游戏显示器: {cmd}")
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', errors='ignore')
            output = result.stdout
            
            current_display_id = 0
            found_display = None
            
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("Display: mDisplayId="):
                    try:
                        current_display_id = int(line.split("mDisplayId=")[1].split()[0])
                    except:
                        pass
                
                # 只要当前显示器块中出现了游戏包名，就认为是这个显示器
                if "com.RoamingStar.StellaSora" in line:
                    # 排除掉一些无关的引用，比如 mLastOrientationSource 指向了其他 display 的 activity (虽然不太常见)
                    # 但通常出现在 display block 里的都是相关的
                    print(f"在显示器 {current_display_id} 中发现游戏包名: {line[:100]}...")
                    found_display = current_display_id
                    
                    # 如果明确是 FocusedApp 或 Task，那优先级最高
                    if "mFocusedApp" in line or "mCurrentFocus" in line or "Task" in line:
                        return current_display_id
            
            if found_display is not None:
                print(f"使用最后一次发现游戏的显示器 ID: {found_display}")
                return found_display

            print("未检测到特定游戏显示器，使用默认 ID: 0")
            return 0
            
        except Exception as e:
            print(f"获取显示器ID失败: {e}")
            return 0

    def _start_scrcpy_stream(self, detect_display: bool = True):
        port = get_adb_port()
        serial = f"127.0.0.1:{port}"
        try:
            adb_path = self._get_adb_path()
            if adb_path and os.path.exists(adb_path):
                adb.adb_path = adb_path

            try:
                print("清理旧的 Scrcpy 服务进程...")
                subprocess.run(f'"{adb_path}" -s {serial} shell "pkill -f scrcpy"', shell=True, timeout=2)
            except Exception:
                pass

            if detect_display:
                display_id = self._preferred_display_id if self._preferred_display_id is not None else self._get_game_display_id(adb_path, serial)
            else:
                display_id = 0

            adb.connect(serial)
            device = adb.device(serial=serial)

            # 预热帧数：适当加大
            self._warmup_frames = 30
            self._need_restart = False
            self._bad_frame_streak = 0

            self.thread = threading.Thread(target=self._scrcpy_loop_safe, args=(device, display_id), daemon=True)
            self.thread.start()

        except Exception as e:
            print(f"Scrcpy 启动准备失败: {e}")
            print("回退到 RAW 模式")
            self.screenshot_method = 'RAW'
            self.thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.thread.start()

    def _scrcpy_loop_safe(self, device, display_id):
        """Scrcpy 视频流监听循环 (带异常捕获和重试)"""
        retry_count = 0

        while self.running:
            if self.thread is not threading.current_thread():
                print("检测到线程变更，停止当前 Scrcpy 线程")
                break

            try:
                if self.scrcpy_client:
                    try:
                        self.scrcpy_client.stop()
                    except:
                        pass

                # 稳定性优先：降一点分辨率/码率/帧率，先把花屏压下去
                self.scrcpy_client = scrcpy.Client(
                    device=device,
                    max_width=960,       # 原 1280
                    bitrate=2000000,     # 原 4000000
                    max_fps=10,          # 原 15
                    display_id=display_id
                )

                self.scrcpy_client.add_listener(scrcpy.EVENT_FRAME, self._on_scrcpy_frame)

                print(f"Scrcpy client starting (attempt {retry_count + 1})...")
                self.scrcpy_client.start(threaded=True)

                time.sleep(1)

                if getattr(self.scrcpy_client, "alive", False):
                    print("Scrcpy client connected successfully")
                    retry_count = 0

                while self.running and getattr(self.scrcpy_client, "alive", False):
                    if self.thread is not threading.current_thread():
                        break

                    # 回调检测到连续坏帧 -> 主循环触发重启
                    if self._need_restart:
                        print("检测到连续花屏帧，重启 Scrcpy client...")
                        self._need_restart = False
                        self._warmup_frames = 30
                        break

                    # 卡帧检测：超过 3 秒没有新帧写入，主动重启
                    if self._warmup_frames == 0 and self._last_frame_ts > 0:
                        if time.time() - self._last_frame_ts > 3.0:
                            print("检测到 Scrcpy 卡帧(>3s无新帧)，重启 Scrcpy client...")
                            self._warmup_frames = 30
                            break

                    time.sleep(0.5)

                print("Scrcpy client disconnected or stopped")

            except Exception as e:
                print(f"Scrcpy 流异常: {e}")

            if self.running:
                if self.thread is not threading.current_thread():
                    break
                retry_count += 1
                if retry_count > 10:
                    print("Scrcpy 重试次数过多，自动降级到 RAW 模式")
                    self.running = False
                    self.screenshot_method = 'RAW'
                    self.start_stream()
                    return

                print(f"等待 2 秒后重试... ({retry_count}/10)")
                time.sleep(2)

            if self.scrcpy_client:
                try:
                    self.scrcpy_client.stop()
                except:
                    pass
                self.scrcpy_client = None

    def _stream_loop(self):
        while self.running:
            try:
                img = self._capture_once()
                if img is not None:
                    with self.frame_lock:
                        self.latest_frame = img
                        self._last_frame_ts = time.time()
                else:
                    time.sleep(0.1) # 失败时稍作等待
            except Exception as e:
                print(f"截图流错误: {e}")
                time.sleep(0.5)

    def _process_image(self, img):
        """处理图像：记录真实分辨率并缩放到目标分辨率"""
        if img is None: return None
        
        h, w = img.shape[:2]
        self.real_width = w
        self.real_height = h
        
        # 如果分辨率不匹配，强制缩放到 1280x720
        # 这样所有的图像识别和坐标计算都可以基于 1280x720 进行
        if w != self.target_width or h != self.target_height:
            try:
                img = cv2.resize(img, (self.target_width, self.target_height))
            except Exception as e:
                print(f"图像缩放失败: {e}")
        return img

    def _capture_raw(self):
        """使用 RAW 模式截图 (adb exec-out screencap)"""
        adb_path = self._get_adb_path()
        port = get_adb_port()
        
        try:
            # 不带 -p 参数，获取原始二进制数据
            # 格式通常为: 12字节头部 (width, height, format) + RGBA数据
            result = subprocess.run(
                f'"{adb_path}" -s 127.0.0.1:{port} exec-out screencap',
                shell=True,
                capture_output=True,
                check=True
            )
            
            data = result.stdout
            if not data:
                return None
                
            # 解析头部
            # 头部通常是 3个 32位整数 (Little Endian)
            # width = int.from_bytes(data[0:4], 'little')
            # height = int.from_bytes(data[4:8], 'little')
            # format = int.from_bytes(data[8:12], 'little')
            
            # 简单起见，我们直接跳过头部，按已知分辨率重构
            # 如果分辨率未知，第一次可能需要解析头部，这里假设标准 RGBA
            
            # 尝试解析头部
            w = int.from_bytes(data[0:4], byteorder='little')
            h = int.from_bytes(data[4:8], byteorder='little')
            f = int.from_bytes(data[8:12], byteorder='little')
            
            # 校验数据长度
            expected_len = w * h * 4 + 12
            if len(data) < expected_len:
                # 有时候 adb 输出可能会截断或包含额外换行符转换
                # 如果长度不对，回退到 PNG 模式或报错
                # print(f"RAW数据长度不匹配: {len(data)} vs {expected_len}")
                return None

            pixels = data[12:expected_len]
            
            # 将字节转换为 numpy 数组
            img = np.frombuffer(pixels, dtype=np.uint8)
            img = img.reshape((h, w, 4))
            
            # RGBA 转 BGR (OpenCV 默认格式)
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            
            return self._process_image(img)
            
        except Exception as e:
            print(f"RAW截图失败: {e}")
            return None

    def _capture_once(self):
        """执行一次截图"""
        if self.screenshot_method == 'RAW':
            img = self._capture_raw()
            if img is not None:
                return img
            # 如果 RAW 失败，自动回退到 PNG
            print("RAW 模式失败，回退到 PNG 模式")
        
        adb_path = self._get_adb_path()
        port = get_adb_port()
        
        try:
            # 移除 connect 命令，假设已连接
            result = subprocess.run(
                f'"{adb_path}" -s 127.0.0.1:{port} exec-out screencap -p',
                shell=True,
                capture_output=True,
                check=True
            )
            
            img_array = np.frombuffer(result.stdout, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return self._process_image(img)
            
        except subprocess.CalledProcessError as e:
            # 如果失败，尝试重连一次
            self._ensure_connected()
            raise RuntimeError(f"ADB截图失败") from e

    def capture(self, instance_num=None, save_path=None):
        """获取当前屏幕截图（合并版，避免重复定义覆盖）"""
        # Scrcpy 模式下若未启动流，自动启动
        if self.screenshot_method == 'SCRCPY':
            if not self.running:
                self.start_stream()
                # 等待第一帧（最多 2 秒）
                for _ in range(20):
                    with self.frame_lock:
                        if self.latest_frame is not None:
                            break
                    time.sleep(0.1)

            img = None
            last_ts = 0.0
            with self.frame_lock:
                if self.latest_frame is not None:
                    img = self.latest_frame.copy()
                    last_ts = float(self._last_frame_ts or 0.0)

            # 若已有帧但长时间未更新：触发重启意图，仍返回当前帧（避免频繁回退 adb 截图）
            if img is not None and last_ts > 0 and (time.time() - last_ts) > 2.0:
                self._need_restart = True

            # 若仍无帧，允许一次 PNG/RAW 回退（避免直接崩）
            if img is None:
                img = self._capture_once()
                if img is not None:
                    self._last_frame_ts = time.time()

        else:
            # 非 Scrcpy：若流在跑取最新帧，否则单次截图
            img = None
            if self.running:
                with self.frame_lock:
                    if self.latest_frame is not None:
                        img = self.latest_frame.copy()
            if img is None:
                img = self._capture_raw() if self.screenshot_method == 'RAW' else self._capture_once()

        if img is None:
            raise ValueError("截图数据解析失败")

        if save_path:
            save_path = str(Path(save_path))
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            cv2.imwrite(save_path, img)

        return img

    def _get_adb_path(self) -> str:
        """解析 adb 路径（优先使用初始化传入的覆盖值）"""
        if self._adb_override:
            return str(self._adb_override)
        p = get_adb_path()
        return str(resolve_path(p)) if p else "adb"

    def _ensure_connected(self, timeout_sec: float = 3.0) -> bool:
        """确保 ADB 已连接到模拟器端口（127.0.0.1:port）"""
        adb_path = self._get_adb_path()
        port = get_adb_port()
        serial = f"127.0.0.1:{port}"

        def _run(cmd: str):
            return subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=timeout_sec,
            )

        # 1) connect
        proc_connect = _run(f'"{adb_path}" connect {serial}')
        if proc_connect.returncode != 0:
            detail = (proc_connect.stderr or proc_connect.stdout or '').strip()
            raise RuntimeError(f"ADB connect 失败: {detail}")

        # 2) devices
        proc_devices = _run(f'"{adb_path}" devices')
        out = (proc_devices.stdout or '')
        ok = False
        for line in out.splitlines():
            if line.strip().startswith(serial) and "\tdevice" in line:
                ok = True
                break
        if not ok:
            detail = ((proc_devices.stderr or '') + "\n" + out).strip()
            raise RuntimeError(f"ADB 未发现设备 {serial} (可能未启动/未授权): {detail}")

        return True

    def preflight_for_task(self, detect_display: bool = True) -> dict:
        """任务启动前置检查：连接设备；SCRCPY 模式可提前探测 display_id。

        返回: { serial, display_id? }
        """
        port = get_adb_port()
        serial = f"127.0.0.1:{port}"
        self._ensure_connected()

        result = {"serial": serial}

        if detect_display and self.screenshot_method == 'SCRCPY' and HAS_SCRCPY:
            adb_path = self._get_adb_path()
            display_id = self._get_game_display_id(adb_path, serial)
            self._preferred_display_id = display_id
            result["display_id"] = display_id

        return result