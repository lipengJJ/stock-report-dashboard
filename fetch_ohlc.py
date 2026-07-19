"""
拉取日K线历史数据，写入 data/ohlc/<TICKER>.json。
用Yahoo Finance公开chart接口（免费，不需要API Key），纯机械抓取，不需要claude/LLM介入。
config/tickers.json 里配置了哪些标的，这个脚本就抓哪些。

用法：python3 fetch_ohlc.py
"""
import json
import os
import sys
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "tickers.json")
OHLC_DIR = os.path.join(BASE_DIR, "data", "ohlc")

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
HEADERS = {"User-Agent": "Mozilla/5.0"}
RANGE = "6mo"
INTERVAL = "1d"


def fetch_one(ticker):
    resp = requests.get(
        YAHOO_URL.format(ticker=ticker),
        params={"range": RANGE, "interval": INTERVAL},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    result = data["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    candles = []
    for i, ts in enumerate(timestamps):
        o, h, l, c, v = (
            quote["open"][i],
            quote["high"][i],
            quote["low"][i],
            quote["close"][i],
            quote["volume"][i],
        )
        # 停牌/数据缺失的bar，Yahoo会返回null，跳过
        if None in (o, h, l, c):
            continue
        candles.append(
            {"t": ts, "o": round(o, 4), "h": round(h, 4), "l": round(l, 4), "c": round(c, 4), "v": v}
        )
    return candles


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        tickers = json.load(f)["tickers"]

    os.makedirs(OHLC_DIR, exist_ok=True)

    for ticker in tickers:
        try:
            candles = fetch_one(ticker)
        except Exception as e:
            print(f"[skip] {ticker}: {e}", file=sys.stderr)
            continue
        out_path = os.path.join(OHLC_DIR, f"{ticker}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"ticker": ticker, "range": RANGE, "interval": INTERVAL, "candles": candles}, f)
        print(f"[ok] {ticker}: {len(candles)} bars -> {out_path}")


if __name__ == "__main__":
    main()
