import os
import json
from PyInstaller.utils.hooks import collect_data_files

# 直接从resources/version/version.json读取版本号（与运行时保持一致）
VERSION_FILE = os.path.join(os.path.abspath('.'), 'resources', 'version', 'version.json')

try:
    if not os.path.exists(VERSION_FILE):
        print(f"版本文件不存在：{VERSION_FILE}，将使用默认版本")
        # 如果文件不存在，尝试从version_manager导入
        import sys
        current_dir = os.path.abspath('.')
        sys.path.append(current_dir)
        from version_manager import DEFAULT_VERSION_STRING
        app_name = f'VProductTestPro_{DEFAULT_VERSION_STRING}'
    else:
        with open(VERSION_FILE, 'r') as f:
            content = f.read().strip()
            if not content:  # 文件为空
                print("版本文件为空，使用默认版本")
                # 如果文件为空，尝试从version_manager导入
                import sys
                current_dir = os.path.abspath('.')
                sys.path.append(current_dir)
                from version_manager import DEFAULT_VERSION_STRING
                app_name = f'VProductTestPro_{DEFAULT_VERSION_STRING}'
            else:
                version = json.loads(content)
                version_str = f"V{version['major']}.{version['minor']}.{version['patch']}.{version['build']}"
                app_name = f'VProductTestPro_{version_str}'
except (json.JSONDecodeError, FileNotFoundError) as e:
    # 如果读取失败，尝试从version_manager导入
    try:
        # 使用绝对路径而不是相对路径
        import sys
        current_dir = os.path.abspath('.')
        sys.path.append(current_dir)
        from version_manager import DEFAULT_VERSION_STRING
        app_name = f'VProductTestPro_{DEFAULT_VERSION_STRING}'
    except ImportError:
        # 如果导入失败，使用硬编码的默认版本号
        app_name = 'VProductTestPro_V25.1.0.9'

a = Analysis(
    ['main_page.py'],
    pathex=['D:/workspace/python/Fluent/PyQt-Fluent-Widgets'],
    binaries=[],
    datas=[('resources/*.*', 'resources'),
            ('resources/ui/*.*','resources/images'),
            ('resources/config/*.*','resources/config'),
            ('resources/user/*.*','resources/user'),
            ('changeLogs.txt','.'),
            ('resources/version/version.json','resources/version')
            ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# 假设你想将整个resources目录及其下的所有子目录和文件原封不动地拷贝到exe的同一目录下
datas = collect_data_files('.',subdir='resources')

a.datas.extend(datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources\\logo.png'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)
