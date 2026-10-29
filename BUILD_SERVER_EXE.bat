@echo off
cd /d "%~dp0"
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --console --name CroakSquad_Server server.py
echo.
echo Check dist\CroakSquad_Server.exe
pause
