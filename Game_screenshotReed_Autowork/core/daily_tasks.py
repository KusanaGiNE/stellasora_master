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
from .config import get_config
from .base_task import BaseTask


class Dailytasks(BaseTask):
    '''
    日常任务：
    ...
    '''
    def __init__(self):
        super().__init__()
        self.display_tool = Showdetector(output_dir="test")
        # self.slide_tool = Slide() # Moved to BaseTask

    # 使用 property 实现懒加载，用到时才读取图片
    @property
    def maintitle_detector(self): return self.load_detector("mainTitle_icon/Market.png")
    @property
    def market_detector(self): return self.load_detector("mainTitle_icon/Purchasing.png")
    @property
    def marketpagecheak_detector(self): return self.load_detector("market/MarketPageCheak.png")
    @property
    def commission_detector(self): return self.load_detector("mainTitle_icon/commission_red.png")
    @property
    def commissionpagecheak_detector(self): return self.load_detector("commission/CommissionPageCheak.png")
    @property
    def iscommission_detector(self): return self.load_detector("commission/iscommission.png")
    @property
    def commissionagain_detector(self): return self.load_detector("commission/commission_again.png")
    @property
    def giftpagecheak_detector(self): return self.load_detector("gift/giftpagecheak.png")
    @property
    def cardpagecheak_detector(self): return self.load_detector("card/cardpagecheak.png")
    @property
    def characterpagecheak_detector(self): return self.load_detector("character/characterpagecheak.png")
    @property
    def characterupgradepagecheak_detector(self): return self.load_detector("character/upgrade.png")
    @property
    def taskpagecheak_detector(self): return self.load_detector("task/taskpagecheak.png")
    @property
    def confirm_detector(self): return self.load_detector("charactercard/icon/confirm.png")
    @property
    def select_detector(self): return self.load_detector("charactercard/icon/select.png")
    @property
    def sendgift_detector(self): return self.load_detector("charactercard/icon/sendgift.png")
    @property
    def skip_detector(self): return self.load_detector("charactercard/icon/skip.png")
    @property
    def invitation_detector(self): return self.load_detector("charactercard/icon/invitationpagecheak.png")

    # 角色卡加载
    @property
    def c_xiaohe_detector(self): return self.load_detector("charactercard/xiaohe.png")
    @property
    def c_xiya_detector(self): return self.load_detector("charactercard/xiya.png")
    @property
    def c_wuyu_detector(self): return self.load_detector("charactercard/wuyu.png")
    @property
    def c_gerui_detector(self): return self.load_detector("charactercard/gerui.png")
    @property
    def c_canglan_detector(self): return self.load_detector("charactercard/canglan.png")
    @property
    def c_lingchuan_detector(self): return self.load_detector("charactercard/lingchuan.png")
    @property
    def c_qiandushi_detector(self): return self.load_detector("charactercard/qiandushi.png")
    @property
    def c_chensha_detector(self): return self.load_detector("charactercard/chensha.png")
    @property
    def c_yuanwei_detector(self): return self.load_detector("charactercard/yuanwei.png")
    @property
    def c_shimiao_detector(self): return self.load_detector("charactercard/shimiao.png")
    @property
    def c_lalu_shengye_detector(self): return self.load_detector("charactercard/lalu_shengye.png")
    @property
    def c_miniewa_detector(self): return self.load_detector("charactercard/miniewa.png")
    @property
    def c_dongxiang_detector(self): return self.load_detector("charactercard/dongxiang.png")
    @property
    def c_huayuan_detector(self): return self.load_detector("charactercard/huayuan.png")
    @property
    def c_chixia_detector(self): return self.load_detector("charactercard/chixia.png")
    @property
    def c_jiaotang_detector(self): return self.load_detector("charactercard/jiaotang.png")
    @property
    def c_kesaite_detector(self): return self.load_detector("charactercard/kesaite.png")
    @property
    def c_xiahua_detector(self): return self.load_detector("charactercard/xiahua.png")
    @property
    def c_zijin_detector(self): return self.load_detector("charactercard/zijin.png")
    @property
    def c_kanasi_detector(self): return self.load_detector("charactercard/kanasi.png")
    @property
    def c_keluonisi_detector(self): return self.load_detector("charactercard/keluonisi.png")
    @property
    def c_jinlin_detector(self): return self.load_detector("charactercard/jinlin.png")
    @property
    def c_kaximila_detector(self): return self.load_detector("charactercard/kaximila.png")
    @property
    def c_tilya_detector(self): return self.load_detector("charactercard/tiliya.png")
    @property
    def c_lalu_detector(self): return self.load_detector("charactercard/lalu.png")
    @property
    def c_hupo_detector(self): return self.load_detector("charactercard/hupo.png")
    @property
    def c_telisha_detector(self): return self.load_detector("charactercard/telisha.png")
    @property
    def c_xingzi_detector(self): return self.load_detector("charactercard/xingzi.png")
        
    def run(self, stop_event=None, sleep_fn=None, selected_tasks=None, invitation_characters=None):
        # 开启截图流，提高效率
        self.screenshot_tool.start_stream()
        try:
            self._run_internal(stop_event, sleep_fn, selected_tasks, invitation_characters)
        finally:
            self.screenshot_tool.stop_stream()

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
        
        # Debug log to help adjust threshold
        # print(f"Debug: Diff ratio {changed_ratio:.6f} (Threshold: {change_ratio})")
        
        return changed_ratio <= change_ratio

    def _run_internal(self, stop_event, sleep_fn, selected_tasks, invitation_characters):
        screenshot_tool = self.screenshot_tool
        tapscreen_tool = self.tapscreen_tool
        display_tool = self.display_tool
        slide_tool = self.slide_tool
        
        if selected_tasks is None:
            selected_tasks = ['interaction', 'market_reward', 'commission', 'gift', 'card_upgrade', 'character_upgrade', 'task_reward']
        
        # region使用预加载的检测器
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
        confirm_detector = self.confirm_detector
        select_detector = self.select_detector
        sendgift_detector = self.sendgift_detector
        skip_detector = self.skip_detector
        invitation_detector = self.invitation_detector



        c_xiaohe_detector = self.c_xiaohe_detector
        c_xiya_detector = self.c_xiya_detector
        c_wuyu_detector = self.c_wuyu_detector
        c_gerui_detector = self.c_gerui_detector
        c_canglan_detector = self.c_canglan_detector
        c_lingchuan_detector = self.c_lingchuan_detector
        c_qiandushi_detector = self.c_qiandushi_detector
        c_chensha_detector = self.c_chensha_detector
        c_yuanwei_detector = self.c_yuanwei_detector
        c_shimiao_detector = self.c_shimiao_detector
        c_lalu_shengye_detector = self.c_lalu_shengye_detector
        c_miniewa_detector = self.c_miniewa_detector
        c_dongxiang_detector = self.c_dongxiang_detector
        c_huayuan_detector = self.c_huayuan_detector
        c_chixia_detector = self.c_chixia_detector
        c_jiaotang_detector = self.c_jiaotang_detector
        c_kesaite_detector = self.c_kesaite_detector
        c_xiahua_detector = self.c_xiahua_detector
        c_zijin_detector = self.c_zijin_detector
        c_kanasi_detector = self.c_kanasi_detector
        c_keluonisi_detector = self.c_keluonisi_detector
        c_jinlin_detector = self.c_jinlin_detector
        c_kaximila_detector = self.c_kaximila_detector
        c_tilya_detector = self.c_tilya_detector
        c_lalu_detector = self.c_lalu_detector
        c_hupo_detector = self.c_hupo_detector
        c_telisha_detector = self.c_telisha_detector
        c_xingzi_detector = self.c_xingzi_detector
        



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
                if not _sleep(2): return
                screenshot1 = screenshot_tool.capture()
                (x3, y3), conf2 = maintitle_detector.find_icon(screenshot1)
            print("返回主界面完成")
            if not _sleep(2): return False
            return True


        # ================== 开始执行日常任务各步骤 ==================

        
        # region主页面角色互动
        if 'interaction' in selected_tasks:
            tapscreen_tool.tap_screen(646, 409)
            if not _sleep(3): return
            tapscreen_tool.tap_screen(646, 409)
            if not _sleep(3): return
            tapscreen_tool.tap_screen(646, 409)
            print("主页面角色互动完成")
            if not _sleep(2): return

        # region领取商店随机奖励
        if 'market_reward' in selected_tasks:
            print("开始执行领取商店随机奖励")
            
            # 使用 click_until_appear 替换原有的 tap + sleep
            # 尝试点击“商店入口”，直到检测到“采购界面”
            success = self.click_until_appear(
                target_detector=market_detector,
                expected_detector=marketpagecheak_detector,
                max_retry=10,
                interval=1.0,
                stop_event=stop_event
            )
            if not success:
                print("进入商店失败，跳过此任务")
                if stop_event and stop_event.is_set(): return
            else:
                # 点击领取随机奖励
                # 这里也可以优化，假设点击后会有弹窗或按钮变灰，暂时保留硬编码点击
                tapscreen_tool.tap_screen(73, 636)
                if not _sleep(1): return
                tapscreen_tool.tap_screen(73, 636)
                if not _sleep(1): return
                print("领取商店随机奖励完成")

                # 返回主页面
                if not Back2maintitle(): return
                if not _sleep(2): return

        # region委托派遣
        if 'commission' in selected_tasks:
            print("开始执行委托派遣")
            
            # 使用 click_until_appear 进入委托界面
            success = self.click_until_appear(
                target_detector=commission_detector,
                expected_detector=commissionpagecheak_detector,
                max_retry=10,
                interval=1.0,
                stop_event=stop_event
            )
            
            if success:
                screenshot1 = screenshot_tool.capture()
                (xa, ya), conf2 = iscommission_detector.find_icon(screenshot1)
                if xa:
                    print("已进入委托派遣界面")
                    tapscreen_tool.tap_screen(1161, 632)
                    if not _sleep(4): return
                    tapscreen_tool.tap_screen(1161, 632)
                    if not _sleep(1): return
                    
                    # 点击一键再次派遣，直到检测到再次派遣按钮出现（这里逻辑有点怪，原代码是点击(68,49)直到commissionagain出现）
                    # 假设(68,49)是某个触发按钮
                    # 这里可以用 click_until_appear 的变体，或者手动循环
                    # 原逻辑：点击(68,49) -> 等待 commissionagain_detector
                    
                    # 尝试点击左上角(68,49)，直到“再次派遣”按钮出现
                    # 由于(68,49)没有对应的detector，我们只能手动调用tap
                    found_again = False
                    for _ in range(10):
                        if stop_event and stop_event.is_set(): return
                        tapscreen_tool.tap_screen(68, 49)
                        if not _sleep(1): return
                        screenshot1 = screenshot_tool.capture()
                        (x6, y6), conf2 = commissionagain_detector.find_icon(screenshot1)
                        if x6:
                            tapscreen_tool.tap_screen(x6, y6)
                            found_again = True
                            break
                    
                    if found_again:
                        if not _sleep(1): return
                        if not Back2maintitle(): return
                else:
                    print("委托任务未完成或没有开始委托")
                    if not Back2maintitle(): return
            else:
                print("进入委托界面失败")

            if not _sleep(2): return

        # region赠送礼物
        if 'gift' in selected_tasks:
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
                if not _sleep(3): return
                screenshot1 = screenshot_tool.capture()
                (x8, y8), conf2 = maintitle_detector.find_icon(screenshot1)
            print("返回主界面完成")

        # region邀约
        if 'invitation' in selected_tasks:
            print("开始执行邀约")
            
            # 角色映射表
            char_map = {
                'xiaohe': self.c_xiaohe_detector,
                'xiya': self.c_xiya_detector,
                'wuyu': self.c_wuyu_detector,
                'gerui': self.c_gerui_detector,
                'canglan': self.c_canglan_detector,
                'lingchuan': self.c_lingchuan_detector,
                'qiandushi': self.c_qiandushi_detector,
                'chensha': self.c_chensha_detector,
                'yuanwei': self.c_yuanwei_detector,
                'shimiao': self.c_shimiao_detector,
                'lalu_shengye': self.c_lalu_shengye_detector,
                'miniewa': self.c_miniewa_detector,
                'dongxiang': self.c_dongxiang_detector,
                'huayuan': self.c_huayuan_detector,
                'chixia': self.c_chixia_detector,
                'jiaotang': self.c_jiaotang_detector,
                'kesaite': self.c_kesaite_detector,
                'xiahua': self.c_xiahua_detector,
                'zijin': self.c_zijin_detector,
                'kanasi': self.c_kanasi_detector,
                'keluonisi': self.c_keluonisi_detector,
                'jinlin': self.c_jinlin_detector,
                'kaximila': self.c_kaximila_detector,
                'tilya': self.c_tilya_detector,
                'lalu': self.c_lalu_detector,
                'hupo': self.c_hupo_detector,
                'telisha': self.c_telisha_detector,
                'xingzi': self.c_xingzi_detector
            }

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
            tapscreen_tool.tap_screen(274, 651)
            if not _sleep(1): return
            (xb, yb), confb = invitation_detector.find_icon(screenshot1)
            while xb is None:
                tapscreen_tool.tap_screen(274, 651)
                screenshot1 = screenshot_tool.capture()
                (xb, yb), confb = invitation_detector.find_icon(screenshot1)

            if invitation_characters:
                for char_key in invitation_characters:
                    if not char_key: continue
                    if stop_event and stop_event.is_set(): return

                    detector = char_map.get(char_key)
                    if detector:
                        
                        
                        # 1.回到顶部
                        print("正在返回列表顶部...")
                        for i in range(15): # 防止死循环，最大尝试15次
                            if stop_event and stop_event.is_set(): return
                            screenshot_before = screenshot_tool.capture()
                            slide_tool.swipe_down(271)
                            if not _sleep(2): return
                            screenshot_after = screenshot_tool.capture()
                            
                            # Debug info: 使用更宽松的阈值 (0.01 = 1%) 以容忍背景动画
                            # 如果是静态画面，差异通常极小。如果是滚动，差异通常很大。
                            is_same = self.screenshots_almost_same(screenshot_before, screenshot_after, change_ratio=0.01)
                            
                            # 计算并打印实际差异率以便调试
                            diff = cv2.absdiff(screenshot_before, screenshot_after)
                            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                            _, mask = cv2.threshold(gray, 3, 255, cv2.THRESH_BINARY)
                            ratio = np.count_nonzero(mask) / mask.size
                            print(f"Debug: 返回顶部滑动第 {i+1} 次, 画面变化率: {ratio:.6f}")

                            if is_same:
                                print("画面变化小于阈值，判定已到达顶部")
                                break
                        print("已到达列表顶部")
                        print(f"正在寻找角色: {char_key}")

                        # 2. 查找角色
                        found = False
                        for _ in range(20): # 防止死循环
                            if stop_event and stop_event.is_set(): return
                            
                            screenshot1 = screenshot_tool.capture()
                            (xc, yc), conf = detector.find_icon(screenshot1)
                            
                            if xc:
                                found = True
                                break
                            
                            # 当前页未找到，尝试向下滑动
                            print(f"当前页未找到 {char_key}，尝试滑动...")
                            screenshot_before = screenshot1
                            slide_tool.swipe_up(271)
                            if not _sleep(1.5): return
                            screenshot_after = screenshot_tool.capture()
                            
                            # Debug info
                            diff = cv2.absdiff(screenshot_before, screenshot_after)
                            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                            _, mask = cv2.threshold(gray, 3, 255, cv2.THRESH_BINARY)
                            ratio = np.count_nonzero(mask) / mask.size
                            print(f"Debug: 查找角色滑动, 画面变化率: {ratio:.6f}")

                            # 判断是否到底
                            if self.screenshots_almost_same(screenshot_before, screenshot_after, change_ratio=0.01):
                                print(f"已滑动至底部，仍未找到角色: {char_key}")
                                break

                        if found:
                            print(f"找到角色 {char_key}")
                            # 1. 点击角色
                            tapscreen_tool.tap_screen(xc, yc)
                            if not _sleep(1): return

                            # 2. 点击进入邀约 -> 等待确认邀约
                            if not self.click_until_appear(target_pos=(895, 647), expected_detector=confirm_detector, max_retry=2, stop_event=stop_event):
                                print(f"进入邀约失败: {char_key}")
                                continue

                            # 3. 点击确认邀约 -> 等待选择
                            if not self.click_until_appear(target_detector=confirm_detector, expected_detector=select_detector, stop_event=stop_event):
                                print(f"确认邀约失败: {char_key}")
                                continue

                            # 4. 处理剧情（点击选择 -> 跳过 -> 送礼）
                            print("正在处理剧情...")
                            gift_found = False
                            for _ in range(20): # Max retry
                                if stop_event and stop_event.is_set(): return
                                screenshot = screenshot_tool.capture()
                                
                                # 检查送礼按钮
                                (xg, yg), _ = sendgift_detector.find_icon(screenshot)
                                if xg:
                                    gift_found = True
                                    break
                                
                                # 检查跳过按钮
                                (xskip, yskip), _ = skip_detector.find_icon(screenshot)
                                if xskip:
                                    print("点击跳过")
                                    tapscreen_tool.tap_screen(xskip, yskip)
                                    _sleep(1)
                                    continue
                                
                                # 检查选择按钮
                                (xs, ys), _ = select_detector.find_icon(screenshot)
                                if xs:
                                    print("点击选择")
                                    tapscreen_tool.tap_screen(xs, ys)
                                    _sleep(1)
                                    continue
                                
                                _sleep(0.5)

                            if not gift_found:
                                print(f"剧情处理超时: {char_key}")
                                continue

                            # 5. 送礼流程
                            # 此时 xg, yg 是送礼按钮坐标
                            tapscreen_tool.tap_screen(xg, yg)
                            if not _sleep(1): return
                            
                            tapscreen_tool.tap_screen(805, 292) # 选择礼物
                            if not _sleep(0.5): return
                            
                            tapscreen_tool.tap_screen(1099, 633) # 点击赠送
                            
                            # 6. 等待赠送完成并返回
                            # 等待5秒动画
                            if not _sleep(5): return
                            
                            # 点击返回直到回到邀约列表
                            if not self.click_until_appear(target_pos=(659, 615), expected_detector=invitation_detector, max_retry=15, stop_event=stop_event):
                                print(f"返回邀约列表失败: {char_key}")
                            
                            print(f"邀约角色 {char_key} 完成")
                            if not _sleep(1): return
                        else:
                            print(f"未找到角色: {char_key}")
                
                # 返回主页面
                tapscreen_tool.tap_screen(1220, 49)
                if not _sleep(2): return
                screenshot1 = screenshot_tool.capture()
                (x8, y8), conf2 = maintitle_detector.find_icon(screenshot1)
                while x8 is None:
                    if stop_event and stop_event.is_set(): return
                    tapscreen_tool.tap_screen(1220, 49)
                    if not _sleep(3): return
                    screenshot1 = screenshot_tool.capture()
                    (x8, y8), conf2 = maintitle_detector.find_icon(screenshot1)
                print("返回主界面完成")
            
            if not _sleep(1): return

        # region秘纹升级
        if 'card_upgrade' in selected_tasks:
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
                if not _sleep(2): return
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

        # region开始执行旅人升级
        if 'character_upgrade' in selected_tasks:
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
                if not _sleep(2): return
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

        # region领取奖励
        if 'task_reward' in selected_tasks:
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
        