#!/usr/bin/env bash
# Bring up zunda-llm-gw (+ Zunda-Yaboo only if it is not already running).
# Never stops an existing Zunda-Yaboo workspace container.
set -euo pipefail
STARTER_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$STARTER_DIR/.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="$STARTER_DIR/docker-compose.yml"
ENV_FILE="$STARTER_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$STARTER_DIR/.env.example" "$ENV_FILE"
  echo "Created Starter/.env from .env.example"
fi

COMPOSE=(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE")

if [[ "$(docker inspect -f '{{.State.Running}}' Zunda-Yaboo 2>/dev/null || true)" == "true" ]]; then
  echo "Zunda-Yaboo already running — leaving it alone; refreshing gateway only."
  docker rm -f zunda-llm-gw 2>/dev/null || true
  "${COMPOSE[@]}" up --build -d llm-gateway
else
  echo "Starting llm-gateway + Zunda-Yaboo (fresh)."
  "${COMPOSE[@]}" up --build -d
fi

echo ""
echo "Up. Next:"
echo "  ./Starter/start-viewer.sh"
echo "  ./Starter/verify.sh"
echo "  http://127.0.0.1:8765/  and  http://127.0.0.1:8765/compare.html"
