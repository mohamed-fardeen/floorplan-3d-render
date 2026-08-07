@echo off
echo Starting Backend...
start "Backend" cmd /k "cd /d %~dp0floorplan-3d-backend && call .venv\Scripts\activate && python api.py"

echo Starting Frontend...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Both services have been started in separate terminals.
