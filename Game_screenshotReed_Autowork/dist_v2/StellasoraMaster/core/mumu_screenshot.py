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

    def __init__(self, adb_path=None, default_instance=None):
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

        # 初始化连接
        self._ensure_connected()

    def set_method(self, method):
        """设置截图方式: 'PNG', 'RAW', 'SCRCPY'"""
        if method == 'SCRCPY' and not HAS_SCRCPY:
            print("Scrcpy 库未安装，无法使用 Scrcpy 模式")
            return

        if method in ['PNG', 'RAW', 'SCRCPY']:
            # 如果正在运行且模式改变，重启流
            restart = self.running and self.screenshot_method != method
            if restart:
                self.stop_stream()
            
            self.screenshot_method = method
            print(f"截图方式已切换为: {method}")
            
            if restart:
                self.start_stream()

    def capture(self):
        """获取当前屏幕截图"""
        if self.screenshot_method == 'SCRCPY':
            # 如果流未启动，自动启动
            if not self.running:
                print("Scrcpy 模式下自动启动截图流...")
                self.start_stream()
                # 等待第一帧
                for _ in range(20):
                    if self.latest_frame is not None: break
                    time.sleep(0.1)
            
            if self.latest_frame is not None:
                return self.latest_frame
            
            # 保持返回 None 以便前端等待，避免闪烁
            return None
            
        elif self.screenshot_method == 'RAW':
            return self._capture_raw()
        else:
            return self._capture_once()

    def _ensure_connected(self):
        """确保ADB已连接，避免每次截图都连接"""
        try:
            adb_path = self._get_adb_path()
        except RuntimeError:
            print("ADB 路径未配置，跳过初始连接")
            return

        port = get_adb_port()
        try:
            subprocess.run(
                f'"{adb_path}" connect 127.0.0.1:{port}',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
        except Exception as e:
            print(f"ADB连接警告: {e}")

    def _get_adb_path(self):
        adb_path = self._adb_override or get_adb_path(raise_on_missing=False)
        if adb_path is None:
            raise RuntimeError("ADB 路径未配置")
        return adb_path

    def start_stream(self):
        """开启后台连续截图"""
        if self.running:
            return
        self.running = True
        
        if self.screenshot_method == 'SCRCPY' and HAS_SCRCPY:
            self._start_scrcpy_stream()
        else:
            self.thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.thread.start()
        
        print(f"截图流已启动 (模式: {self.screenshot_method})")

    def stop_stream(self):
        """停止后台截图"""
        self.running = False
        
        # 停止 Scrcpy
        if self.scrcpy_client:
            try:
                self.scrcpy_client.stop()
            except Exception as e:
                print(f"Scrcpy 停止错误: {e}")
            self.scrcpy_client = None

        # 停止普通线程
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None
        print("截图流已停止")

    def _on_scrcpy_frame(self, frame):
        """Scrcpy 回调"""
        if frame is not None:
            # 预热丢帧，防止绿屏
            if hasattr(self, '_warmup_frames') and self._warmup_frames > 0:
                self._warmup_frames -= 1
                return

            # Scrcpy 返回的是 BGR (opencv 默认)
            img = self._process_image(frame)
            with self.frame_lock:
                self.latest_frame = img

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

    def _start_scrcpy_stream(self):
        port = get_adb_port()
        serial = f"127.0.0.1:{port}"
        try:
            # 尝试设置 adbutils 的 adb 路径
            adb_path = self._get_adb_path()
            if adb_path and os.path.exists(adb_path):
                adb.adb_path = adb_path
            
            # 清理残留的 scrcpy-server 进程，防止连接到错误的旧会话
            try:
                print("清理旧的 Scrcpy 服务进程...")
                # 使用 pkill (如果可用) 或通过 ps 查找
                # 简单粗暴的方法：kill 掉所有包含 scrcpy 的 app_process
                subprocess.run(f'"{adb_path}" -s {serial} shell "pkill -f scrcpy"', shell=True, timeout=2)
            except Exception:
                pass

            # 获取正确的 display_id
            display_id = self._get_game_display_id(adb_path, serial)
            
            adb.connect(serial)
            device = adb.device(serial=serial)
            
            # 初始化预热计数器
            self._warmup_frames = 15

            # 启动守护线程，在线程内部管理 Scrcpy Client 的生命周期
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
        # 导入 av 库 (放在这里是为了避免初始化时的依赖错误)
        import av
        
        retry_count = 0
        
        while self.running:
            # 检查当前线程是否仍是活跃的截图线程
            # 如果 stop_stream 被调用，self.thread 会被置为 None
            # 如果 start_stream 被调用，self.thread 会指向新线程
            if self.thread is not threading.current_thread():
                print("检测到线程变更，停止当前 Scrcpy 线程")
                break

            try:
                # 每次循环重新创建 client，确保状态重置
                if self.scrcpy_client:
                    try:
                        self.scrcpy_client.stop()
                    except:
                        pass
                
                # max_width=1280 限制分辨率，避免过高分辨率导致花屏或性能问题
                # bitrate=4000000 (4Mbps) 降低码率以提高稳定性
                # max_fps=15 限制帧率，减少解码压力
                self.scrcpy_client = scrcpy.Client(
                    device=device, 
                    max_width=1280, 
                    bitrate=4000000, 
                    max_fps=15,
                    display_id=display_id
                )
                
                # 绑定监听器
                self.scrcpy_client.add_listener(scrcpy.EVENT_FRAME, self._on_scrcpy_frame)
                
                print(f"Scrcpy client starting (attempt {retry_count + 1})...")
                self.scrcpy_client.start(threaded=True)
                
                # 等待连接建立
                time.sleep(1)
                
                if self.scrcpy_client.alive:
                    print("Scrcpy client connected successfully")
                    retry_count = 0 # 重置重试计数
                
                # 监控循环
                while self.running and self.scrcpy_client.alive:
                    if self.thread is not threading.current_thread():
                        break
                    time.sleep(1)
                
                print("Scrcpy client disconnected or stopped")
                    
            except Exception as e:
                print(f"Scrcpy 流异常: {e}")
            
            # 如果还在运行状态，说明是异常退出，准备重试
            if self.running:
                if self.thread is not threading.current_thread():
                    break
                retry_count += 1
                if retry_count > 10:
                    print("Scrcpy 重试次数过多，自动降级到 RAW 模式")
                    self.running = False # 停止当前循环
                    self.screenshot_method = 'RAW'
                    # 重新启动流（会进入 _stream_loop）
                    self.start_stream()
                    return

                print(f"等待 2 秒后重试... ({retry_count}/10)")
                time.sleep(2)
            
            # 清理资源
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
        """获取当前屏幕截图"""
        # 如果是 Scrcpy 模式且未运行，自动启动流以获得高性能
        if self.screenshot_method == 'SCRCPY' and not self.running:
            print("Scrcpy 模式下自动启动截图流...")
            self.start_stream()
            # 等待第一帧，最多等待 2 秒
            for _ in range(20):
                with self.frame_lock:
                    if self.latest_frame is not None:
                        break
                time.sleep(0.1)

        img = None
        
        # 如果开启了流模式，直接取最新帧
        if self.running:
            with self.frame_lock:
                if self.latest_frame is not None:
                    img = self.latest_frame.copy()
        
        # 如果没开启流模式，或者流模式还没获取到第一帧，则手动截取 (回退到 PNG)
        if img is None:
            # 如果是 Scrcpy 模式但获取失败，可能是启动延迟，这里允许一次 PNG 回退
            img = self._capture_once()
            
        if img is None:
            raise ValueError("截图数据解析失败")
            
        if save_path:
            save_path = str(Path(save_path))
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            cv2.imwrite(save_path, img)
        
        return img