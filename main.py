"""
╔══════════════════════════════════════════════════════╗
║         CRT SCANNER — Telegram Bot                   ║
║         Candle Range Theory                          ║
║         Binance USDT-M Futures                       ║
╚══════════════════════════════════════════════════════╝

SETUP:
  1. Palitan ang BOT_TOKEN ng token mo mula sa @BotFather
  2. Palitan ang CHAT_ID ng chat id mo
  3. I-upload sa Railway/Render/VPS
  4. Done!

CRT RULES:
  BULLISH:
    C1 = Malaking GREEN candle, maliit ang wicks
    C2 = RED candle na:
         - Wick bumaba BELOW ng C1 low (sweep)
         - Close ABOVE ng C1 low (rejection)

  BEARISH:
    C1 = Malaking RED candle, maliit ang wicks
    C2 = GREEN candle na:
         - Wick umabot ABOVE ng C1 high (sweep)
         - Close BELOW ng C1 high (rejection)
"""

import os
import time
import logging
import requests
from datetime import datetime

# ─────────────────────────────────────────────────────
#  CONFIG — PALITAN MO DITO
# ─────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8702212260:AAF74coK0pDbcPUsSSvI2XGo0aUo3p5E-wc")
CHAT_ID   = os.environ.get("CHAT_ID",   "5264853786")

# Scan settings
TIMEFRAMES = ["1M", "1W", "1D", "4H", "1H"]
SCAN_INTERVAL_MINUTES = 60   # mag-scan kada ilang minuto

# CRT thresholds
BODY_MIN_RATIO = 0.60   # C1 body >= 60% ng total range
WICK_MAX_RATIO = 0.20   # bawat wick <= 20% ng total range

# Binance mirrors
API_MIRRORS = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://fapi3.binance.com",
]

BINANCE_TF_MAP = {
    "1M": "1M",
    "1W": "1w",
    "1D": "1d",
    "4H": "4h",
    "1H": "1h",
}

TV_INTERVAL_MAP = {
    "1M": "M",
    "1W": "W",
    "1D": "D",
    "4H": "240",
    "1H": "60",
}

# ─────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────
#  BINANCE API
# ─────────────────────────────────────────────────────
_working_base = None

def get_base() -> str:
    global _working_base
    if _working_base:
        return _working_base
    for mirror in API_MIRRORS:
        try:
            r = requests.get(f"{mirror}/fapi/v1/ping", timeout=6)
            if r.ok:
                log.info(f"Using Binance mirror: {mirror}")
                _working_base = mirror
                return mirror
        except Exception:
            continue
    _working_base = API_MIRRORS[0]
    return _working_base


def get_symbols() -> list:
    try:
        base = get_base()
        r = requests.get(f"{base}/fapi/v1/exchangeInfo", timeout=15)
        r.raise_for_status()
        data = r.json()
        symbols = [
            s["symbol"]
            for s in data["symbols"]
            if s["quoteAsset"] == "USDT"
            and s["status"] == "TRADING"
            and s["contractType"] == "PERPETUAL"
        ]
        log.info(f"Loaded {len(symbols)} symbols")
        return sorted(symbols)
    except Exception as e:
        log.error(f"get_symbols error: {e}")
        return []


def get_klines(symbol: str, tf: str, limit: int = 3):
    try:
        base     = get_base()
        interval = BINANCE_TF_MAP[tf]
        r = requests.get(
            f"{base}/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=8,
        )
        if not r.ok:
            return None
        data = r.json()
        if len(data) < 2:
            return None
        return [{"o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4])} for k in data]
    except Exception:
        return None

# ─────────────────────────────────────────────────────
#  CRT DETECTION
# ─────────────────────────────────────────────────────
def is_valid_c1(c: dict) -> bool:
    rng = c["h"] - c["l"]
    if rng <= 0:
        return False
    body  = abs(c["c"] - c["o"])
    upper = c["h"] - max(c["o"], c["c"])
    lower = min(c["o"], c["c"]) - c["l"]
    return (
        body  / rng >= BODY_MIN_RATIO
        and upper / rng <= WICK_MAX_RATIO
        and lower / rng <= WICK_MAX_RATIO
    )


def detect_crt(klines: list) -> dict | None:
    if not klines or len(klines) < 2:
        return None

    c1 = klines[-2]
    c2 = klines[-1]

    if not is_valid_c1(c1):
        return None

    # BULLISH
    if c1["c"] > c1["o"]:
        if c2["l"] < c1["l"] and c2["c"] > c1["l"]:
            return {
                "type":   "BULLISH",
                "emoji":  "🟢",
                "c1":     c1,
                "c2":     c2,
                "swept":  c1["l"],
                "c1_close": c1["c"],
                "c2_close": c2["c"],
            }

    # BEARISH
    if c1["c"] < c1["o"]:
        if c2["h"] > c1["h"] and c2["c"] < c1["h"]:
            return {
                "type":   "BEARISH",
                "emoji":  "🔴",
                "c1":     c1,
                "c2":     c2,
                "swept":  c1["h"],
                "c1_close": c1["c"],
                "c2_close": c2["c"],
            }

    return None

# ─────────────────────────────────────────────────────
#  TELEGRAM
# ─────────────────────────────────────────────────────
def send_telegram(message: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id":    CHAT_ID,
            "text":       message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        r = requests.post(url, json=payload, timeout=10)
        return r.ok
    except Exception as e:
        log.error(f"Telegram send error: {e}")
        return False


def fmt_price(n: float) -> str:
    if n >= 10000: return f"{n:,.2f}"
    if n >= 1:     return f"{n:.4f}"
    return f"{n:.6f}"


def build_alert(symbol: str, tf: str, sig: dict) -> str:
    base = symbol.replace("USDT", "")
    pair = f"BINANCE:{base}USDT.P"
    iv   = TV_INTERVAL_MAP.get(tf, "D")
    tv_url = f"https://www.tradingview.com/chart/?symbol={pair}&interval={iv}"

    bull = sig["type"] == "BULLISH"

    msg = (
        f"{sig['emoji']} <b>CRT {sig['type']} SETUP DETECTED</b>\n"
        f"{'─' * 28}\n"
        f"🪙 <b>Coin:</b> {symbol}\n"
        f"⏱ <b>Timeframe:</b> {tf}\n\n"
        f"<b>Candle 1</b> ({'🟢 Big Green' if bull else '🔴 Big Red'}):\n"
        f"  Close: <code>{fmt_price(sig['c1_close'])}</code>\n\n"
        f"<b>Candle 2</b> ({'🔴 Red sweep' if bull else '🟢 Green sweep'}):\n"
        f"  Close: <code>{fmt_price(sig['c2_close'])}</code>\n"
        f"  Swept: <code>{fmt_price(sig['swept'])}</code> "
        f"({'C1 Low' if bull else 'C1 High'})\n\n"
        f"📊 <a href='{tv_url}'>View on TradingView</a>\n"
        f"{'─' * 28}\n"
        f"⚠️ Educational only. I-confirm sa TradingView."
    )
    return msg

# ─────────────────────────────────────────────────────
#  SCANNER
# ─────────────────────────────────────────────────────
# Track already-alerted signals to avoid duplicates
alerted = set()


def run_scan():
    global _working_base
    _working_base = None  # reset mirror cache each scan

    log.info("=" * 50)
    log.info(f"Starting CRT scan — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    symbols = get_symbols()
    if not symbols:
        log.warning("No symbols loaded, skipping scan")
        send_telegram("⚠️ CRT Scanner: Failed to fetch symbols from Binance.")
        return

    found   = 0
    checked = 0

    for symbol in symbols:
        for tf in TIMEFRAMES:
            checked += 1
            key = f"{symbol}_{tf}"

            try:
                klines = get_klines(symbol, tf)
                sig    = detect_crt(klines)

                if sig:
                    if key not in alerted:
                        msg = build_alert(symbol, tf, sig)
                        ok  = send_telegram(msg)
                        if ok:
                            alerted.add(key)
                            found += 1
                            log.info(f"SIGNAL: {symbol} {tf} {sig['type']}")
                        time.sleep(0.3)  # avoid Telegram rate limit
                    else:
                        log.debug(f"Already alerted: {key}")
                else:
                    # Remove from alerted when signal disappears
                    alerted.discard(key)

            except Exception as e:
                log.error(f"Error scanning {symbol} {tf}: {e}")

            # Small delay to avoid Binance rate limit
            time.sleep(0.05)

    log.info(f"Scan done — checked {checked}, found {found} new signals")

    # Send summary
    summary = (
        f"📊 <b>CRT Scan Complete</b>\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"✅ Checked: {checked}\n"
        f"🎯 New Signals: {found}\n"
        f"⏱ Next scan in {SCAN_INTERVAL_MINUTES} min"
    )
    send_telegram(summary)


# ─────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────
def main():
    log.info("CRT Scanner Bot starting...")

    # Send startup message
    startup_msg = (
        f"✅ <b>CRT Scanner started!</b>\n\n"
        f"📡 Scanning Binance USDT-M Futures\n"
        f"⏱ Timeframes: {', '.join(TIMEFRAMES)}\n"
        f"🔄 Scan interval: every {SCAN_INTERVAL_MINUTES} min\n\n"
        f"First scan starting now... 🚀"
    )
    send_telegram(startup_msg)

    while True:
        try:
            run_scan()
        except Exception as e:
            log.error(f"Main loop error: {e}")
            send_telegram(f"⚠️ Scanner error: {e}")

        log.info(f"Sleeping {SCAN_INTERVAL_MINUTES} minutes until next scan...")
        time.sleep(SCAN_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
