@echo off
chcp 65001 > nul
echo 开始构建应用程序...

REM 检查Python是否安装
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误：找不到Python。请确保Python已安装并添加到PATH中。
    goto :end
)

REM 检查PyInstaller是否安装
python -c "import PyInstaller" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误：找不到PyInstaller。请使用命令安装：pip install pyinstaller
    goto :end
)

REM 只更新version.json文件中的版本号
echo 更新版本号...
python update_version.py --increment build
if %ERRORLEVEL% neq 0 (
    echo 更新版本号失败！请检查错误信息。
    goto :end
)

REM 运行构建脚本（不再增加构建号）
python build.py
if %ERRORLEVEL% neq 0 (
    echo 构建失败！请检查错误信息。
) else (
    echo 构建完成！
)

:end
pause 