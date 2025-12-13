import subprocess
import cv2
import numpy as np
import os
import sys
import time
from pathlib import Path

from .mumu_screenshot import MumuScreenshot
from .start_icon_detector import IconDetector
from .mumu_click import Tapscreen
from .show_detector import Showdetector
from .slide import Slide


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
        [秘纹升级]
            |  
            v
        [旅人升级]
            |  
            v
     [领取日常任务奖励]

    '''
    def __init__(self):
        self.screenshot_tool = MumuScreenshot()
        self.tapscreen_tool = Tapscreen()
        self.display_tool = Showdetector(output_dir="test")
        self.slide_tool = Slide()

        # 预加载所有图标检测器，避免每次运行任务时重复加载
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            tpl_dir = os.path.join(base_path, "templates")
        else:
            tpl_dir = os.path.join(os.path.dirname(__file__), "../templates")
        
        tpl_dir = os.path.abspath(tpl_dir)

        def _load(subpath):
            return IconDetector(os.path.join(tpl_dir, subpath))

        self.maintitle_detector = _load("mainTitle_icon/Market.png")
        self.market_detector = _load("mainTitle_icon/Purchasing.png")
        self.marketpagecheak_detector = _load("market/MarketPageCheak.png")
        self.commission_detector = _load("mainTitle_icon/commission_red.png")
        self.commissionpagecheak_detector = _load("commission/CommissionPageCheak.png")
        self.iscommission_detector = _load("commission/iscommission.png")
        self.commissionagain_detector = _load("commission/commission_again.png")
        self.giftpagecheak_detector = _load("gift/giftpagecheak.png")
        self.cardpagecheak_detector = _load("card/cardpagecheak.png")
        self.characterpagecheak_detector = _load("character/characterpagecheak.png")
        self.characterupgradepagecheak_detector = _load("character/upgrade.png")
        self.taskpagecheak_detector = _load("task/taskpagecheak.png")
        
        
        

    @staticmethod
    def screenshots_almost_same(img_a, img_b, pixel_threshold=3, change_ratio=0.001):
        """Return True if two screenshots are almost identical."""
        if img_a is None or img_b is None:
            return False
        if img_a.shape != img_b.shape:
            return False

        diff = cv2.absdiff(img_a, img_b)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, pixel_threshold, 255, cv2.THRESH_BINARY)
        changed_pixels = np.count_nonzero(mask)
        total_pixels = mask.size
        if total_pixels == 0:
            return False
        changed_ratio = changed_pixels / total_pixels
        return changed_ratio <= change_ratio

    
    def run(self, stop_event=None, sleep_fn=None):
        screenshot_tool = self.screenshot_tool
        tapscreen_tool = self.tapscreen_tool
        display_tool = self.display_tool
        slide_tool = self.slide_tool
        
        
        # 使用预加载的检测器
        maintitle_detector = self.maintitle_detector
        market_detector = self.market_detector
        marketpagecheak_detector = self.marketpagecheak_detector
        commission_detector = self.commission_detector
        commissionpagecheak_detector = self.commissionpagecheak_detector
        iscommission_detector = self.iscommission_detector
        commissionagain_detector = self.commissionagain_detector
        giftpagecheak_detector = self.giftpagecheak_detector
        cardpagecheak_detector = self.cardpagecheak_detector
        characterpagecheak_detector = self.characterpagecheak_detector
        characterupgradepagecheak_detector = self.characterupgradepagecheak_detector
        taskpagecheak_detector = self.taskpagecheak_detector

        def _sleep(sec):
            if sleep_fn:
                return sleep_fn(sec, stop_event)
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


        # ================== 开始执行日常任务各步骤 ==================

        
        # 主页面角色互动
        tapscreen_tool.tap_screen(646, 409)
        if not _sleep(3): return
        tapscreen_tool.tap_screen(646, 409)
        if not _sleep(3): return
        tapscreen_tool.tap_screen(646, 409)
        print("主页面角色互动完成")
        if not _sleep(2): return
        print("开始执行领取商店随机奖励")

        # 领取商店随机奖励
        screenshot1 = screenshot_tool.capture()
        (x1, y1), conf1 = market_detector.find_icon(screenshot1)  
        tapscreen_tool.tap_screen(x1, y1)
        if not _sleep(3): return

        # 检测是否已经处于采购界面
        screenshot1 = screenshot_tool.capture()
        (x2, y2), conf2 = marketpagecheak_detector.find_icon(screenshot1)
        while x2 is None:
            if stop_event and stop_event.is_set(): return
            print("正在等待进入采购界面...")
            if not _sleep(1): return
            screenshot1 = screenshot_tool.capture()
            (x2, y2), conf2 = marketpagecheak_detector.find_icon(screenshot1)

        # 点击领取随机奖励
        tapscreen_tool.tap_screen(73, 636)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(73, 636)
        if not _sleep(1): return
        print("领取商店随机奖励完成")

        # 返回主页面
        if not Back2maintitle(): return
        if not _sleep(2): return

        # 委托派遣
        print("开始执行委托派遣")
        screenshot1 = screenshot_tool.capture()
        (x4, y4), conf2 = commission_detector.find_icon(screenshot1)
        tapscreen_tool.tap_screen(x4, y4)
        if not _sleep(3): return
        screenshot1 = screenshot_tool.capture()
        (x5, y5), conf2 = commissionpagecheak_detector.find_icon(screenshot1)
        while x5 is None:
            if stop_event and stop_event.is_set(): return
            tapscreen_tool.tap_screen(x4, y4)
            if not _sleep(1): return
            screenshot1 = screenshot_tool.capture()
            (x5, y5), conf2 = commissionpagecheak_detector.find_icon(screenshot1)

        screenshot1 = screenshot_tool.capture()
        (xa, ya), conf2 = iscommission_detector.find_icon(screenshot1)
        if xa:
            print("已进入委托派遣界面")
            tapscreen_tool.tap_screen(1161, 632)
            if not _sleep(4): return
            tapscreen_tool.tap_screen(1161, 632)
            if not _sleep(1): return
            tapscreen_tool.tap_screen(68, 49)
            # 一键再次派遣
            screenshot1 = screenshot_tool.capture()
            (x6, y6), conf2 = commissionagain_detector.find_icon(screenshot1)
            while x6 is None:
                if stop_event and stop_event.is_set(): return
                tapscreen_tool.tap_screen(68, 49)
                if not _sleep(1): return
                screenshot1 = screenshot_tool.capture()
                (x6, y6), conf2 = commissionagain_detector.find_icon(screenshot1)
            tapscreen_tool.tap_screen(x6, y6)
            if not _sleep(1): return
            if not Back2maintitle(): return
        else:
            print("委托任务未完成或没有开始委托")
            if not Back2maintitle(): return

        if not _sleep(2): return

        # 赠送礼物
        print("开始执行赠送礼物")
        tapscreen_tool.tap_screen(1044, 123)
        if not _sleep(3): return
        screenshot1 = screenshot_tool.capture()
        (x7, y7), conf2 = giftpagecheak_detector.find_icon(screenshot1)
        while x7 is None:
            if stop_event and stop_event.is_set(): return
            tapscreen_tool.tap_screen(1044, 123)
            if not _sleep(1): return
            screenshot1 = screenshot_tool.capture()
            (x7, y7), conf2 = giftpagecheak_detector.find_icon(screenshot1)
        print("已进入赠送礼物界面")
        tapscreen_tool.tap_screen(398, 665)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(398, 665)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(398, 665)
        tapscreen_tool.tap_screen(690, 321)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(898, 644)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(898, 644)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(898, 644)
        if not _sleep(1): return
        # 返回主页面
        tapscreen_tool.tap_screen(1220, 49)
        if not _sleep(2): return
        screenshot1 = screenshot_tool.capture()
        (x8, y8), conf2 = maintitle_detector.find_icon(screenshot1)
        while x8 is None:
            if stop_event and stop_event.is_set(): return
            tapscreen_tool.tap_screen(1220, 49)
            if not _sleep(2): return
            screenshot1 = screenshot_tool.capture()
            (x8, y8), conf2 = maintitle_detector.find_icon(screenshot1)
        print("返回主界面完成")

        # 秘纹升级
        print("开始执行秘纹升级")
        tapscreen_tool.tap_screen(1125, 535)
        if not _sleep(3): return
        screenshot1 = screenshot_tool.capture()
        (x9, y9), conf2 = cardpagecheak_detector.find_icon(screenshot1)
        while x9 is None:
            if stop_event and stop_event.is_set(): return
            tapscreen_tool.tap_screen(1125, 535)
            if not _sleep(1): return
            screenshot1 = screenshot_tool.capture()
            (x9, y9), conf2 = cardpagecheak_detector.find_icon(screenshot1)
        print("已进入秘纹升级界面")
        # 滑动至页面底部
        screenshot_before_swipe = screenshot1
        slide_tool.swipe_up(1000)
        if not _sleep(1): return
        screenshot_after_swipe = screenshot_tool.capture()
        # 判断是否已经滑动到页面底部
        while self.screenshots_almost_same(screenshot_before_swipe, screenshot_after_swipe) is False:
            print("继续滑动")
            screenshot_before_swipe = screenshot_after_swipe
            if stop_event and stop_event.is_set(): return
            slide_tool.swipe_up(1000)
            if not _sleep(1): return
            screenshot_after_swipe = screenshot_tool.capture()
        print("已滑动至页面底部")
        if not _sleep(1): return
        # 选取左下角秘闻进行升级
        tapscreen_tool.tap_screen(191, 562)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(191, 562)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(191, 562)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(568, 661)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(568, 661)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(568, 661)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(921, 469)
        if not _sleep(1): return
        for _ in range(4):
            tapscreen_tool.tap_screen(1008, 548)
            if not _sleep(1): return
        print("秘纹升级完成")
        if not Back2maintitle(): return
        if not _sleep(2): return

        # 开始执行旅人升级
        print("开始执行旅人升级")
        tapscreen_tool.tap_screen(1039, 561)
        if not _sleep(3): return
        screenshot1 = screenshot_tool.capture()
        (x10, y10), conf2 = characterpagecheak_detector.find_icon(screenshot1)
        while x10 is None:
            if stop_event and stop_event.is_set(): return
            tapscreen_tool.tap_screen(1039, 561)
            if not _sleep(1): return
            screenshot1 = screenshot_tool.capture()
            (x10, y10), conf2 = characterpagecheak_detector.find_icon(screenshot1)
        print("已进入旅人升级界面")
        # 滑动至页面底部
        screenshot_before_swipe = screenshot1
        slide_tool.swipe_up(1000)
        if not _sleep(1): return
        screenshot_after_swipe = screenshot_tool.capture()
        # 判断是否已经滑动到页面底部
        while self.screenshots_almost_same(screenshot_before_swipe, screenshot_after_swipe) is False:
            print("继续滑动")
            screenshot_before_swipe = screenshot_after_swipe
            if stop_event and stop_event.is_set(): return
            slide_tool.swipe_up(1000)
            if not _sleep(1): return
            screenshot_after_swipe = screenshot_tool.capture()
        print("已滑动至页面底部")
        if not _sleep(1): return
        tapscreen_tool.tap_screen(173, 551)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(173, 551)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(173, 551)
        if not _sleep(1): return
        tapscreen_tool.tap_screen(1110, 522)
        if not _sleep(1): return
        screenshot1 = screenshot_tool.capture()
        (x11, y11), conf2 = characterupgradepagecheak_detector.find_icon(screenshot1)
        while x11 is None:
            if stop_event and stop_event.is_set(): return
            print("旅人升级界面未加载完成，继续点击升级按钮")
            if not _sleep(1): return
            tapscreen_tool.tap_screen(1110, 522)
            if not _sleep(1): return
            screenshot1 = screenshot_tool.capture()
            (x11, y11), conf2 = characterupgradepagecheak_detector.find_icon(screenshot1)
        tapscreen_tool.tap_screen(x11, y11)
        if not _sleep(1): return
        for _ in range(3):
            tapscreen_tool.tap_screen(1028, 590)
            if not _sleep(1): return
        print("旅人升级完成")
        if not Back2maintitle(): return
        if not _sleep(2): return

        # 领取奖励
        print("开始领取奖励")
        tapscreen_tool.tap_screen(955, 119)
        if not _sleep(3): return
        screenshot1 = screenshot_tool.capture()
        (x12, y12), conf2 = taskpagecheak_detector.find_icon(screenshot1)
        while x12 is None:
            if stop_event and stop_event.is_set(): return
            tapscreen_tool.tap_screen(955, 119)
            if not _sleep(1): return
            screenshot1 = screenshot_tool.capture()
            (x12, y12), conf2 = taskpagecheak_detector.find_icon(screenshot1)
        print("已进入任务界面")
        for _ in range(3):
            tapscreen_tool.tap_screen(1125, 591)
            if not _sleep(1): return
        for _ in range(4):
            tapscreen_tool.tap_screen(1142, 65)
            if not _sleep(1): return
        if not Back2maintitle(): return
        if not _sleep(2): return
        print("领取奖励完成")
        print("日常任务全部完成!")
        