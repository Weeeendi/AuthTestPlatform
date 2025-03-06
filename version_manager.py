#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import re

# 使用绝对路径
VERSION_FILE = os.path.join(os.path.abspath('.'), 'version.json')

def get_version():
    """读取当前版本号"""
    if not os.path.exists(VERSION_FILE):
        # 如果版本文件不存在，创建默认版本
        version = {'major': 24, 'minor': 1, 'patch': 0, 'build': 20}
        save_version(version)
        return version
    
    try:
        with open(VERSION_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"读取版本文件出错：{e}")
        # 返回默认版本
        version = {'major': 24, 'minor': 1, 'patch': 0, 'build': 20}
        save_version(version)
        return version

def save_version(version):
    """保存版本号到文件"""
    try:
        with open(VERSION_FILE, 'w') as f:
            json.dump(version, f, indent=4)
        return True
    except Exception as e:
        print(f"保存版本文件出错：{e}")
        return False

def increment_build():
    """增加构建号"""
    version = get_version()
    version['build'] += 1
    save_version(version)
    return version

def increment_patch():
    """增加补丁号"""
    version = get_version()
    version['patch'] += 1
    version['build'] = 0  # 重置构建号
    save_version(version)
    return version

def increment_minor():
    """增加次版本号"""
    version = get_version()
    version['minor'] += 1
    version['patch'] = 0  # 重置补丁号
    version['build'] = 0  # 重置构建号
    save_version(version)
    return version

def increment_major():
    """增加主版本号"""
    version = get_version()
    version['major'] += 1
    version['minor'] = 0  # 重置次版本号
    version['patch'] = 0  # 重置补丁号
    version['build'] = 0  # 重置构建号
    save_version(version)
    return version

def get_version_string():
    """获取版本号字符串，格式为 'V{major}.{minor}.{patch}.{build}'"""
    version = get_version()
    return f"V{version['major']}.{version['minor']}.{version['patch']}.{version['build']}"

def update_spec_file(spec_file='main.spec'):
    """更新spec文件中的版本号"""
    spec_file = os.path.join(os.path.abspath('.'), spec_file)
    if not os.path.exists(spec_file):
        print(f"错误：找不到 {spec_file} 文件")
        return False
    
    try:
        # 增加构建号
        version = increment_build()
        version_str = f"V{version['major']}.{version['minor']}.{version['patch']}.{version['build']}"
        
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
        
        print(f"已更新版本号为：{version_str}")
        return True
    except Exception as e:
        print(f"更新spec文件出错：{e}")
        return False

if __name__ == "__main__":
    # 当脚本直接运行时，更新spec文件中的版本号
    update_spec_file() 