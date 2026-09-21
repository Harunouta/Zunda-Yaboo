#!/usr/bin/env bash
# Start HTML viewer inside Zunda-Yaboo (bind 0.0.0.0:8765).
set -euo pipefail
CONTAINER="${ZUNDA_CONTAINER:-Zunda-Yaboo}"

if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)" != "true" ]]; then
  echo "Container $CONTAINER is not running. Run ./Starter/up.sh first." >&2
  exit 1
fi

docker exec "$CONTAINER" python - <<'PY'
import os, signal, pathlib
for p in pathlib.Path("/proc").glob("[0-9]*"):
  try:
    c = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode()
  except Exception:
    continue
  if "web_viewer_server.py" in c:
    try:
      os.kill(int(p.name), signal.SIGTERM)
    except ProcessLookupError:
      pass
PY

sleep 1
docker exec -d -w /workspace "$CONTAINER" python scripts/web_viewer_server.py --bind 0.0.0.0 --port 8765
sleep 2

if command -v curl >/dev/null 2>&1; then
  curl -fsS "http://127.0.0.1:8765/api/job" >/dev/null
  echo "Viewer OK."
else
  echo "Viewer started (install curl to probe /api/job)."
fi
echo "Open http://127.0.0.1:8765/ and http://127.0.0.1:8765/compare.html"
