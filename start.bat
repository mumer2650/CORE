@echo off
echo Starting CORE Backend...
start cmd /k "cd backend && call .venv\Scripts\activate && uvicorn main:app --reload"

echo Starting CORE Frontend...
start cmd /k "cd frontend && npm run dev"

echo Both servers are starting up in new windows!
