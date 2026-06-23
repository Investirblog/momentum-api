"""
main.py — Momentum ETF Screener API
FastAPI + yfinance · Déployé sur Render.com
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yfinance as yf
import numpy as np
from datetime import datetime
import asyncio
from functools import lru_cache
import time

app = FastAPI(title="Momentum ETF Screener API")

# CORS — autorise toutes les origines (Netlify, fichier local, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

UNIVERSE = [
    {"ticker": "QDVF.DE", "display": "QDVF", "name": "S&P 500 Energy",           "bloc": "sector"},
    {"ticker": "QDVG.DE", "display": "QDVG", "name": "S&P 500 Financials",        "bloc": "sector"},
    {"ticker": "QDVH.DE", "display": "QDVH", "name": "S&P 500 Health Care",       "bloc": "sector"},
    {"ticker": "QDVD.DE", "display": "QDVD", "name": "S&P 500 Consumer Discret.", "bloc": "sector"},
    {"ticker": "QDVE.DE", "display": "QDVE", "name": "S&P 500 Technology",        "bloc": "sector"},
    {"ticker": "QDVC.DE", "display": "QDVC", "name": "S&P 500 Industrials",       "bloc": "sector"},
    {"ticker": "QDVI.DE", "display": "QDVI", "name": "MSCI USA Value Factor",     "bloc": "factor"},
    {"ticker": "IWMO.L",  "display": "IWMO", "name": "MSCI World Momentum",       "bloc": "factor"},
    {"ticker": "IWQU.L",  "display": "IWQU", "name": "MSCI World Quality",        "bloc": "factor"},
    {"ticker": "WSML.L",  "display": "WSML", "name": "MSCI World Small Cap",      "bloc": "factor"},
    {"ticker": "MVOL.L",  "display": "MVOL", "name": "MSCI World Min Volatility", "bloc": "factor"},
    {"ticker": "IEMA.L",  "display": "IEMA", "name": "MSCI Emerging Markets",     "bloc": "refuge"},
    {"ticker": "IGLN.L",  "display": "IGLN", "name": "Physical Gold ETC",         "bloc": "refuge"},
    {"ticker": "IDTM.L",  "display": "IDTM", "name": "US Treasuries 7-10Y",       "bloc": "refuge"},
]

# Cache simple en mémoire : données valables 6h
_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 6 * 3600  # 6 heures


def calc_perf(closes, n):
    if len(closes) < n + 1:
        return None
    cur, past = closes[-1], closes[-1 - n]
    if past == 0:
        return None
    return round((cur / past - 1) * 100, 2)


def calc_sma(closes, n):
    if len(closes) < n:
        return None
    return float(np.mean(closes[-n:]))


def fetch_etf(etf):
    try:
        df = yf.download(
            etf["ticker"],
            period="12mo",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if df.empty or len(df) < 30:
            raise ValueError("Historique insuffisant")

        closes = df["Close"].dropna().squeeze().tolist()

        p1m = calc_perf(closes, 21)
        p3m = calc_perf(closes, 63)
        p6m = calc_perf(closes, 126)
        sma200 = calc_sma(closes, 200)
        last = round(closes[-1], 4)
        above_sma200 = bool(last > sma200) if sma200 is not None else None

        valid = [v for v in [p1m, p3m, p6m] if v is not None]
        score = round(sum(valid), 2) if valid else None

        return {
            **etf,
            "last_price": last,
            "p1m": p1m,
            "p3m": p3m,
            "p6m": p6m,
            "sma200": round(sma200, 4) if sma200 else None,
            "above_sma200": above_sma200,
            "score": score,
            "error": None,
        }
    except Exception as e:
        return {
            **etf,
            "last_price": None,
            "p1m": None, "p3m": None, "p6m": None,
            "sma200": None, "above_sma200": None, "score": None,
            "error": str(e),
        }


def compute_all():
    results = []
    for etf in UNIVERSE:
        results.append(fetch_etf(etf))
    return results


@app.get("/")
def root():
    return {"status": "ok", "service": "Momentum ETF Screener API"}


@app.get("/health")
def health():
    """Endpoint de health check — utilisé par Render et UptimeRobot."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/momentum")
def get_momentum(force: bool = False):
    """
    Retourne les scores momentum pour les 14 ETF.
    Données mises en cache 6h. Passe ?force=true pour forcer le recalcul.
    """
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
