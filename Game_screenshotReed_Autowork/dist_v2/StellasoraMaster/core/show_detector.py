import cv2
import numpy as np
import os
from pathlib import Path

class Showdetector:
    def __init__(self, output_dir="test"):
        self.output_dir = output_dir
        # 自动创建输出目录
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def show_image_with_rectangle(self, image, top_left, bottom_right, window_name='Result', save_image=True):
        marked_image = image.copy()
        cv2.rectangle(marked_image, top_left, bottom_right, (0, 255, 0), 2)
        cv2.imshow(window_name, marked_image)
        cv2.waitKey(1000)
        cv2.destroyAllWindows()
        if save_image:
            self.save_marked_image(marked_image)

    def save_marked_image(self, image, filename_prefix="marked"):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.png"
        save_path = Path(self.output_dir) / filename
        
        success = cv2.imwrite(str(save_path), image)
        if success:
            print(f"已保存标记图像到: {save_path}")
        else:
            print(f"无法保存图像到: {save_path}")

default_display = Showdetector()