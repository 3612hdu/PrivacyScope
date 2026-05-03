"""
PrivacyScope — Windows 隐私仪表盘
扫描和修复 Windows 隐私设置。
"""
import tkinter as tk
import sys
import os
import ctypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import PrivacyScopeGUI


def request_admin():
    """请求管理员权限"""
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return False
    except Exception:
        return False


def main():
    root = tk.Tk()
    app = PrivacyScopeGUI(root)

    try:
        root.iconbitmap("privacyscope.ico")
    except Exception:
        pass

    root.mainloop()


if __name__ == "__main__":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("提示: 以普通权限运行，扫描仍可用，但修复功能需要管理员权限。")
        print("右键 → 以管理员身份运行 即可解锁修复功能。\n")
    main()
