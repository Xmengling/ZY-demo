@echo off
chcp 65001 >nul
cd /d %~dp0backend
echo [AI 智能问诊系统] 启动后端 (FastAPI) ...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
