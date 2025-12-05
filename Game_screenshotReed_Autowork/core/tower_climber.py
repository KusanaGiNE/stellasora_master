

import subprocess
import cv2
import numpy as np
import os
import time

from pathlib import Path
from core import OcrTool
from .mumu_screenshot import MumuScreenshot
from .start_icon_detector import IconDetector
from .mumu_click import Tapscreen
from .show_detector import Showdetector
from .slide import Slide


class TowerClimber:
    def __init__(self):
        self.screenshot_tool = MumuScreenshot()
        self.tapscreen_tool = Tapscreen()
        self.display_tool = Showdetector(output_dir="tower_climber_test")
        self.ocr_tool = OcrTool()
        self.slide_tool = Slide()

        tpl_dir = os.path.join(os.path.dirname(__file__), "../templates")
        def _load(subpath):
            return IconDetector(os.path.join(tpl_dir, subpath))

        self.maintitle_detector = _load("mainTitle_icon/Market.png")
        self.market_detector = _load("mainTitle_icon/Purchasing.png")

    def run(self, attribute_type=None, stop_event=None, sleep_fn=None):
        """
        支持 stop_event; sleep_fn(seconds, stop_event).
        :param attribute_type: 'light_earth' | 'water_wind' | 'fire_dark'
        """
        print(f"启动爬塔任务，目标属性: {attribute_type}")
        screenshot_tool = self.screenshot_tool
        tapscreen_tool = self.tapscreen_tool
        display_tool = self.display_tool
        ocr_tool = self.ocr_tool
        slide_tool = self.slide_tool

        # 使用预加载的检测器
        maintitle_detector = self.maintitle_detector
        market_detector = self.market_detector
        def _sleep(sec):
            if sleep_fn:
                return sleep_fn(sec, stop_event)
            # fallback 简单分片
            end = time.time() + sec
            while time.time() < end:
                if stop_event and stop_event.is_set():
                    return False
                time.sleep(min(0.2, end - time.time()))
            return True

        def Back2maintitle():
            tapscreen_tool.tap_screen(66, 37)
            if not _sleep(1): return False
            screenshot1 = screenshot_tool.capture()
            (x3, y3), conf2 = maintitle_detector.find_icon(screenshot1)
            while x3 is None:
                if stop_event and stop_event.is_set(): return False
                tapscreen_tool.tap_screen(66, 37)
                screenshot1 = screenshot_tool.capture()
                (x3, y3), conf2 = maintitle_detector.find_icon(screenshot1)
            print("返回主界面完成")
            if not _sleep(2): return False
            return True

        
        #检测是否处于主页面：
        if not Back2maintitle(): return
        if not _sleep(2): return

        #出发爬塔





