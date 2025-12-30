import os
import sys
import time
import threading
from core.mumu_screenshot import MumuScreenshot
from core.mumu_click import Tapscreen
from core.slide import Slide
from core.start_icon_detector import IconDetector
from core.config import get_config

class BaseTask:
    def __init__(self):
        self.screenshot_tool = MumuScreenshot()
        self.tapscreen_tool = Tapscreen()
        self.slide_tool = Slide()
        self.config = get_config()
        self.lang = self.config.get("server_lang", "zh-CN")
        self._detectors = {} # 缓存检测器
        self._init_resource_path()
        self._init_resolution_scale()

    def _init_resolution_scale(self):
        """初始化分辨率缩放比例"""
        # 截取一帧以获取真实分辨率
        # MumuScreenshot 会自动处理缩放，但我们需要它的 real_width/real_height 属性
        try:
            self.screenshot_tool.capture()
            real_w = self.screenshot_tool.real_width
            real_h = self.screenshot_tool.real_height
            target_w = self.screenshot_tool.target_width
            target_h = self.screenshot_tool.target_height
            
            if real_w > 0 and real_h > 0:
                scale_x = real_w / target_w
                scale_y = real_h / target_h
                self.tapscreen_tool.set_scale(scale_x, scale_y)
                self.slide_tool.set_scale(scale_x, scale_y)
        except Exception as e:
            print(f"初始化分辨率缩放失败: {e}")

    def _init_resource_path(self):
        """统一处理资源路径（支持打包后运行）"""
        folder_name = f"templates_{self.lang}"
        if getattr(sys, 'frozen', False):
            # 在 onedir 模式下，资源文件放在 exe 同级目录，而不是 _internal (_MEIPASS)
            base_path = os.path.dirname(sys.executable)
            tpl_dir = os.path.join(base_path, folder_name)
        else:
            # 假设 core/base_task.py 位置，向上两级找到 templates
            tpl_dir = os.path.join(os.path.dirname(__file__), f"../{folder_name}")
        self.tpl_dir = os.path.abspath(tpl_dir)

    def load_detector(self, subpath):
        """懒加载检测器，避免重复IO"""
        if subpath not in self._detectors:
            full_path = os.path.join(self.tpl_dir, subpath)
            self._detectors[subpath] = IconDetector(full_path)
        return self._detectors[subpath]

    def click_until_appear(self, target_detector=None, expected_detector=None, max_retry=10, interval=1.0, stop_event=None, region=None, target_pos=None):
        """
        MAA式核心逻辑：点击目标(target)，直到预期画面(expected)出现。
        
        :param target_detector: 需要点击的按钮检测器 (可以是 None，表示只等待不点击)
        :param expected_detector: 点击后应该出现的画面检测器
        :param max_retry: 最大重试次数
        :param interval: 每次检测间隔(秒)
        :param stop_event: 停止信号
        :param region: 目标检测的区域 (x, y, w, h)，用于加速识别
        :param target_pos: 直接点击的坐标 (x, y)，如果提供了此参数，则忽略 target_detector
        :return: True if success, False if timeout
        """
        if expected_detector is None:
            raise ValueError("expected_detector is required")

        print(f"正在尝试操作，等待目标画面出现...")
        for i in range(max_retry):
            if stop_event and stop_event.is_set():
                return False

            screenshot = self.screenshot_tool.capture()
            
            # 1. 检查是否成功
            (ex, ey), _ = expected_detector.find_icon(screenshot)
            if ex is not None:
                print("预期画面已出现，操作成功")
                return True
            
            # 2. 如果还没成功，尝试点击目标
            if target_pos:
                print(f"点击固定坐标 {target_pos}，第 {i+1}/{max_retry} 次尝试")
                self.tapscreen_tool.tap_screen(*target_pos)
            elif target_detector:
                # 使用 region 加速识别
                (tx, ty), _ = target_detector.find_icon(screenshot, region=region)
                if tx is not None:
                    print(f"点击目标 ({tx}, {ty})，第 {i+1}/{max_retry} 次尝试")
                    self.tapscreen_tool.tap_screen(tx, ty)
            
            time.sleep(interval)
        
        print("操作超时，未检测到预期画面")
        return False

    def wait_until_appear(self, expected_detector, max_retry=20, interval=0.5, stop_event=None):
        """
        等待画面出现，不进行点击
        """
        print(f"正在等待画面出现...")
        for i in range(max_retry):
            if stop_event and stop_event.is_set():
                return False
            
            screenshot = self.screenshot_tool.capture()
            (ex, ey), _ = expected_detector.find_icon(screenshot)
            if ex is not None:
                print("目标画面已出现")
                return True
            
            time.sleep(interval)
        
        print("等待超时")
        return False

    def interruptible_sleep(self, seconds: float, stop_event: threading.Event | None = None) -> bool:
        """支持中断的睡眠"""
        if seconds <= 0:
            return not (stop_event and stop_event.is_set())
        end = time.time() + seconds
        while time.time() < end:
            if stop_event and stop_event.is_set():
                return False
            remaining = end - time.time()
            if remaining <= 0:
                break
            time.sleep(min(0.2, remaining))
        return True
