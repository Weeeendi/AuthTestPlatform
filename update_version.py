#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
版本号更新脚本
用于确保所有地方的版本号一致
"""

import os
import sys
import json
import re

# 确保当前目录在sys.path中
current_dir = os.path.abspath('.')
if current_dir not in sys.path:
    sys.path.append(current_dir)

from version_manager import get_version, save_version, get_version_string

def update_version(major=None, minor=None, patch=None, build=None):
    """更新版本号"""
    version = get_version()
    
    # 更新版本号
    if major is not None:
        version['major'] = major
    if minor is not None:
        version['minor'] = minor
    if patch is not None:
        version['patch'] = patch
    if build is not None:
        version['build'] = build
    
    # 保存版本号
    save_version(version)
    
    # 获取版本号字符串
    version_str = get_version_string()
    print(f"版本号已更新为：{version_str}")
    
    return version_str

def update_all_files():
    """更新所有文件中的版本号"""
    version_str = get_version_string()
    
    # 更新main.spec文件
    update_spec_file('main.spec', version_str)
    
    # 更新main_page.py文件
    update_py_file('main_page.py', version_str)
    
    # 更新version_manager.py文件
    update_version_manager_file('version_manager.py', version_str)
    
    # 更新view/settingConf_interface.py文件
    update_py_file('view/settingConf_interface.py', version_str)
    
    print(f"所有文件中的版本号已更新为：{version_str}")

def update_spec_file(spec_file, version_str):
    """更新spec文件中的版本号"""
    spec_file = os.path.join(os.path.abspath('.'), spec_file)
    if not os.path.exists(spec_file):
        print(f"错误：找不到 {spec_file} 文件")
        return False
    
    try:
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
        
        print(f"已更新 {spec_file} 中的版本号为：{version_str}")
        return True
    except Exception as e:
        print(f"更新 {spec_file} 出错：{e}")
        return False

def update_py_file(py_file, version_str):
    """更新Python文件中的版本号"""
    py_file = os.path.join(os.path.abspath('.'), py_file)
    if not os.path.exists(py_file):
        print(f"错误：找不到 {py_file} 文件")
        return False
    
    try:
        # 读取Python文件内容
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式替换版本号
        pattern = r"APP_VERSION = \"V\d+\.\d+\.\d+\.\d+\""
        replacement = f'APP_VERSION = "{version_str}"'
        
        # 如果找不到APP_VERSION变量，尝试查找默认版本号
        if not re.search(pattern, content):
            pattern = r'APP_VERSION = "V\d+\.\d+\.\d+\.\d+"  # 默认版本号'
            replacement = f'APP_VERSION = "{version_str}"  # 默认版本号'
        
        new_content = re.sub(pattern, replacement, content)
        
        # 写回Python文件
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"已更新 {py_file} 中的版本号为：{version_str}")
        return True
    except Exception as e:
        print(f"更新 {py_file} 出错：{e}")
        return False

def update_version_manager_file(py_file, version_str):
    """更新version_manager.py文件中的默认版本号"""
    py_file = os.path.join(os.path.abspath('.'), py_file)
    if not os.path.exists(py_file):
        print(f"错误：找不到 {py_file} 文件")
        return False
    
    try:
        # 获取版本号
        version = get_version()
        
        # 读取Python文件内容
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式替换版本号
        pattern = r"version = \{'major': \d+, 'minor': \d+, 'patch': \d+, 'build': \d+\}"
        replacement = f"version = {{'major': {version['major']}, 'minor': {version['minor']}, 'patch': {version['patch']}, 'build': {version['build']}}}"
        
        new_content = re.sub(pattern, replacement, content)
        
        # 写回Python文件
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"已更新 {py_file} 中的默认版本号为：{version_str}")
        return True
    except Exception as e:
        print(f"更新 {py_file} 出错：{e}")
        return False

def update_only_version_json(increment_type=None):
    """只更新version.json文件，不修改代码中的默认版本号"""
    version = get_version()
    
    # 根据increment_type增加相应部分的版本号
    if increment_type:
        if increment_type == 'major':
            version['major'] += 1
            version['minor'] = 0
            version['patch'] = 0
            version['build'] = 0
        elif increment_type == 'minor':
            version['minor'] += 1
            version['patch'] = 0
            version['build'] = 0
        elif increment_type == 'patch':
            version['patch'] += 1
            version['build'] = 0
        elif increment_type == 'build':
            version['build'] += 1
    
    # 保存版本号
    save_version(version)
    
    # 获取版本号字符串
    version_str = get_version_string()
    print(f"版本号已更新为：{version_str}")
    
    # 只更新spec文件中的版本号，不修改代码中的默认版本号
    update_spec_file_without_changing_code('main.spec')
    
    return version_str

def update_spec_file_without_changing_code(spec_file='main.spec'):
    """更新spec文件中的版本号，但不修改代码中的默认版本号"""
    spec_file = os.path.join(os.path.abspath('.'), spec_file)
    if not os.path.exists(spec_file):
        print(f"错误：找不到 {spec_file} 文件")
        return False
    
    try:
        # 获取当前版本号（不增加构建号）
        version_str = get_version_string()
        
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

if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    
    parser = argparse.ArgumentParser(description='更新版本号')
    parser.add_argument('--major', type=int, help='主版本号')
    parser.add_argument('--minor', type=int, help='次版本号')
    parser.add_argument('--patch', type=int, help='补丁号')
    parser.add_argument('--build', type=int, help='构建号')
    parser.add_argument('--increment', choices=['major', 'minor', 'patch', 'build'], help='增加指定部分的版本号')
    
    args = parser.parse_args()
    
    # 如果指定了increment参数，则增加相应部分的版本号
    if args.increment:
        update_only_version_json(args.increment)
    elif any([args.major, args.minor, args.patch, args.build]):
        # 更新版本号
        version = get_version()
        if args.major is not None:
            version['major'] = args.major
        if args.minor is not None:
            version['minor'] = args.minor
        if args.patch is not None:
            version['patch'] = args.patch
        if args.build is not None:
            version['build'] = args.build
        
        save_version(version)
        version_str = get_version_string()
        print(f"版本号已更新为：{version_str}")
        
        # 只更新spec文件中的版本号，不修改代码中的默认版本号
        update_spec_file_without_changing_code('main.spec')
    else:
        # 如果没有指定任何参数，则只打印当前版本号
        print(f"当前版本号：{get_version_string()}") 