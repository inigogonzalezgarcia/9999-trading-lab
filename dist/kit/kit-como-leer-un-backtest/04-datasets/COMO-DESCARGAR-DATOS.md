# Cómo descargar los datos originales y reproducir las ejecuciones · How to download the original data and reproduce the runs

Las velas M1 de EUR/USD 2024 no se incluyen en el kit: pertenecen a su proveedor (Dukascopy) y no se pueden redistribuir.
Se descargan gratis con el script del repositorio y se comprueba el hash.

The EUR/USD 2024 M1 candles are not included in the kit: they belong to their provider (Dukascopy) and cannot be redistributed.
They are downloaded for free with the repository script and the hash is checked.

```bash
git clone https://github.com/inigogonzalezgarcia/9999-trading-lab.git
cd 9999-trading-lab
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 1) descargar · download (ticks -> M1, con reanudación por meses · resumable month by month)
python -m backend.cli fetch dukascopy --symbol EURUSD --start 2024-01-01 --end 2025-01-01 --out data/raw/EURUSD_2024.csv
#    (o haz doble clic en scripts/fetch_history.command con YEARS="2024" · or double-click scripts/fetch_history.command with YEARS="2024")

# 2) comprobar la calidad y el hash · check quality and hash (dataset_hash debe ser · must be)
#    65a7a807004594d4a14e4408ce4abc71db1bc8f2d6c73e72a19f5ca25acde62d
python -m backend.cli validate data/raw/EURUSD_2024.csv

# 3) reproducir · reproduce (V1 = config/strategy_v1.yaml, V1.1 = config/strategy_v1_1.yaml)
python -m backend.cli backtest data/raw/EURUSD_2024.csv --strategy config/strategy_v1_1.yaml --out results/EURUSD_2024_v1_1_backtest.json
python -m backend.cli research data/raw/EURUSD_2024.csv --strategy config/strategy_v1_1.yaml --seed 7 --out results/EURUSD_2024_v1_1_research.json
```

`python -m backend.cli --help` lista todos los subcomandos; el README del repositorio es la referencia.
`python -m backend.cli --help` lists every subcommand; the repository README is the reference.

Versión del software usada en el kit · software version used in the kit: 0.2.0 · source-sha256:e5bedf30a94f7bcaa37eaa733205a69121f4ac262b9649ff40e07f24f74fb81f
Hash de configuración · configuration hash: 1ba09079be704d33d200276d5306ed197a93ced0b069adbc341c0eb62dccbbb3

Si Dukascopy limita tu IP (429/503), el script espera y reanuda por meses; deja el proceso abierto o relánzalo más tarde.
If Dukascopy rate-limits your IP (429/503), the script waits and resumes month by month; leave it running or relaunch later.

## 2022 y 2023 · 2022 and 2023

Esos años vienen de HistData.com (gratis, sin columna de spread; las ejecuciones usan 0,3 pips fijos):
Those years come from HistData.com (free, no spread column; the runs use a fixed 0.3 pips):

```bash
python3 scripts/fetch_histdata.py --years 2022 2023 --symbols EURUSD GBPUSD
python -m backend.cli backtest data/raw/EURUSD_2022.csv --strategy config/strategy_v1_1.yaml --fixed-spread-pips 0.3 --out results/EURUSD_2022_v1_1_backtest.json
python -m backend.cli research data/raw/EURUSD_2022.csv --strategy config/strategy_v1_1.yaml --fixed-spread-pips 0.3 --seed 7 --out results/EURUSD_2022_v1_1_research.json
```
