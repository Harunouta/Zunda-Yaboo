#!/usr/bin/env bash
# Health checks for Starter stack (gateway, viewer, dry-run).
set -euo pipefail
CONTAINER="${ZUNDA_CONTAINER:-Zunda-Yaboo}"
FAILED=0

ok() { echo "[OK] $*"; }
bad() { echo "[FAIL] $*"; FAILED=$((FAILED + 1)); }

echo "=== Starter verify ==="

if [[ "$(docker inspect -f '{{.State.Running}}' zunda-llm-gw 2>/dev/null || true)" == "true" ]]; then
  ok "zunda-llm-gw running"
else
  bad "zunda-llm-gw not running"
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)" == "true" ]]; then
  ok "Zunda-Yaboo running"
  ZY_UP=1
else
  bad "Zunda-Yaboo not running"
  ZY_UP=0
fi

if curl -fsS "http://127.0.0.1:4000/health" >/dev/null 2>&1; then
  ok "gateway :4000/health"
else
  bad "gateway :4000/health"
fi

for path in "/" "/compare.html"; do
  if curl -fsSI "http://127.0.0.1:8765${path}" >/dev/null 2>&1; then
    ok "viewer http://127.0.0.1:8765${path}"
  else
    bad "viewer http://127.0.0.1:8765${path}"
  fi
done

if [[ "$ZY_UP" == "1" ]]; then
  if docker exec -w /workspace -e PYTHONPATH=/workspace "$CONTAINER" \
    python -m src.main --no-llm --standard zunda --start 1853-01 --end 1853-03 --run-name starter_verify_dry; then
    ok "dry-run 1853-01..03"
  else
    bad "dry-run failed"
  fi
else
  bad "skip dry-run (container down)"
fi

if [[ "$FAILED" -gt 0 ]]; then
  echo "=== FAILED ($FAILED) — see Starter/VERIFY.md ==="
  exit 1
fi
echo "=== ALL OK ==="
exit 0
