#!/bin/sh
set -e
cd /workspace
exec python -m src.main "$@"
