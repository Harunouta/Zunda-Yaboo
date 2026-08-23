# Third-party notices

This file tracks third-party software and data.  
Original Zunda-Yaboo code is under MIT (`../LICENSE`). Restricted data is not shipped.

## Runtime dependencies

| Name | Use | Redistribute in this repo? | Notes |
|------|-----|----------------------------|-------|
| PyYAML | YAML config | No need to vendor; pip install | MIT — https://github.com/yaml/pyyaml |
| Python stdlib | HTTP, JSON, etc. | N/A | PSF |

## Container base

| Name | Redistribute? | Notes |
|------|---------------|-------|
| `python:3.12-slim` (Docker Hub) | Image pulled by user | Follow Docker Hub / Debian terms; we ship Dockerfile only |

## Host tools (not bundled)

| Name | Redistribute? | Notes |
|------|---------------|-------|
| LM Studio | NO | Proprietary app on host |
| Cursor | NO | Dev environment |

## Optional local model weights (`D:\Zunda-AI` / `/models`)

| Example | Redistribute in git? | Notes |
|---------|----------------------|-------|
| GGUF / safetensors caches | **NO** | Too large; per-model license on Hugging Face / publisher |

## Character / persona data

| Name | Redistribute in git? | Source / terms |
|------|----------------------|----------------|
| ずんだもん／あんこもん persona files | **NO** (unpublished) | Local `data/restricted/` only. Do not publish. [ずん子ガイドライン](https://zunko.jp/guideline.html). Character IP is not MIT. |

Place obtained files only under `data/restricted/` (gitignored).

## Historical inspiration

Event names (天明・ペリー等) are historical facts. Prompt wording in `src/events.py` is original for this sim.  
Do not drop copyrighted primary-source corpora (e.g. full scanned books, paid economic DBs) into `data/redistributable/` without a clear license.
