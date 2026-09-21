# Start HTML viewer inside Zunda-Yaboo (bind 0.0.0.0:8765).
$ErrorActionPreference = "Stop"
$container = "Zunda-Yaboo"

$running = docker inspect -f "{{.State.Running}}" $container 2>$null
if ($running -ne "true") {
  Write-Error "Container $container is not running. Run Starter/up.ps1 first."
}

# Stop prior viewer on 8765 inside the container (best-effort).
docker exec $container python -c @"
import os, signal, pathlib
for p in pathlib.Path('/proc').glob('[0-9]*'):
  try:
    c = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
  except Exception:
    continue
  if 'web_viewer_server.py' in c:
    try:
      os.kill(int(p.name), signal.SIGTERM)
    except ProcessLookupError:
      pass
"@

Start-Sleep -Seconds 1
docker exec -d -w /workspace $container python scripts/web_viewer_server.py --bind 0.0.0.0 --port 8765
Start-Sleep -Seconds 2

try {
  $job = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/job" -TimeoutSec 5
  Write-Host "Viewer OK. /api/job running=$($job.running)"
  Write-Host "Open http://127.0.0.1:8765/ and http://127.0.0.1:8765/compare.html"
} catch {
  Write-Error "Viewer did not respond on http://127.0.0.1:8765/ — $($_.Exception.Message)"
}
