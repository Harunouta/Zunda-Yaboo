# Third-party data sources (cite when using)

## Kyoto cherry flowering / March temperature reconstruction

- File: `data/raw/noaa/kyoto2010flower.txt` (also NOAA public copy)
- Investigators: Aono, Y.; Saito, S.; Kazui, K.
- NOAA landing: https://www.ncdc.noaa.gov/paleo/study/26430
- Raw URL: https://www1.ncdc.noaa.gov/pub/data/paleo/historical/phenology/japan/kyoto2010flower.txt
- Ingest: `python scripts/ingest_kyoto_cherry.py`
- Output: `data/processed/climate_monthly.csv` (gitignored; regenerate locally)

## JCDP reconstructed temperatures

- Index page: https://jcdp.jp/reconstructed-climate-indices/
- Hachioji July mean (1721–): `data/raw/jcdp/hachioji_july.csv` — Mikami 1996  
  Ingest: `python scripts/ingest_jcdp_hachioji_july.py`
- Kawanishi DJF min (1831–): `data/raw/jcdp/kawanishi_djf.csv` — Hirano et al. 2012  
  Ingest: `python scripts/ingest_jcdp_kawanishi_djf.py`
- Kawanishi July max (1830–): `data/raw/jcdp/kawanishi_july.csv`  
  Ingest: `python scripts/ingest_jcdp_kawanishi_july.py`

## JCDP WJT (West Japan Temperature)

- Page: https://jcdp.jp/instrumental-meteorological-data/
- Download monitor id 1062 → local `data/raw/jcdp/wjt1821_2000.csv` (1825–2000 monthly anomaly vs 1971–2000)
- Cite: Zaiki et al. 2006 Int. J. Climatol. 26:399-423
- Ingest: `python scripts/ingest_jcdp_wjt.py`

## JCDP typhoon landfalls 1877–2020

- CSV: https://jcdp.jp/wp-content/uploads/2021/01/TyphoonData1877-2020.csv
- Cite: Kubota et al. 2021 Climatic Change 164:29; https://jcdp.jp/reconstructed-typhoon-data/
- Ingest: `python scripts/ingest_jcdp_typhoon.py` (landfall months lower `disasterMultiplier`)

Rebuild all: `python scripts/rebuild_climate_monthly.py` then gapfill is included.

## Lake Suwa freeze / Omiwatari (winter proxy)

- Background: https://jcdp.jp/omiwatari/
- **Local dump used:** NSIDC G01377 Lake Suwa (`ARAI1`) — `data/raw/suwa/liag_freeze_thaw_table.csv` (gitignored). Unrestricted NOAA@NSIDC. Extract: `python scripts/ingest_suwa_omiwatari.py --from-nsidc`
- **CC BY 4.0 package (PASTA often 403 here):** EDI `knb-lter-ntl.327` (Sharma / Magnuson et al.)
- Japanese scholarly compilation: IRDB DOI:10.24567/0002005902
- Japanese scholarly compilation with per-year sources (license is **not** a blanket CC dump): IRDB DOI:10.24567/0002005902 (Hasegawa / Mikami / Hirano)
- Expected local file: `data/raw/suwa/omiwatari.csv` (`year,freezeDoy,omiwatari`)
- Pipeline sample (NOT authoritative): `data/redistributable/suwa_omiwatari_sample.csv`
- Ingest: `python scripts/ingest_suwa_omiwatari.py` or `--sample`

## Rice / crop series (CC vs not-CC)

- **CC BY 4.0 (easy to reuse):** Figshare prefectural crop production 1883–2022 (rice yield/area, not Edo market price) — https://doi.org/10.6084/m9.figshare.29135699
- **Government stats (often 政府標準利用規約 ≈ CC BY compatible, re-check page):** Bank of Japan IMES historical wholesale/retail price CSVs from Meiji — https://www.imes.boj.or.jp/jp/historical/hstat/hstat.html
- **Best Edo Osaka rice (public HTML, not CC):** Kobe RIEB + Mitsui Bunko Kinsei DB 1787–early Meiji — https://www.rieb.kobe-u.ac.jp/project/kinsei-db/ — cite; do not vendor the full daily dump without their terms
- There is **no** long CC-BY daily Edo rice series that replaces Kinsei. Use Kinsei (LINK) for 1787–1871 anchors; use Figshare/BOJ for 1883+

## Planned (not yet ingested)

- Kinsei DB weather: **do not use**
- See `DATA_INGEST_PLAN.md` for mortality / epidemic notes

Do not commit `data/raw/**` bulk downloads or `data/processed/**` regenerated CSVs.
