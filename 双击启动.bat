@echo off
chcp 65001 > nul
echo ==========================================
echo       正在启动 Trae 助手...
echo ==========================================

echo [1/3] 检查运行环境...
pip install -r requirements.txt > nul 2>&1
if %errorlevel% neq 0 (
    echo 依赖安装失败，请检查网络或 Python 环境。
    pause
    exit /b
)

echo [2/3] 启动后台服务...
echo 程序将在后台运行，请查看任务栏右下角托盘图标。
echo (如果没有看到图标，请点击任务栏的 "^" 箭头)

REM 使用 pythonw 启动，无黑框后台运行
start "" pythonw launcher.py

echo [3/3] 启动完成！
echo.
echo 本窗口将在 3 秒后自动关闭...
timeout /t 3 > nul
exit
