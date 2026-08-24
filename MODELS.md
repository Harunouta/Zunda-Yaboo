# Local SLM / model cache

役割分担の図: [`docs/MODEL_WIRING.md`](docs/MODEL_WIRING.md)。

Host path: set `ZUNDA_AI_HOST` or `ZUNDA_AI_DIR` (container mount is `/models`). Do not hard-code a drive letter.  
Container mount: `/models` (`ZUNDA_AI_DIR`)

**Do not commit weights to GitHub.** See [REDISTRIBUTION.md](REDISTRIBUTION.md).

Place GGUF or LM Studio model folders here when you need extra small models
that should not crash the PC. The simulation primarily uses LM Studio over
HTTP (`RULER_MODEL`, `CROWD_MODEL`). Files in this directory are discovered
by `python -m src.main --probe` as `localHints`.

## Recommended LM Studio roles (2026-08)

| Role | ENV | Current default | Notes |
|------|-----|-----------------|-------|
| Ruler | `RULER_MODEL` | `qwen3.6-27b` | Keep for long JSON + decree |
| Crowd / mascot / opinion | `CROWD_MODEL` | `qwen2.5-7b-instruct` | Short Japanese JSON; lighter than Gemma dual-load pain |
| Crowd fallback | `CROWD_FALLBACK_MODEL` | `google/gemma-4-e4b` | Tried after crowd fails |

### Break-time download list (optional — not required)

This PC (7800X3D / 64GB / RTX 4070 Ti SUPER 16GB) is enough for **ruler 27B + crowd 7B**.  
No extra model is required for completion. If you want spares in LM Studio:

| Priority | Search in LM Studio | Role | Quant |
|----------|---------------------|------|-------|
| Have | `qwen3.6-27b` | Ruler | already in use |
| Have | `qwen2.5-7b-instruct` | Crowd / opinion | already in use |
| Optional | `Qwen2.5-14B-Instruct` | Stronger crowd (VRAM trade-off) | Q4_K_M |
| Optional | `Llama-3.1-8B-Instruct` | Crowd A/B compare | Q4_K_M |
| Keep unloaded | `google/gemma-4-e4b` | Fallback only | — |
| Avoid | Second 27B+ loaded with ruler | Causes empty / `terminated` | — |

After any download: Load → `python -m src.main --probe` → copy exact model id into `CROWD_MODEL`.
After download in LM Studio Discover/My Models:

```powershell
# Example: use Qwen2.5-7B as crowd, keep 27B as ruler
$env:CROWD_MODEL = "qwen2.5-7b-instruct"   # exact id from `python -m src.main --probe`
$env:CROWD_FALLBACK_MODEL = "google/gemma-4-e4b"
$env:LM_CROWD_MAX_TOKENS = "768"
$env:LM_CHAT_RETRIES = "2"
# Optional if your LM Studio build supports it:
$env:LM_USE_JSON_SCHEMA = "1"
python -m src.main --probe
python -m src.main --llm --standard zunda --start 1853-01 --end 1853-03 --log logs/runs/crowd_json_smoke.jsonl
```

Client-side mitigations already in `src/llm_client.py`:

- JSON repair (trailing commas, True/False, nested extract)
- Retries with lower temperature
- Model chain: `CROWD_MODEL` → `CROWD_FALLBACK_MODEL` → `RULER_MODEL`
- Separate `LM_CROWD_MAX_TOKENS` / `LM_OPINION_MAX_TOKENS`
