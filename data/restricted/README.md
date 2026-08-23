# Restricted data (DO NOT COMMIT / DO NOT PUBLISH)

Put local-only persona files here. **ずんだもん／あんこもんの聖書は非公開方針です。**  
Do not push them to GitHub (this repo or a public dataset repo).

## Expected filenames

| File | Purpose |
|------|---------|
| `zundamon_bible.jsonl` | ずんだもん few-shot / persona（手元のみ） |
| `ankomon_bible.txt` | あんこもん persona（手元のみ） |

Character use follows [ずん子ガイドライン](https://zunko.jp/guideline.html).  
Without these files, the sim still runs using short fallback prompts in `src/mascot.py`.

## Rule

Everything in this directory except this README is **gitignored**.  
Do not publish, mirror, or document a public download URL for these files.
