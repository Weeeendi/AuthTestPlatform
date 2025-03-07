#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import re
import json

# 确保当前目录在sys.path中
current_dir = os.path.abspath('.')
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 直接从version.json读取版本号，不依赖DEFAULT_VERSION
VERSION_FILE = os.path.join(os.path.abspath('.'), 'version.json')

def get_version_from_json():
    """直接从version.json读取版本号"""
    try:
        if not os.path.exists(VERSION_FILE):
            print(f"版本文件不存在：{VERSION_FILE}，将使用默认版本")
            # 如果文件不存在，尝试从version_manager导入
            try:
                from version_manager import DEFAULT_VERSION
                return DEFAULT_VERSION.copy()
            except ImportError:
                # 如果导入失败，使用硬编码的默认版本
                return {'major': 25, 'minor': 1, 'patch': 0, 'build': 0}
        
        with open(VERSION_FILE, 'r') as f:
            content = f.read().strip()
            if not content:  # 文件为空
                print("版本文件为空，使用默认版本")
                # 如果文件为空，尝试从version_manager导入
                try:
                    from version_manager import DEFAULT_VERSION
                    return DEFAULT_VERSION.copy()
                except ImportError:
                    # 如果导入失败，使用硬编码的默认版本
                    return {'major': 25, 'minor': 1, 'patch': 0, 'build': 0}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"读取版本文件出错：{e}")
        # 如果读取失败，尝试从version_manager导入
        try:
            from version_manager import DEFAULT_VERSION
            return DEFAULT_VERSION.copy()
        except ImportError:
            # 如果导入失败，使用硬编码的默认版本
            return {'major': 25, 'minor': 1, 'patch': 0, 'build': 0}

def get_version_string_from_json():
    """获取版本号字符串，直接从version.json读取"""
    version = get_version_from_json()
    return f"V{version['major']}.{version['minor']}.{version['patch']}.{version['build']}"

def update_spec_file_without_increment(spec_file='main.spec'):
    """更新spec文件中的版本号，但不增加构建号"""
    import re
    
    spec_file = os.path.join(os.path.abspath('.'), spec_file)
    if not os.path.exists(spec_file):
        print(f"错误：找不到 {spec_file} 文件")
        return False
    
    try:
        # 获取当前版本号，直接从version.json读取
        version_str = get_version_string_from_json()
        
        # 读取spec文件内容
        with open(spec_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式替换版本号
        pattern = r"app_name = ['\"]VProductTest_V\d+\.\d+\.\d+\.\d+['\"]"
        replacement = f"app_name = 'VProductTest_{version_str}'"
        
        # 如果找不到app_name变量，尝试查找name参数
        if not re.search(pattern, content):
            pattern = r"name='VProductTest_V\d+\.\d+\.\d+\.\d+'"
            replacement = f"name='VProductTest_{version_str}'"
        
        new_content = re.sub(pattern, replacement, content)
        
        # 写回spec文件
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"已更新spec文件中的版本号为：{version_str}")
        return True
    except Exception as e:
        print(f"更新spec文件出错：{e}")
        return False

def build_app():
    """构建应用程序"""
    print("开始构建应用程序...")
    
    # 更新spec文件中的版本号，但不增加构建号
    if not update_spec_file_without_increment():
        print("更新版本号失败，构建终止")
        return False
    
    # 获取当前版本号，直接从version.json读取
    version_str = get_version_string_from_json()
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