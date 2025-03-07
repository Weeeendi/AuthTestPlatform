#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import re

# 确保当前目录在sys.path中
current_dir = os.path.abspath('.')
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from version_manager import get_version_string
except ImportError:
    print("错误：无法导入version_manager模块")
    sys.exit(1)

def build_app():
    """构建应用程序"""
    print("开始构建应用程序...")
    
    # 获取当前版本号
    version_str = get_version_string()
    print(f"正在构建版本：{version_str}")
    
    # 使用PyInstaller构建应用
    try:
        # 使用完整路径运行pyinstaller
        pyinstaller_cmd = ["pyinstaller", "main.spec"]
        print(f"执行命令: {' '.join(pyinstaller_cmd)}")
        subprocess.run(pyinstaller_cmd, check=True)
        print(f"构建成功！版本：{version_str}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"构建失败：{e}")
        return False
    except FileNotFoundError:
        print("错误：找不到pyinstaller命令。请确保已安装PyInstaller并且在PATH中。")
        return False

if __name__ == "__main__":
    build_app() 