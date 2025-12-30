import sys
import os
import traceback


base_path = os.path.dirname(os.path.abspath(sys.argv[0]))


sys.path.insert(0, base_path)

# 切换工作目录到 base_path
os.chdir(base_path)

print(f"Launcher started in: {base_path}")

try:
  

    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        normalized = os.path.basename(first_arg).lower()
        if first_arg in ("--update", "update") or normalized == "update.py":
            import update
            update.update()
            raise SystemExit(0)

    import run_app
    print("Loaded run_app successfully.")
    run_app.main()
except ImportError as e:
    print(f"Error: Could not import run_app.py. Make sure it exists in {base_path}")
    print(f"Details: {e}")
 
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
