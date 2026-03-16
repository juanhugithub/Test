@echo off
setlocal
cd /d %~dp0
python folder_tree_workbench.py gui
if errorlevel 1 (
  echo.
  echo 如果没有启动成功，请确认这台电脑已安装 Python 3，并且已加入 PATH。
  pause
)
endlocal
