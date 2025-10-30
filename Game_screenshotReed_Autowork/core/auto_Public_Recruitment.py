import subprocess
import cv2
import numpy as np
import os
import time
from pathlib import Path
#import easyocr


from core import MumuScreenshot, IconDetector, Tapscreen, Showdetector
#reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)

class Autorecruitment:
    #自动公招
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
        

        # 在首页找到“公开招募”按钮并点击
        template1 = os.path.join(os.path.dirname(__file__), "../templates/PublicRecruitment/gongkaizhaomu.png")
        template1_1 = os.path.join(os.path.dirname(__file__), "../templates/PublicRecruitment/back1.png")
        detector1 = IconDetector(template1)
        detector1_1 = IconDetector(template1_1)

        screenshot1 = screenshot_tool.capture()
        (x1, y1), conf1 = detector1.find_icon(screenshot1)
        if x1 is not None:
            tapscreen_tool.tap_screen(x1, y1)
        else:
            
            print("未找到“公开招募”按钮")
            print("尝试返回主菜单")
            '''
            screenshot1_1 = screenshot_tool.capture()
            (x1_1, y1_1), conf1_1 = detector1_1.find_icon(screenshot1_1)
            if x1_1 is None:
                print("未找到返回按钮，无法返回主菜单，请手动操作")
            else:
                while x1_1 is not None:
                    tapscreen_tool.tap_screen(x1_1, y1_1)
                    screenshot1_1 = screenshot_tool.capture()
                    (x1_1, y1_1), conf1_1 = detector1_1.find_icon(screenshot1_1)
            '''
            max_retries = 5
            while x1 is None and max_retries > 0: 
                tapscreen_tool.tap_screen(80, 38) # 点击左上角返回按钮
                screenshot1 = screenshot_tool.capture()
                (x1, y1), conf1 = detector1.find_icon(screenshot1)
                max_retries -= 1
                
                
            tapscreen_tool.tap_screen(x1, y1) 

            
        
        # 选择招募tag
        screenshot = screenshot_tool.capture() 

        # 2. 初始化所有检测器
        template_paths = [
            os.path.join(os.path.dirname(__file__), "../templates/PublicRecruitment/kaishizhaomu1.png"),
            os.path.join(os.path.dirname(__file__), "../templates/PublicRecruitment/kaishizhaomu2.png"),
            os.path.join(os.path.dirname(__file__), "../templates/PublicRecruitment/kaishizhaomu3.png"),
            os.path.join(os.path.dirname(__file__), "../templates/PublicRecruitment/kaishizhaomu4.png"),
        ]

        detectors = [IconDetector(template) for template in template_paths]

        # 3. 检测所有模板并存储结果
        
        Tap_results = []
        results = []
        for detector in detectors:
            (x, y), conf = detector.find_icon(screenshot)
            Tap_results.append((x, y))
            if x is not None and y is not None:
                h, w = detector.template.shape[:2]
                top_left = (x - w // 2, y - h // 2)
                bottom_right = (x + w // 2, y + h // 2)
                results.append((top_left, bottom_right))

        print("检测到的坐标:", Tap_results)

        # 4. 在同一个截图上绘制所有矩形
        output_img = screenshot.copy()  # 避免修改原图
        colors = [
            (0, 255, 0),  # 绿色
            (0, 0, 255),  # 红色
            (255, 0, 0),  # 蓝色
            (255, 255, 0),  # 黄色
        ]

        for idx, (top_left, bottom_right) in enumerate(results):
            cv2.rectangle(output_img, top_left, bottom_right, colors[idx], 2)  # 绘制矩形
            cv2.putText(output_img, f"Match {idx+1}", (top_left[0], top_left[1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[idx], 1)  # 添加标签
 
          # 5. 显示或保存结果
        cv2.imshow("Multiple Matches", output_img)
        cv2.waitKey(0)  # 按任意键关闭窗口
        cv2.destroyAllWindows()

        # 6. 点击所有检测到的坐标
        print("开始招募")
        
        for (x, y) in Tap_results:
            if x is not None:
                tapscreen_tool.tap_screen(x, y)
                time.sleep(1)  # 等待1秒，确保点击生效
                '''
                 screenshot3_1 = screenshot_tool.capture()
                roi = screenshot3_1[353:353, 883:483]  # 截取屏幕中间部分
                results = reader.readtext(roi)
                for (bbox, text, prob) in results:
                    print(f"ROI文本: {text}, 置信度: {prob:.2f}")
                '''
               
                
                tapscreen_tool.tap_screen(976, 582)
                time.sleep(1)




                
      

default_PublicRecruitment = Autorecruitment()


