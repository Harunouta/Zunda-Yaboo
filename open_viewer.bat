@echo off
setlocal
cd /d "%~dp0"
echo Docker: Zunda-Yaboo serves 0.0.0.0:8765
echo Windows: http://127.0.0.1:8765/  (published as 127.0.0.1:8765)
docker start Zunda-Yaboo >nul 2>&1
docker exec -d -e PYTHONPATH=/workspace -w /workspace Zunda-Yaboo python scripts/web_viewer_server.py --bind 0.0.0.0 --port 8765
timeout /t 1 /nobreak >nul
start "" "http://127.0.0.1:8765/"
echo Opened the Windows browser. The server stays in Docker.
endlocal
