# Raw third-party downloads (gitignored)

Place originals here; do not commit.

| Folder | Expected |
|--------|----------|
| `noaa/` | `kyoto2010flower.txt` |
| `jcdp/` | `hachioji_july.csv`, `kawanishi_djf.csv`, `kawanishi_july.csv` |
| `suwa/` | `omiwatari.csv` (`year,freezeDoy,omiwatari`) — see folder README |
| `kinsei/` | `data_180301.xlsx` etc. |

Rebuild monthly climate:

```powershell
python scripts/ingest_kyoto_cherry.py
python scripts/ingest_jcdp_hachioji_july.py
python scripts/ingest_jcdp_kawanishi_djf.py
python scripts/ingest_jcdp_kawanishi_july.py
python scripts/ingest_suwa_omiwatari.py --sample
# or with local raw: python scripts/ingest_suwa_omiwatari.py
```
