import subprocess
import cv2
import numpy as np
import os
import time
from pathlib import Path

from core import MumuScreenshot, IconDetector, Tapscreen, Showdetector

class Dailytasks:
    '''
    日常任务：

     [主页面角色互动]
            |  
            v
     [领取商店随机奖励]
            |  
            v
        [委托派遣]
            |  
            v
      [赠送一次礼物]
            |  
            v
     [领取日常任务奖励]

    '''
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

        

        #采购图标检测
        market_template_path = os.path.join(os.path.dirname(__file__), "../templates/mainTitle_icon/Purchasing.png")
        market_detector = IconDetector(market_template_path)

        #采购界面检测
        marketpagecheak_template_path = os.path.join(os.path.dirname(__file__), "../templates/market/MarketPageCheak.png")
        marketpagecheak_detector = IconDetector(marketpagecheak_template_path)

        #商城图标检测，用于检测是否处于主页面
        maintitle_chake = os.path.join(os.path.dirname(__file__), "../templates/mainTitle_icon/Market.png")
        maintitle_detector = IconDetector(maintitle_chake)

        



        #主页面角色互动
        self.tapscreen_tool.tap_screen(646, 409)
        time.sleep(3)
        self.tapscreen_tool.tap_screen(646, 409)
        time.sleep(3)
        self.tapscreen_tool.tap_screen(646, 409)
        
        print("主页面角色互动完成")
        time.sleep(2)
        print("开始执行领取商店随机奖励")

        #领取商店随机奖励
        
        #点击采购图标
        screenshot1 = screenshot_tool.capture()
        (x1, y1), conf1 = market_detector.find_icon(screenshot1)
        self.display_tool.show_image_with_rectangle(screenshot1, (x1, y1), (x1+10, y1+10))
        tapscreen_tool.tap_screen(x1, y1)
        time.sleep(3)

        #检测是否已经处于采购界面
        screenshot1 = screenshot_tool.capture()
        (x2, y2), conf2 = marketpagecheak_detector.find_icon(screenshot1)
        while x2 is None:
            print("正在等待进入采购界面...")
            time.sleep(1)
            screenshot1 = screenshot_tool.capture()
            (x2, y2), conf2 = marketpagecheak_detector.find_icon(screenshot1)
        

        #点击领取随机奖励
        tapscreen_tool.tap_screen(73, 636)
        time.sleep(1)
        tapscreen_tool.tap_screen(73, 636)
        time.sleep(1)
        print("领取商店随机奖励完成")

        #返回主页面
        tapscreen_tool.tap_screen(66, 37)
        time.sleep(1)
        screenshot1 = screenshot_tool.capture()
        (x3, y3), conf2 = maintitle_detector.find_icon(screenshot1)
        while x3 is None:
            tapscreen_tool.tap_screen(66, 37)
            screenshot1 = screenshot_tool.capture()
            (x3, y3), conf2 = maintitle_detector.find_icon(screenshot1)
        
        print("返回主界面完成")
        time.sleep(2)
        print("开始执行委托派遣")











    
        