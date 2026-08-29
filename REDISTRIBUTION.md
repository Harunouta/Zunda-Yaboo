# Redistribution map (GitHub publication prep)

This repo is prepared for a public GitHub release.  
**Do not commit restricted assets.** See [CONTRIBUTING.md](CONTRIBUTING.md) for what belongs in git.

## Quick legend

| Mark | Meaning |
|------|---------|
| OK | Safe to put on a public GitHub repo (as of project policy) |
| NO | Must stay local / private; obtain yourself; do not push |
| LINK | Reference by URL/docs only; do not vendor the full dataset |

---

## OK — publish with the repo

| Path | Notes |
|------|-------|
| `src/**` | Original simulation engine (MIT) |
| `scripts/**` (except local smoke secrets) | Tooling |
| `config/default.yaml` | Defaults (no secrets) |
| `Dockerfile`, `docker-compose.yml`, `entrypoint.sh` | Container recipe |
| `requirements.txt` | Declares PyYAML only |
| `README.md`, `MODELS.md`, `LICENSE`, this file | Docs (not local handoff files) |
| `licenses/**` | Attribution |
| `data/events/**` | User-editable history tables (OK to publish; keep sparse) |
| `data/redistributable/**` | Synthetic / original sample data only. Includes speechless `compare_packs/*.zip` and **duel** `duel_packs/*.zip` (opinion+agri, no mascot) |
| `web/viewer/compare_duel.html` (+ js/css) | Public duel overlap viewer (MIT) |
| `.gitignore` | Keeps NO paths out of git |

Historical event *IDs and short Japanese prompt strings* in `src/events.py` and  
synthetic anchors in `src/historical_track.py` are original abstractions for the sim  
(not copyrighted primary-source dumps).

---

## NO — do not publish / do not commit

| Path / item | Why |
|-------------|-----|
| `data/restricted/**` (except README) | Character bibles / third-party persona corpora |
| `/models/**` (host cache of GGUF etc.) | Local LLM/SLM weights |
| `logs/**` | Run outputs (large; may contain model text) |
| `checkpoints/**` | Resume state |
| `.env`, API keys, LM Studio tokens | Secrets |
| Full copies of HF datasets | License / size / terms |
| User-provided Excel workbooks used as import input | Local-only; pass `--xlsx` or set `ZUNDA_EVENTS_XLSX` |
| `HANDOFF.md`, `.cursor/**`, `COMPLETION_PLAN.md`, `OVERNIGHT_*.md`, `docs/CUI_AND_VIZ.md`, `DATA_INGEST_PLAN.md` | Local handoff / overnight notes (gitignored) |

### Character / IP (especially careful)

| Asset | Status | Action for GitHub |
|-------|--------|-------------------|
| ずんだもん persona bible | **NO** (unpublished) | Keep under `data/restricted/` if you have a local copy. Do not publish or link a public dump. [ずん子ガイドライン](https://zunko.jp/guideline.html). |
| あんこもん persona bible | **NO** (unpublished) | Same. Do not publish a public `simple-ankomon` (or similar) dump. |
| Official SSS / 東北ずん子 project materials | NO by default | Follow official guidelines; do not redistribute assets from the org. |

The simulation **runs without** restricted bibles (fallback short system prompts in `src/mascot.py`).  
For authentic speech, place files locally per `data/restricted/README.md`.

---

## LINK — cite, don’t vendor

| Dependency | License (check upstream) | How we use it |
|------------|--------------------------|---------------|
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | Optional config |
| Python 3.12 / Docker Hub `python:3.12-slim` | PSF / Docker Hub terms | Runtime image |
| LM Studio (host app) | Proprietary host tool | HTTP client only; not bundled |
| Models in LM Studio (Qwen, Gemma, …) | Per-model cards | Not bundled; user downloads |
| ずんだもん／あんこもん bible | Unpublished / local only | Optional files under `data/restricted/`; never vendor or publish |

Always re-check upstream LICENSE before a public release.

---

## Suggested public tree

```
zunda-yaboo/
  LICENSE                 # MIT — code only
  REDISTRIBUTION.md       # this file
  licenses/THIRD_PARTY.md
  data/
    redistributable/      # OK
    restricted/           # NO content in git (README only)
  src/ …                  # OK
```

## Pre-publish checklist

1. `git status` shows no `data/restricted/*` bibles, no `logs/`, no model files  
2. README links character guidelines instead of embedding full corpora  
3. Confirm PyYAML / base image licenses unchanged  
5. `python scripts/check_redistribution.py` passes  
6. Maintainer sets GitHub visibility to public when ready, then pushes
