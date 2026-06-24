"""
main.py — Momentum ETF Screener API
FastAPI + Alpha Vantage · Déployé sur Render.com
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import numpy as np
from datetime import datetime
import time
import asyncio

app = FastAPI(title="Momentum ETF Screener API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

AV_KEY = "4DMNSIZ0TEEUGS2L"
AV_URL = "https://www.alphavantage.co/query"

UNIVERSE = [
    {"ticker": "QDVF.DEX", "display": "QDVF", "name": "S&P 500 Energy",           "bloc": "sector"},
    {"ticker": "QDVG.DEX", "display": "QDVG", "name": "S&P 500 Financials",        "bloc": "sector"},
    {"ticker": "QDVH.DEX", "display": "QDVH", "name": "S&P 500 Health Care",       "bloc": "sector"},
    {"ticker": "QDVD.DEX", "display": "QDVD", "name": "S&P 500 Consumer Discret.", "bloc": "sector"},
    {"ticker": "QDVE.DEX", "display": "QDVE", "name": "S&P 500 Technology",        "bloc": "sector"},
    {"ticker": "QDVC.DEX", "display": "QDVC", "name": "S&P 500 Industrials",       "bloc": "sector"},
    {"ticker": "QDVI.DEX", "display": "QDVI", "name": "MSCI USA Value Factor",     "bloc": "factor"},
    {"ticker": "IWMO.LON", "display": "IWMO", "name": "MSCI World Momentum",       "bloc": "factor"},
    {"ticker": "IWQU.LON", "display": "IWQU", "name": "MSCI World Quality",        "bloc": "factor"},
    {"ticker": "WSML.LON", "display": "WSML", "name": "MSCI World Small Cap",      "bloc": "factor"},
    {"ticker": "MVOL.LON", "display": "MVOL", "name": "MSCI World Min Volatility", "bloc": "factor"},
    {"ticker": "IEMA.LON", "display": "IEMA", "name": "MSCI Emerging Markets",     "bloc": "refuge"},
    {"ticker": "IGLN.LON", "display": "IGLN", "name": "Physical Gold ETC",         "bloc": "refuge"},
    {"ticker": "IDTM.LON", "display": "IDTM", "name": "US Treasuries 7-10Y",       "bloc": "refuge"},
]

# Cache 6h
_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 6 * 3600


def calc_perf(closes, n):
    if len(closes) < n + 1:
        return None
    cur, past = closes[-1], closes[-1 - n]
    if not past or past == 0:
        return None
    return round((cur / past - 1) * 100, 2)


def calc_sma(closes, n):
    if len(closes) < n:
        return None
    return float(np.mean(closes[-n:]))


def fetch_etf(etf):
    try:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": etf["ticker"],
            "outputsize": "compact",
            "apikey": AV_KEY,
        }
        with httpx.Client(timeout=30) as client:
            r = client.get(AV_URL, params=params)
            data = r.json()

        if "Time Series (Daily)" not in data:
            note = data.get("Note") or data.get("Information") or str(data)
            raise ValueError(str(note)[:120])

        ts = data["Time Series (Daily)"]
        dates = sorted(ts.keys())
        closes = [float(ts[d]["4. close"]) for d in dates]

        if len(closes) < 30:
            raise ValueError(f"Seulement {len(closes)} jours disponibles")

        p1m = calc_perf(closes, 21)
        p3m = calc_perf(closes, 63)
        p6m = calc_perf(closes, 126)
        sma200 = calc_sma(closes, 200)
        last = round(float(closes[-1]), 4)
        above_sma200 = bool(last > sma200) if sma200 is not None else None

        valid = [v for v in [p1m, p3m, p6m] if v is not None]
        score = round(sum(valid), 2) if valid else None

        return {
            **etf,
            "ticker": etf["display"],  # on remet le ticker lisible
            "last_price": last,
            "p1m": p1m, "p3m": p3m, "p6m": p6m,
            "sma200": round(sma200, 4) if sma200 else None,
            "above_sma200": above_sma200,
            "score": score,
            "error": None,
        }

    except Exception as e:
        return {
            **etf,
            "ticker": etf["display"],
            "last_price": None, "p1m": None, "p3m": None, "p6m": None,
            "sma200": None, "above_sma200": None, "score": None,
            "error": str(e),
        }


def compute_all():
    results = []
    for i, etf in enumerate(UNIVERSE):
        result = fetch_etf(etf)
        results.append(result)
        # Alpha Vantage free = 25 req/jour, max ~5 req/min → pause entre chaque
        if i < len(UNIVERSE) - 1:
            time.sleep(13)  # 13s entre requêtes = ~4.6 req/min, safe
    return results


@app.get("/")
def root():
    return {"status": "ok", "service": "Momentum ETF Screener API"}


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/momentum")
def get_momentum(force: bool = False):
    global _cache
    now = time.time()

    if not force and _cache["data"] and (now - _cache["timestamp"]) < CACHE_TTL:
        return JSONResponse({
            "cached": True,
            "computed_at": datetime.utcfromtimestamp(_cache["timestamp"]).isoformat() + "Z",
            "results": _cache["data"],
        })

    results = compute_all()
    _cache["data"] = results
    _cache["timestamp"] = now

    return JSONResponse({
        "cached": False,
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "results": results,
    })
