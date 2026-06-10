#!/bin/zsh
cd /Users/xxm/Documents/AI/ZY-demo/ai-medical-consultant/backend
./.venv312/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
