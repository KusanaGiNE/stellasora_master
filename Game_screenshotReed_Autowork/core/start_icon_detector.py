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

    def find_icon(self, screenshot, threshold=0.8, show_result=False, region=None, target_width=1280):
        """
        在截图中查找图标，支持区域搜索和分辨率适配
        
        参数:
            screenshot: 要搜索的截图(OpenCV图像)
            threshold: 匹配阈值(0-1)
            show_result: 是否显示标记结果
            region: (x, y, w, h) 指定搜索区域，相对于原始截图
            target_width: 模板对应的基准分辨率宽度，默认1280。如果截图宽度不同，会自动缩放截图进行匹配。
            
        返回:
            (中心坐标x, 中心坐标y), 匹配度 或 (None, None), 0
        """
        if self.template is None:
            raise RuntimeError("未加载模板图片")
            
        # 1. 分辨率适配
        h_img, w_img = screenshot.shape[:2]
        scale_ratio = 1.0
        
        # 如果截图宽度与基准宽度差异较大，则进行缩放
        if abs(w_img - target_width) > 10:
            scale_ratio = target_width / w_img
            new_h = int(h_img * scale_ratio)
            screenshot_resized = cv2.resize(screenshot, (target_width, new_h))
        else:
            screenshot_resized = screenshot

        # 2. 区域裁剪 (Region of Interest)
        # 注意：region 是基于原始截图的坐标，如果缩放了，region 也需要缩放
        if region:
            rx, ry, rw, rh = region
            # 缩放 region
            rx = int(rx * scale_ratio)
            ry = int(ry * scale_ratio)
            rw = int(rw * scale_ratio)
            rh = int(rh * scale_ratio)
            
            # 边界检查
            h_res, w_res = screenshot_resized.shape[:2]
            rx = max(0, min(rx, w_res))
            ry = max(0, min(ry, h_res))
            rw = max(0, min(rw, w_res - rx))
            rh = max(0, min(rh, h_res - ry))
            
            if rw <= 0 or rh <= 0:
                return (None, None), 0
                
            search_img = screenshot_resized[ry:ry+rh, rx:rx+rw]
            offset_x, offset_y = rx, ry
        else:
            search_img = screenshot_resized
            offset_x, offset_y = 0, 0

        # 3. 模板匹配
        # 检查 search_img 是否比 template 小
        th, tw = self.template.shape[:2]
        sh, sw = search_img.shape[:2]
        if sh < th or sw < tw:
            # 搜索区域比模板还小，无法匹配
            return (None, None), 0

        result = cv2.matchTemplate(search_img, self.template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            top_left = max_loc
            # 计算在 search_img 中的中心点
            center_x_in_search = top_left[0] + tw // 2
            center_y_in_search = top_left[1] + th // 2
            
            # 4. 坐标还原
            # 先还原到 screenshot_resized 的坐标
            center_x_resized = center_x_in_search + offset_x
            center_y_resized = center_y_in_search + offset_y
            
            # 再还原到原始 screenshot 的坐标
            final_x = int(center_x_resized / scale_ratio)
            final_y = int(center_y_resized / scale_ratio)
            
            if show_result:
                # 注意：show_result 这里只在缩放后的图上画框，简单示意
                marked = search_img.copy()
                cv2.rectangle(marked, top_left, (top_left[0]+tw, top_left[1]+th), (0,255,0), 2)
                cv2.imshow('Detection Result', marked)
                cv2.waitKey(2000)
                cv2.destroyAllWindows()
                
            return (final_x, final_y), max_val
        else:
            return (None, None), max_val

# 提供默认实例方便快速使用
default_detector = IconDetector()