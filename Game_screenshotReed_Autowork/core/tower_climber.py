import subprocess
import cv2
import numpy as np
import os
import sys
import time

from pathlib import Path
from core import OcrTool
from .mumu_screenshot import MumuScreenshot
from .start_icon_detector import IconDetector
from .mumu_click import Tapscreen
from .show_detector import Showdetector
from .slide import Slide
from .config import get_config


from .base_task import BaseTask

class TowerClimber(BaseTask):
    def __init__(self):
        super().__init__()
        self.display_tool = Showdetector(output_dir="tower_climber_test")
        self.ocr_tool = OcrTool()
        self.slide_tool = Slide()

        # region图标识别器预加载
        self.maintitle_detector = self.load_detector("mainTitle_icon/Market.png")
        self.market_detector = self.load_detector("mainTitle_icon/Purchasing.png")
        self.tower_detector = self.load_detector("tower_climber/tower.png")
        self.recommend_detector = self.load_detector("tower_climber/recommend.png") #推荐卡牌检测器
        self.musicnoteget_detector = self.load_detector("tower_climber/musicnoteget.png") #音符获取检测器
        self.skillactivate_detector = self.load_detector("tower_climber/skillactivate.png") #协奏技能激活检测器
        self.talk_detector = self.load_detector("tower_climber/talk.png") #对话检测器
        self.skipshopping_detector = self.load_detector("tower_climber/skipshopping.png") #跳过购买检测器
        self.quittower_detector = self.load_detector("tower_climber/quittower.png") #退出爬塔检测器
        self.formationpagecheak_detector = self.load_detector("tower_climber/formationpagecheak.png") #编成页面检测器 
        self.cancel_detector = self.load_detector("tower_climber/cancel.png") #取消按钮检测器
        self.savepagecheak_detector = self.load_detector("tower_climber/delete.png") #保存页面检测器
        self.quickclimb_detector = self.load_detector("tower_climber/quickclimb.png") #快速爬塔检测器
        self.giveupticket_detector = self.load_detector("tower_climber/giveup.png") #检测是否有未完成的爬塔记录
        self.discount_detector = self.load_detector("tower_climber/discount.png") #优惠商品检测器
        self.buy_detector = self.load_detector("tower_climber/buy.png") #购买按钮检测器
        self.buypagecheak_detector = self.load_detector("tower_climber/buypagecheak.png") #购买页面检测器
        self.islocked_detector = self.load_detector("tower_climber/islocked.png") #检测是否锁定

    # Removed local click_until_appear to use BaseTask's implementation
    
    def find_multi_icons(self, screenshot, detector, threshold=0.85, min_dist=30, target_width=1280):
        """
        在截图中查找所有匹配的图标，支持分辨率适配
        """
        if screenshot is None or detector is None:
            return []

        try:
            template = detector.template 
        except AttributeError:
           
            if hasattr(detector, 'image_path'):
                template = cv2.imread(detector.image_path)
            else:
                print("Error: 无法获取检测器模板图片")
                return []

        if template is None:
            return []

        # 分辨率适配
        h_img, w_img = screenshot.shape[:2]
        scale_ratio = 1.0
        if abs(w_img - target_width) > 10:
            scale_ratio = target_width / w_img
            new_h = int(h_img * scale_ratio)
            screenshot_resized = cv2.resize(screenshot, (target_width, new_h))
        else:
            screenshot_resized = screenshot

        h, w = template.shape[:2]
        # 检查大小
        if screenshot_resized.shape[0] < h or screenshot_resized.shape[1] < w:
             return []

        res = cv2.matchTemplate(screenshot_resized, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        
        points = []
        for pt in zip(*loc[::-1]):  
            center_x = int(pt[0] + w / 2)
            center_y = int(pt[1] + h / 2)
            # 还原坐标
            final_x = int(center_x / scale_ratio)
            final_y = int(center_y / scale_ratio)
            points.append((final_x, final_y))

        filtered_points = []
        for p in points:
            is_close = False
            for fp in filtered_points:
                dist = ((p[0] - fp[0])**2 + (p[1] - fp[1])**2)**0.5
                if dist < min_dist:
                    is_close = True
                    break
            if not is_close:
                filtered_points.append(p)
                
        return filtered_points

    def run(self, attribute_type=None, max_runs=0, stop_on_weekly=True, stop_event=None, sleep_fn=None, climb_type= None):
        self.screenshot_tool.start_stream()
        try:
            self._run_internal(attribute_type, max_runs, stop_on_weekly, stop_event, sleep_fn, climb_type)
        finally:
            self.screenshot_tool.stop_stream()

    def _run_internal(self, attribute_type, max_runs, stop_on_weekly, stop_event, sleep_fn, climb_type):
        """
        支持 stop_event; sleep_fn(seconds, stop_event).
        :param attribute_type: 'light_earth' | 'water_wind' | 'fire_dark'
        :param max_runs: 指定爬塔次数，0为不限
        :param stop_on_weekly: 是否在周常完成后停止 (默认True)
        """
        #if climb_type not in ['quick', 'standard']:
            #climb_type = 'standard'

        print(f"启动爬塔任务，目标属性: {attribute_type}, 爬塔模式：{climb_type},次数: {max_runs}, 周常停止: {stop_on_weekly}")
        if attribute_type is None:
            print("警告: 未收到属性类型，将跳过属性选择步骤")
        
        screenshot_tool = self.screenshot_tool
        tapscreen_tool = self.tapscreen_tool
        display_tool = self.display_tool
        ocr_tool = self.ocr_tool
        slide_tool = self.slide_tool

        # region用预加载的检测器
        maintitle_detector = self.maintitle_detector
        market_detector = self.market_detector
        recommend_detector = self.recommend_detector
        musicnoteget_detector = self.musicnoteget_detector
        skillactivate_detector = self.skillactivate_detector
        talk_detector = self.talk_detector
        skipshopping_detector = self.skipshopping_detector
        quittower_detector = self.quittower_detector
        formationpagecheak_detector = self.formationpagecheak_detector
        savepagecheak_detector = self.savepagecheak_detector
        quickclimb_detector = self.quickclimb_detector
        giveupticket_detector = self.giveupticket_detector
        discount_detector = self.discount_detector
        buy_detector = self.buy_detector
        buypagecheak_detector = self.buypagecheak_detector
        islocked_detector = self.islocked_detector
        cancel_detector = self.cancel_detector
        

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
            screenshot1 = screenshot_tool.capture()
            (x3, y3), conf2 = maintitle_detector.find_icon(screenshot1)
            while x3 is None:
                if stop_event and stop_event.is_set(): return False
                tapscreen_tool.tap_screen(66, 37)
                if not _sleep(1): return False
                screenshot1 = screenshot_tool.capture()
                (x3, y3), conf2 = maintitle_detector.find_icon(screenshot1)
            print("返回主界面完成")
            if not _sleep(2): return False
            return True
        
        #检查电梯票数量
        def check_tickets():
            screenshot = screenshot_tool.capture()
            
            ticket_num = ocr_tool.recognize_number(screenshot, region=(1200, 39, 41, 20))
            print(f"当前电梯票数量: {ticket_num}")
            return ticket_num

        #检查奖励完成情况
        def check_weekly_progress():
            screenshot = screenshot_tool.capture()
            progress = ocr_tool.recognize_number(screenshot, region=(481, 641, 67, 22)) 
            print(f"每周奖励完成情况: {progress}/3000")
            return progress
        
        #检测是否处于主页面：
        if not Back2maintitle(): return
        if not _sleep(2): return

        #region出发爬塔
        # 使用 click_until_appear 尝试进入爬塔界面
        # 目标：点击(1158, 637)（出发按钮？），直到检测到 tower_detector
        # 由于出发按钮没有detector，我们只能手动循环，或者创建一个临时的“虚拟detector”
        # 但 click_until_appear 支持 target_detector=None，我们可以手动点击
        
        print("尝试进入爬塔界面...")
        entered_tower = False
        for _ in range(5):
            if stop_event and stop_event.is_set(): return
            tapscreen_tool.tap_screen(1158, 637)
            if not _sleep(2): return # 稍微等待界面加载
            
            screenshot = screenshot_tool.capture()
            (x_tower, y_tower), conf_tower = self.tower_detector.find_icon(screenshot)
            if x_tower is not None:
                entered_tower = True
                # 点击塔
                tapscreen_tool.tap_screen(x_tower, y_tower)
                if not _sleep(3): return
                break
        
        if not entered_tower:
            print("未能进入爬塔界面")
            return

        screenshot = screenshot_tool.capture()
        (x_giveup, y_giveup), conf_giveup = giveupticket_detector.find_icon(screenshot)
        if x_giveup is not None:
            print("检测到有未完成的爬塔记录，终止爬塔")
            Back2maintitle()
            return
            
        

        # 循环执行爬塔
        run_count = 0
        while True:
            if stop_event and stop_event.is_set():
                print("收到停止信号，退出爬塔")
                break

            # 1. 检查次数限制
            if max_runs > 0 and run_count >= max_runs:
                print(f"已达到指定次数 {max_runs}，结束任务")
                break
            
            # 2. 检查周常 (假设在进入塔后的界面可以看到进度，或者需要返回上一级查看)
            # 由于不知道具体界面布局，这里假设在当前界面可以检查，或者在每次战斗前检查
            if stop_on_weekly:
                progress = check_weekly_progress()
                if progress >= 3000:
                    print("周常任务已完成，结束任务")
                    break
            #region选择属性

            if attribute_type == 'light_earth':
                tapscreen_tool.tap_screen(288, 139)
                if not _sleep(2): return
            elif attribute_type == 'water_wind':
                tapscreen_tool.tap_screen(288, 274)
                if not _sleep(2): return
            elif attribute_type == 'fire_dark':
                tapscreen_tool.tap_screen(288, 402)
                if not _sleep(2): return

            tapscreen_tool.tap_screen(956, 600) #进入选的的属性塔
            if not _sleep(2): return
                

            # 3. 检查票数
            ticket_num = check_tickets()
            if ticket_num == 0:
                print("电梯票数量为0，结束爬塔任务")
                break

            print(f"=== 开始第 {run_count + 1} 次爬塔 ===")
            
            # region开始爬塔流程
            screenshot = screenshot_tool.capture()
            (x_quick, y_quick), conf_quick = quickclimb_detector.find_icon(screenshot)
            if x_quick is None:
                print("未检测到快速爬塔选项，终止任务")
                break
            tapscreen_tool.tap_screen(x_quick, y_quick)  # 点击快速爬塔
            if not _sleep(2): return
            screenshot = screenshot_tool.capture()
            (x_forma, y_forma), conf_forma = formationpagecheak_detector.find_icon(screenshot)
            while x_forma is  None:
                tapscreen_tool.tap_screen(900, 650)  # 点击开始爬塔
                if not _sleep(3): return
                screenshot = screenshot_tool.capture()
                (x_forma, y_forma), conf_forma = formationpagecheak_detector.find_icon(screenshot)
            print("进入编成页面")

            tapscreen_tool.tap_screen(954, 666)  # 旅人自动编成
            if not _sleep(2): return
            
            screenshot = screenshot_tool.capture()
            (x_cancel, y_cancel), conf_cancel = cancel_detector.find_icon(screenshot)
            if x_cancel is not None:
                tapscreen_tool.tap_screen(x_cancel, y_cancel)  # 点击取消
                if not _sleep(2): return
            tapscreen_tool.tap_screen(1158, 662)  #下一步
            if not _sleep(3): return
            tapscreen_tool.tap_screen(954, 666)  # 秘纹自动编成
            if not _sleep(2): return
            screenshot = screenshot_tool.capture()
            (x_cancel, y_cancel), conf_cancel = cancel_detector.find_icon(screenshot)
            if x_cancel is not None:
                tapscreen_tool.tap_screen(x_cancel, y_cancel)  # 点击取消
                if not _sleep(2): return
            tapscreen_tool.tap_screen(1158, 662)  #开始战斗
            if not _sleep(3): return


            #region爬塔主体逻辑
            while True:

                if stop_event and stop_event.is_set():
                    print("收到停止信号，退出爬塔")
                    return
                
                screenshot = screenshot_tool.capture()
                (x_quit, y_quit), conf_quit = quittower_detector.find_icon(screenshot)
                if x_quit is not None:
                    if climb_type == 'standard':  #标准爬塔模式:购买，强化
                        tapscreen_tool.tap_screen(657, 280) #点击进入商店
                        if not _sleep(2): return

                        print("正在扫描优惠商品...")
                        screenshot = screenshot_tool.capture()
                        discount_points = self.find_multi_icons(screenshot, self.discount_detector)
                        
                        if discount_points:
                            print(f"发现 {len(discount_points)} 个优惠商品，开始购买")
                            for idx, (dx, dy) in enumerate(discount_points):
                                if stop_event and stop_event.is_set(): return
                                print(f"购买第 {idx + 1} 个优惠商品: ({dx}, {dy})")
                                tapscreen_tool.tap_screen(dx, dy) 
                                if not _sleep(2): return # 点击间隔
                                screenshot = screenshot_tool.capture()
                                (x_buy, y_buy), conf_buy = self.buy_detector.find_icon(screenshot)
                                if x_buy is not None:
                                    tapscreen_tool.tap_screen(x_buy, y_buy)  # 点击购买按钮
                                    if not _sleep(2): return
                                    
                                    # 引入计数器，实现动态等待
                                    no_response_count = 0
                                    
                                    while True:
                                        if stop_event and stop_event.is_set():
                                            print("收到停止信号，退出爬塔")
                                            return
                                        
                                        screenshot = screenshot_tool.capture()
                                        (x_buycheak, y_buycheak), conf_buycheak = buypagecheak_detector.find_icon(screenshot)
                                        if x_buycheak is not None:
                                            break # 购买成功，退出循环

                                        (x_reco, y_reco), conf_reco = recommend_detector.find_icon(screenshot)
                                        if x_reco is not None:
                                            print("检测到推荐卡牌页面，进行选择")
                                            tapscreen_tool.tap_screen(x_reco, y_reco)  # 点击推荐卡
                                            if not _sleep(2): return
                                            tapscreen_tool.tap_screen(x_reco+129, y_reco+193)  # 确认选择
                                            if not _sleep(3): return
                                            no_response_count = 0 # 重置计数器
                                            continue    
                                        (x_music, y_music), conf_music = musicnoteget_detector.find_icon(screenshot)
                                        if x_music is not None:
                                            print("检测到音符获取页面，执行点击")
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(2): return
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(3): return
                                            no_response_count = 0 # 重置计数器
                                            continue
                                        (x_skill, y_skill), conf_skill = skillactivate_detector.find_icon(screenshot)
                                        if x_skill is not None:
                                            print("检测到协奏技能激活，执行点击")
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(1): return
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(1): return
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(2): return
                                            no_response_count = 0 # 重置计数器
                                            continue
                                        
                                        # === 动态等待逻辑 ===
                                        # 如果代码运行到这里，说明上述所有图标都没找到（界面卡住或加载中）
                                        no_response_count += 1
                                        if no_response_count >= 3:
                                            # 连续3次未检测到状态，判定为卡顿，主动休眠1秒防止ADB崩溃
                                            # 正常流畅时不会触发此逻辑，保证效率
                                            if not _sleep(1): return
                                        # ===================

                                else:#金钱不足，跳出购买循环
                                    break

                            print("优惠商品购买完成")
                            tapscreen_tool.tap_screen(68, 37)
                            if not _sleep(2): return
                        
                                
                        else:
                            print("未发现优惠商品")
                            tapscreen_tool.tap_screen(68, 37)
                            if not _sleep(2): return
                        

                        #点击强化
                        
                        #循环到金钱不够
                        
                        while True:
                            if stop_event and stop_event.is_set():
                                print("收到停止信号，退出爬塔")
                                return
                            tapscreen_tool.tap_screen(657, 393)
                            if not _sleep(2): return
                            screenshot = screenshot_tool.capture()
                            (x_reco, y_reco), conf_reco = recommend_detector.find_icon(screenshot)
                            if x_reco is not None:
                                print("检测到推荐卡牌页面，进行选择")
                                tapscreen_tool.tap_screen(x_reco, y_reco)  # 点击推荐卡
                                if not _sleep(2): return
                                tapscreen_tool.tap_screen(x_reco+129, y_reco+193)  # 确认选择
                                if not _sleep(3): return
                            else:
                                break

                    tapscreen_tool.tap_screen(x_quit, y_quit)  # 点击退出爬塔
                    if not _sleep(2): return
                    tapscreen_tool.tap_screen(778, 506)  # 确认退出
                    if not _sleep(2): return
                    tapscreen_tool.tap_screen(656, 672) 
                    if not _sleep(2): return
                    tapscreen_tool.tap_screen(656, 672) 
                    if not _sleep(2): return
                    screenshot = screenshot_tool.capture()
                    (x_save, y_save), conf_save = savepagecheak_detector.find_icon(screenshot)
                    while x_save is None:
                        tapscreen_tool.tap_screen(656, 672) 
                        if not _sleep(2): return
                        screenshot = screenshot_tool.capture()
                        (x_save, y_save), conf_save = savepagecheak_detector.find_icon(screenshot)
                    
                    (x_locked, y_locked), conf_locked = islocked_detector.find_icon(screenshot)
                    if x_locked is not None:
                        tapscreen_tool.tap_screen(x_locked, y_locked)
                        if not _sleep(2): return
                    
                    
                    tapscreen_tool.tap_screen(x_save, y_save)  # 删除记录
                    if not _sleep(2): return
                    tapscreen_tool.tap_screen(776, 534)  # 确认删除
                    if not _sleep(2): return
                    tapscreen_tool.tap_screen(776, 534)  
                    if not _sleep(2): return
                    tapscreen_tool.tap_screen(776, 534)  
                    if not _sleep(2): return
                    break # 退出塔后跳出循环，完成一次爬塔
                    
    
                (x_reco, y_reco), conf_reco = recommend_detector.find_icon(screenshot)
                if x_reco is not None:
                    print("检测到推荐卡牌页面，进行选择")
                    tapscreen_tool.tap_screen(x_reco, y_reco)  # 点击推荐卡
                    if not _sleep(2): return
                    tapscreen_tool.tap_screen(x_reco+129, y_reco+193)  # 确认选择
                    if not _sleep(3): return
                    continue    
                (x_music, y_music), conf_music = musicnoteget_detector.find_icon(screenshot)
                if x_music is not None:
                    print("检测到音符获取页面，执行点击")
                    tapscreen_tool.tap_screen(157, 341) 
                    if not _sleep(2): return
                    tapscreen_tool.tap_screen(157, 341) 
                    if not _sleep(3): return
                    
                    continue
                    
                (x_skill, y_skill), conf_skill = skillactivate_detector.find_icon(screenshot)
                if x_skill is not None:
                    print("检测到协奏技能激活，执行点击")
                    tapscreen_tool.tap_screen(157, 341) 
                    if not _sleep(1): return
                    tapscreen_tool.tap_screen(157, 341) 
                    if not _sleep(1): return
                    tapscreen_tool.tap_screen(157, 341) 
                    if not _sleep(2): return
                    continue
                
                (x_skipshop, y_skipshop), conf_skipshop = self.skipshopping_detector.find_icon(screenshot)
                if x_skipshop is not None:
                    if climb_type == 'standard':  #标准爬塔模式:购买，强化
                        print("检测到商店强化页面页面，执行购买音符以及升级")
                        tapscreen_tool.tap_screen(653, 286) #点击进入商店
                        if not _sleep(2): return

                        print("正在扫描优惠商品...")
                        screenshot = screenshot_tool.capture()
                        discount_points = self.find_multi_icons(screenshot, self.discount_detector)
                        
                        if discount_points:
                            print(f"发现 {len(discount_points)} 个优惠商品，开始购买")
                            for idx, (dx, dy) in enumerate(discount_points):
                                if stop_event and stop_event.is_set(): return
                                print(f"购买第 {idx + 1} 个优惠商品: ({dx}, {dy})")
                                tapscreen_tool.tap_screen(dx, dy) 
                                if not _sleep(2): return # 点击间隔
                                screenshot = screenshot_tool.capture()
                                (x_buy, y_buy), conf_buy = self.buy_detector.find_icon(screenshot)
                                if x_buy is not None:
                                    tapscreen_tool.tap_screen(x_buy, y_buy)  # 点击购买按钮
                                    if not _sleep(2): return
                                    
                                    # 引入计数器，实现动态等待
                                    no_response_count = 0
                                    
                                    while True:
                                        if stop_event and stop_event.is_set():
                                            print("收到停止信号，退出爬塔")
                                            return
                                        
                                        screenshot = screenshot_tool.capture()
                                        (x_buycheak, y_buycheak), conf_buycheak = buypagecheak_detector.find_icon(screenshot)
                                        if x_buycheak is not None:
                                            break

                                        (x_reco, y_reco), conf_reco = recommend_detector.find_icon(screenshot)
                                        if x_reco is not None:
                                            print("检测到推荐卡牌页面，进行选择")
                                            tapscreen_tool.tap_screen(x_reco, y_reco)  # 点击推荐卡
                                            if not _sleep(2): return
                                            tapscreen_tool.tap_screen(x_reco+129, y_reco+193)  # 确认选择
                                            if not _sleep(3): return
                                            no_response_count = 0 # 重置计数器
                                            continue    
                                        (x_music, y_music), conf_music = musicnoteget_detector.find_icon(screenshot)
                                        if x_music is not None:
                                            print("检测到音符获取页面，执行点击")
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(2): return
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(3): return
                                            no_response_count = 0 # 重置计数器
                                            continue
                                        (x_skill, y_skill), conf_skill = skillactivate_detector.find_icon(screenshot)
                                        if x_skill is not None:
                                            print("检测到协奏技能激活，执行点击")
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(1): return
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(1): return
                                            tapscreen_tool.tap_screen(157, 341) 
                                            if not _sleep(2): return
                                            no_response_count = 0 # 重置计数器
                                            continue
                                        
                                        # 防止网卡adb截图崩溃
                                        no_response_count += 1
                                        if no_response_count >= 2:
                                            # 连续2次未检测到状态，判定为卡顿
                                            
                                            if not _sleep(1): return
                                       
                                else:#金钱不足，跳出购买循环
                                    break

                            print("优惠商品购买完成")
                            tapscreen_tool.tap_screen(68, 37)
                            if not _sleep(2): return
                        
                                                
                        else:
                            print("未发现优惠商品")
                            tapscreen_tool.tap_screen(68, 37)
                            if not _sleep(2): return
                        

                        #点击强化
                        
                        #循环到金钱不够
                        
                        while True:
                            if stop_event and stop_event.is_set():
                                print("收到停止信号，退出爬塔")
                                return
                            tapscreen_tool.tap_screen(597, 392)
                            if not _sleep(2): return
                            screenshot = screenshot_tool.capture()
                            (x_reco, y_reco), conf_reco = recommend_detector.find_icon(screenshot)
                            if x_reco is not None:
                                print("检测到推荐卡牌页面，进行选择")
                                tapscreen_tool.tap_screen(x_reco, y_reco)  # 点击推荐卡
                                if not _sleep(2): return
                                tapscreen_tool.tap_screen(x_reco+129, y_reco+193)  # 确认选择
                                if not _sleep(3): return
                            else:
                                tapscreen_tool.tap_screen(x_skipshop, y_skipshop) 
                                if not _sleep(3): return
                                break
                        tapscreen_tool.tap_screen(x_skipshop, y_skipshop) 
                        if not _sleep(3): return 
                    elif climb_type == 'quick': #快速爬塔模式:跳过购买，直接继续爬塔
                        print("检测到商店强化页面，跳过购买直接继续爬塔")
                        tapscreen_tool.tap_screen(x_skipshop, y_skipshop) 
                        if not _sleep(3): return                
                    continue
                

                #以上页面均未检测到，说明进入对话

                tapscreen_tool.tap_screen(1060, 600) 
                if not _sleep(2): return
                screenshot = screenshot_tool.capture()
                (x_talk, y_talk), conf_talk = self.talk_detector.find_icon(screenshot)
                if x_talk is not None:
                    tapscreen_tool.tap_screen(x_talk, y_talk)
                    if not _sleep(3): return
                    continue


            

            if not _sleep(5): break 
            
            tapscreen_tool.tap_screen(66, 37)
            if not _sleep(2): return
            run_count += 1
            
        Back2maintitle()
        return












