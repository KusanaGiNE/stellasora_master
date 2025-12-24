import requests
import zipfile
import os
import sys
import shutil
import json
import time
import subprocess
from packaging import version

# === 配置 ===
SERVER_URL = "http://103.239.245.46:52176/version.json"
# 获取脚本所在目录的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_VERSION_FILE = os.path.join(BASE_DIR, "version.txt") # 本地版本文件

def get_local_version():
    if os.path.exists(CURRENT_VERSION_FILE):
        with open(CURRENT_VERSION_FILE, 'r') as f:
            return f.read().strip()
    return "1.0.0"

def update():
    print("正在检查更新...")
    try:
        # 1. 获取远程版本信息
        resp = requests.get(SERVER_URL, timeout=5)
        if resp.status_code != 200:
            print("无法连接到更新服务器")
            return
            
        remote_data = resp.json()
        remote_ver = remote_data['latest_version']
        local_ver = get_local_version()
        
        print(f"当前版本: {local_ver}, 最新版本: {remote_ver}")
        
        if version.parse(remote_ver) <= version.parse(local_ver):
            print("已经是最新版本。")
            time.sleep(2)
            return

        print(f"\n发现新版本！更新内容:\n{remote_data['changelog']}\n")
        
        # 2. 下载补丁
        print("正在下载更新包...")
        zip_resp = requests.get(remote_data['download_url'], stream=True)
        zip_path = os.path.join(BASE_DIR, "update_temp.zip")
        
        with open(zip_path, 'wb') as f:
            for chunk in zip_resp.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # 3. 解压覆盖
        print("正在安装更新...")
        # 备份旧文件 (可选)
        # shutil.copytree("core", "core_backup", dirs_exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(BASE_DIR) # 直接覆盖当前目录下的 core, webapp 等
            
        # 4. 更新本地版本号
        with open(CURRENT_VERSION_FILE, 'w') as f:
            f.write(remote_ver)
            
        # 5. 清理
        os.remove(zip_path)
        
        print("更新成功！正在启动主程序...")
        time.sleep(1)
        
        # 启动主程序
        exe_path = os.path.join(BASE_DIR, "StellasoraMaster.exe")
        if os.path.exists(exe_path):
            os.startfile(exe_path)
        else:
            print("未找到主程序，请手动启动。")
        
    except Exception as e:
        print(f"更新失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    # 确保不在 _internal 中运行，而是作为独立进程
    update()
