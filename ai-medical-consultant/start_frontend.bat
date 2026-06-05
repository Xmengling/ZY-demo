@echo off
chcp 65001 >nul
cd /d %~dp0frontend
if not exist node_modules (
  echo [AI 智能问诊系统] 首次运行，安装前端依赖 ...
  call npm install
)
echo [AI 智能问诊系统] 启动前端 (Vite) ...
call npm run dev
pause
