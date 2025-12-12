import cv2
import ddddocr
import numpy as np
import PIL.Image

# Monkey patch ANTIALIAS for Pillow 10.0.0+ compatibility
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

class OcrTool:
    """
    基于 ddddocr 的轻量级 OCR 工具类，用于识别游戏中的数字和短文本。
    """
    def __init__(self, beta=True):
        # beta=True 启用新版模型，识别效果通常更好
        # show_ad=False 关闭广告打印
        # 注意：某些版本的 ddddocr 可能不支持 beta 参数，如果报错请尝试移除 beta=beta
        try:
            self.ocr = ddddocr.DdddOcr(beta=beta, show_ad=False)
        except TypeError:
            try:
                self.ocr = ddddocr.DdddOcr(show_ad=False)
            except TypeError:
                self.ocr = ddddocr.DdddOcr()

    def recognize_number(self, image: np.ndarray, region: tuple[int, int, int, int] | None = None) -> int:
        """
        从图片或指定区域识别数字。
        
        Args:
            image: OpenCV 格式的图片 (numpy array)
            region: 可选的识别区域 (x, y, w, h)。如果不传则识别全图。
            
        Returns:
            int: 识别到的数字。如果未识别到数字则返回 0。
        """
        if region:
            x, y, w, h = region
            # 简单的边界检查
            h_img, w_img = image.shape[:2]
            x = max(0, min(x, w_img))
            y = max(0, min(y, h_img))
            w = max(0, min(w, w_img - x))
            h = max(0, min(h, h_img - y))
            
            if w <= 0 or h <= 0:
                return 0
                
            image = image[y:y+h, x:x+w]

        # ddddocr 需要 bytes 格式
        success, encoded_image = cv2.imencode('.png', image)
        if not success:
            return 0
        
        img_bytes = encoded_image.tobytes()
        
        # 执行识别
        res = self.ocr.classification(img_bytes)
        
        # 过滤非数字字符（防止识别出逗号、空格、小数点等干扰）
        digits = ''.join(filter(str.isdigit, res))
        
        return int(digits) if digits else 0

    def recognize_text(self, image: np.ndarray, region: tuple[int, int, int, int] | None = None) -> str:
        """
        从图片或指定区域识别文本（不限于数字）。
        """
        if region:
            x, y, w, h = region
            h_img, w_img = image.shape[:2]
            x = max(0, min(x, w_img))
            y = max(0, min(y, h_img))
            w = max(0, min(w, w_img - x))
            h = max(0, min(h, h_img - y))
            
            if w <= 0 or h <= 0:
                return ""
            image = image[y:y+h, x:x+w]

        success, encoded_image = cv2.imencode('.png', image)
        if not success:
            return ""
            
        img_bytes = encoded_image.tobytes()
        return self.ocr.classification(img_bytes)
