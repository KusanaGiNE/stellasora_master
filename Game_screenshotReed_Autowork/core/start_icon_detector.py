# filepath: d:\Python-Autogamg\Game_screenshotReed_Autowork\core\start_icon_detector.py
import cv2
import os
import numpy as np

class IconDetector:
    def __init__(self, template_path=None):
        """
        初始化图标识别器
        
        参数:
            template_path: 模板图片路径
        """
        self.template = None
        if template_path:
            self.load_template(template_path)

    def load_template(self, template_path):
        """
        加载模板图片
        
        参数:
            template_path: 模板图片路径
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"模板图片不存在: {template_path}")
            
        # 使用 imdecode + fromfile 支持中文路径
        self.template = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if self.template is None:
            raise ValueError(f"无法加载模板图片: {template_path}")
        
        return self.template

    def find_icon(self, screenshot, threshold=0.8, show_result=False):
        """
        在截图中查找图标
        
        参数:
            screenshot: 要搜索的截图(OpenCV图像)
            threshold: 匹配阈值(0-1)
            show_result: 是否显示标记结果
            
        返回:
            (中心坐标x, 中心坐标y), 匹配度 或 (None, None), 0
        """
        if self.template is None:
            raise RuntimeError("未加载模板图片")
            
        # 模板匹配
        result = cv2.matchTemplate(screenshot, self.template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            h, w = self.template.shape[:2]
            top_left = max_loc
            center_x = top_left[0] + w // 2
            center_y = top_left[1] + h // 2
            
            if show_result:
                marked = screenshot.copy()
                cv2.rectangle(marked, top_left, (top_left[0]+w, top_left[1]+h), (0,255,0), 2)
                cv2.imshow('Detection Result', marked)
                cv2.waitKey(2000)  # 显示2秒
                cv2.destroyAllWindows()
                
            return (center_x, center_y), max_val
        else:
            return (None, None), max_val

# 提供默认实例方便快速使用
default_detector = IconDetector()