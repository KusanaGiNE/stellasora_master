import subprocess
import cv2
import numpy as np
import os
import time
from pathlib import Path
import sys

from core import MumuScreenshot, IconDetector, Tapscreen, Showdetector
from .config import get_config


class StartGame:
    def __init__(self):
        self.screenshot_tool = MumuScreenshot()
        self.tapscreen_tool = Tapscreen()
        self.display_tool = Showdetector(output_dir="test")

    def run(self, stop_event=None, sleep_fn=None):
        """支持 stop_event; sleep_fn(seconds, stop_event)."""
        screenshot_tool = self.screenshot_tool
        tapscreen_tool = self.tapscreen_tool
        display_tool = self.display_tool

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

        config = get_config()
        lang = config.get("server_lang", "zh-CN")
        folder_name = f"templates_{lang}"

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            tpl_dir = os.path.join(base_path, folder_name)
        else:
            tpl_dir = os.path.join(os.path.dirname(__file__), f"../{folder_name}")
        
        tpl_dir = os.path.abspath(tpl_dir)

        # 识别游戏图标
        gameicon_template_path = os.path.join(tpl_dir, "gamestart/button_template.png")
        gameicon_detector = IconDetector(gameicon_template_path)
        game_loding_template_path = os.path.join(tpl_dir, "gamestart/game_loading.png")
        gameloding_detector = IconDetector(game_loding_template_path)
        maintitle_chake = os.path.join(tpl_dir, "mainTitle_icon/Market.png")
        maintitle_detector = IconDetector(maintitle_chake)

        if stop_event and stop_event.is_set():
            return
        screenshot1 = screenshot_tool.capture()
        (x1, y1), conf1 = gameicon_detector.find_icon(screenshot1)
        # 仅在识别到坐标时才绘制矩形，避免 None 与整数相加报错
        if x1 is not None and y1 is not None:
            self.display_tool.show_image_with_rectangle(screenshot1, (x1, y1), (x1+10, y1+10))  # 显示识别结果
        else:
            print("游戏图标未识别到，跳过标记展示")
        if x1 is not None:
            tapscreen_tool.tap_screen(x1, y1)
            if not _sleep(12):
                return
            # 等待游戏启动至登录界面
            screenshot2 = screenshot_tool.capture()
            (x2, y2), conf1 = gameloding_detector.find_icon(screenshot2)
            if x2 is None:
                print("登录界面未加载完成")
            while x2 is None:
                if stop_event and stop_event.is_set():
                    return
                screenshot2 = screenshot_tool.capture()
                (x2, y2), conf1 = gameloding_detector.find_icon(screenshot2)
                print("登录界面未加载完成")
                if not _sleep(1): return
            
            
            self.display_tool.show_image_with_rectangle(screenshot2, (x2, y2), (x2+10, y2+10))
            if not _sleep(1): return
            for _ in range(3):
                tapscreen_tool.tap_screen(1116, 104)
                if not _sleep(1): return

            # 主页面检测
            screenshot3 = screenshot_tool.capture()
            (x3, y3), conf1 = maintitle_detector.find_icon(screenshot3)
            tapscreen_tool.tap_screen(678, 28)
            if x3 is None:
                print("未进入主页面")
            while x3 is None:
                if stop_event and stop_event.is_set():
                    return
                screenshot3 = screenshot_tool.capture()
                (x3, y3), conf1 = maintitle_detector.find_icon(screenshot3)
                print("未进入主页面")
                tapscreen_tool.tap_screen(678, 28)
                if not _sleep(1): return
            
            print("已进入主页面")
            

        else:
            print("未找到游戏图标")
        

