@echo off
echo Cleaning old build files...
rmdir /s /q dist
rmdir /s /q build
echo Starting rebuild...
pyinstaller main.spec --noconfirm
echo Build completed!
pause 