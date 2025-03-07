import os
from PyInstaller.utils.hooks import collect_data_files
# 导入版本管理模块
import sys
# 使用绝对路径而不是相对路径
current_dir = os.path.abspath('.')
sys.path.append(current_dir)
try:
    from version_manager import get_version_string
    # 获取当前版本号
    version_str = get_version_string()
    app_name = f'VProductTest_{version_str}'
except ImportError:
    # 如果导入失败，使用默认版本号
    app_name = 'VProductTest_V25.1.0.1'

a = Analysis(
    ['main_page.py'],
    pathex=['D:/workspace/python/Fluent/PyQt-Fluent-Widgets'],
    binaries=[],
    datas=[('resources/*.*', 'resources'),
            ('resources/ui/*.*','resources/images'),
            ('resources/config/*.*','resources/config'),
            ('resources/user/*.*','resources/user'),
            ('changeLogs.txt','.')
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
