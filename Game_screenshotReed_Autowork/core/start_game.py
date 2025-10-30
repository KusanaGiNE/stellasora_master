import subprocess
import cv2
import numpy as np
import os
import time
from pathlib import Path


from core import MumuScreenshot, IconDetector, Tapscreen, Showdetector


class StartGame:
    def __init__(self):
        self.screenshot_tool = MumuScreenshot()
        self.tapscreen_tool = Tapscreen()
        self.display_tool = Showdetector(output_dir="test")
        

    def run(self):
        from core import MumuScreenshot, IconDetector, Tapscreen
        import os

        screenshot_tool = MumuScreenshot()
        tapscreen_tool = Tapscreen()
        display_tool = Showdetector() 

        # 识别游戏图标
        gameicon_template_path = os.path.join(os.path.dirname(__file__), "../templates/gamestart/button_template.png")
        gameicon_detector = IconDetector(gameicon_template_path)
        game_loding_template_path = os.path.join(os.path.dirname(__file__), "../templates/gamestart/game_loading.png")
        gameloding_detector = IconDetector(game_loding_template_path)
        maintitle_chake = os.path.join(os.path.dirname(__file__), "../templates/mainTitle_icon/Market.png")
        maintitle_detector = IconDetector(maintitle_chake)

        screenshot1 = screenshot_tool.capture()
        (x1, y1), conf1 = gameicon_detector.find_icon(screenshot1)
        self.display_tool.show_image_with_rectangle(screenshot1, (x1, y1), (x1+10, y1+10)) #显示识别结果
        if x1 is not None:
            tapscreen_tool.tap_screen(x1, y1)
            time.sleep(12) 
            # 等待游戏启动至登录界面
            screenshot2 = screenshot_tool.capture()
            (x2, y2), conf1 = gameloding_detector.find_icon(screenshot2)
            if x2 is None:
                print("登录界面未加载完成")
            while x2 is None:
                screenshot2 = screenshot_tool.capture()
                (x2, y2), conf1 = gameloding_detector.find_icon(screenshot2)
                print("登录界面未加载完成")
                time.sleep(1)
            
            
            self.display_tool.show_image_with_rectangle(screenshot2, (x2, y2), (x2+10, y2+10))
            time.sleep(1)
            tapscreen_tool.tap_screen(1116, 104)
            time.sleep(1)
            tapscreen_tool.tap_screen(1116, 104)
            time.sleep(1)
            tapscreen_tool.tap_screen(1116, 104)
            time.sleep(1)

            # 主页面检测
            screenshot3 = screenshot_tool.capture()
            (x3, y3), conf1 = maintitle_detector.find_icon(screenshot3)
            tapscreen_tool.tap_screen(678, 28)
            if x3 is None:
                print("未进入主页面")
            while x3 is None:
                screenshot3 = screenshot_tool.capture()
                (x3, y3), conf1 = maintitle_detector.find_icon(screenshot3)
                print("未进入主页面")
                tapscreen_tool.tap_screen(678, 28)
                time.sleep(1)
            
            print("已进入主页面")
            

        else:
            
            print("未找到游戏图标")
        

