@echo off
chcp 65001 >nul
title A股智能分析助手

echo ========================================
echo    A股智能分析助手 - 启动中...
echo ========================================
echo.

REM 启动Flask后端
start "AStock-Server" /MIN python app.py

REM 等待服务器启动
echo [1/2] 正在启动后端服务...
timeout /t 6 /nobreak >nul

REM 启动serveo隧道
echo [2/2] 正在创建公网隧道...
echo.
echo ========================================
echo    公网地址（分享给任何人）：
echo.

ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R 80:localhost:5099 serveo.net

echo.
echo 隧道已断开，按任意键重新连接...
pause >nul
