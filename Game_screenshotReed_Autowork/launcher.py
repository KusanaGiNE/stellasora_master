import sys
import os
import traceback

# 获取当前 exe (或脚本) 所在的目录
base_path = os.path.dirname(os.path.abspath(sys.argv[0]))

# 将该目录加入 sys.path，以便能 import 旁边的 run_app.py
sys.path.insert(0, base_path)

# 切换工作目录到 base_path
os.chdir(base_path)

print(f"Launcher started in: {base_path}")

try:
    # 尝试导入外部的 run_app.py
    # 这要求 run_app.py 必须在 exe 同级目录下
    import run_app
    print("Loaded run_app successfully.")
    run_app.main()
except ImportError as e:
    print(f"Error: Could not import run_app.py. Make sure it exists in {base_path}")
    print(f"Details: {e}")
    # 如果是 GUI 运行，可能看不到 print，但在 cmd 运行能看到
    # 也可以考虑弹窗提示，但为了简单先这样
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"无法找到 run_app.py\n\n{e}", "启动错误", 0x10)
    except:
        pass
except Exception as e:
    print(f"Critical Error: {e}")
    traceback.print_exc()
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"发生严重错误:\n{e}", "运行错误", 0x10)
    except:
        pass
