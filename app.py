"""
╔══════════════════════════════════════════════════════╗
║         CRT SCANNER — Candle Range Theory            ║
║         Binance USDT-M Futures                       ║
║                                                      ║
║  HOW TO DEPLOY:                                      ║
║  1. Upload this file to GitHub                       ║
║  2. Go to share.streamlit.io                         ║
║  3. Connect your GitHub repo                         ║
║  4. Done! Free hosting.                              ║
╚══════════════════════════════════════════════════════╝

CRT Rules:
  BULLISH:
    C1 = Big GREEN candle, small wicks (body >= 60% of range, each wick <= 20%)
    C2 = RED candle whose wick sweeps BELOW C1 low,
         but C2 CLOSES ABOVE C1 low (liquidity sweep + rejection)

  BEARISH:
    C1 = Big RED candle, small wicks
    C2 = GREEN candle whose wick sweeps ABOVE C1 high,
         but C2 CLOSES BELOW C1 high (liquidity sweep + rejection)
"""

import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="CRT Scanner — Binance Futures",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', monospace !important;
    background-color: #04080f !important;
    color: #8ba8c8 !important;
}

/* Main bg */
.stApp { background-color: #04080f !important; }

/* Header */
.main-header {
    background: linear-gradient(180deg, rgba(13,255,140,0.05) 0%, transparent 100%);
    border-bottom: 1px solid #162440;
    padding: 20px 0 16px 0;
    margin-bottom: 20px;
}
.main-title {
    font-size: 36px;
    font-weight: 900;
    color: #e8f0f8;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin: 0;
}
.main-title span { color: #0dff8c; }
.main-sub {
    font-size: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #4a6a8a;
    margin-top: 4px;
}

/* Stat cards */
.stat-card {
    background: #0c1525;
    border: 1px solid #162440;
    border-radius: 4px;
    padding: 18px 20px;
    text-align: center;
}
.stat-num {
    font-size: 42px;
    font-weight: 900;
    line-height: 1;
    margin-bottom: 6px;
}
.stat-lbl {
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #4a6a8a;
}
.num-total  { color: #00aaff; text-shadow: 0 0 20px rgba(0,170,255,0.3); }
.num-bull   { color: #0dff8c; text-shadow: 0 0 20px rgba(13,255,140,0.3); }
.num-bear   { color: #ff2d55; text-shadow: 0 0 20px rgba(255,45,85,0.3); }
.num-scanned{ color: #e8f0f8; }

/* Badges in table */
.badge-bull {
    background: rgba(13,255,140,0.1);
    border: 1px solid rgba(13,255,140,0.35);
    color: #0dff8c;
    padding: 3px 10px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}
.badge-bear {
    background: rgba(255,45,85,0.1);
    border: 1px solid rgba(255,45,85,0.35);
    color: #ff2d55;
    padding: 3px 10px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}
.badge-tf {
    background: rgba(255,204,0,0.08);
    border: 1px solid rgba(255,204,0,0.25);
    color: #ffcc00;
    padding: 3px 10px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #080f1a !important;
    border-right: 1px solid #162440 !important;
}
section[data-testid="stSidebar"] * { color: #8ba8c8 !important; }

/* Buttons */
.stButton > button {
    background: #0dff8c !important;
    color: #000 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 3px !important;
    padding: 10px 28px !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #00cc6a !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(13,255,140,0.3) !important;
}

/* Progress */
.stProgress > div > div { background: #0dff8c !important; }

/* DataFrame / Table */
.dataframe {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    background: #0c1525 !important;
    border: 1px solid #162440 !important;
}
.dataframe th {
    background: #111d30 !important;
    color: #4a6a8a !important;
    font-size: 9px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid #162440 !important;
}
.dataframe td {
    color: #8ba8c8 !important;
    border-bottom: 1px solid rgba(22,36,64,0.6) !important;
}

/* Selectbox / multiselect */
.stSelectbox > div, .stMultiSelect > div {
    background: #0c1525 !important;
    border: 1px solid #162440 !important;
}

/* Info / success / error boxes */
.stAlert { border-radius: 3px !important; }

/* Links */
a { color: #ffcc00 !important; text-decoration: none !important; }
a:hover { text-decoration: underline !important; }

/* Divider */
hr { border-color: #162440 !important; margin: 16px 0 !important; }

/* Hide Streamlit branding */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────
API_BASE = "https://fapi.binance.com"

TIMEFRAMES = {
    "1M": "1M",
    "1W": "1w",
    "1D": "1d",
    "4H": "4h",
    "1H": "1h",
}

TV_INTERVAL = {
    "1M": "M",
    "1W": "W",
    "1D": "D",
    "4H": "240",
    "1H": "60",
}

# ─────────────────────────────────────────────────────
#  BINANCE API
# ─────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_futures_symbols():
    """Get all USDT-M perpetual futures symbols."""
    try:
        r = requests.get(f"{API_BASE}/fapi/v1/exchangeInfo", timeout=10)
        r.raise_for_status()
        data = r.json()
        symbols = [
            s["symbol"]
            for s in data["symbols"]
            if s["quoteAsset"] == "USDT"
            and s["status"] == "TRADING"
            and s["contractType"] == "PERPETUAL"
        ]
        return sorted(symbols)
    except Exception as e:
        st.error(f"Failed to fetch symbols: {e}")
        return []


def get_klines(symbol: str, tf_label: str, limit: int = 3):
    """Fetch klines for a symbol and timeframe."""
    interval = TIMEFRAMES[tf_label]
    try:
        r = requests.get(
            f"{API_BASE}/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=8,
        )
        if not r.ok:
            return None
        data = r.json()
        if len(data) < 2:
            return None
        return [
            {
                "o": float(k[1]),
                "h": float(k[2]),
                "l": float(k[3]),
                "c": float(k[4]),
            }
            for k in data
        ]
    except Exception:
        return None

# ─────────────────────────────────────────────────────
#  CRT DETECTION
# ─────────────────────────────────────────────────────
def is_big_body_small_wicks(c: dict, body_min: float, wick_max: float) -> bool:
    """Check if candle has big body and small wicks."""
    rng = c["h"] - c["l"]
    if rng <= 0:
        return False
    body  = abs(c["c"] - c["o"])
    upper = c["h"] - max(c["o"], c["c"])
    lower = min(c["o"], c["c"]) - c["l"]
    return (
        body  / rng >= body_min
        and upper / rng <= wick_max
        and lower / rng <= wick_max
    )


def detect_crt(klines: list, body_min: float, wick_max: float):
    """
    Detect CRT setup from klines list.
    Returns dict with signal info or None.

    BULLISH:
      C1 = big green candle (body >= body_min, wicks <= wick_max)
      C2 = red candle: wick sweeps BELOW C1 low, but CLOSES ABOVE C1 low

    BEARISH:
      C1 = big red candle (body >= body_min, wicks <= wick_max)
      C2 = green candle: wick sweeps ABOVE C1 high, but CLOSES BELOW C1 high
    """
    if not klines or len(klines) < 2:
        return None

    c1 = klines[-2]
    c2 = klines[-1]

    if not is_big_body_small_wicks(c1, body_min, wick_max):
        return None

    # BULLISH CRT
    if c1["c"] > c1["o"]:
        if c2["l"] < c1["l"] and c2["c"] > c1["l"]:
            return {
                "type":        "Bullish",
                "c1_close":    c1["c"],
                "c2_close":    c2["c"],
                "swept_level": c1["l"],
                "c1_open":     c1["o"],
                "c1_high":     c1["h"],
                "c1_low":      c1["l"],
                "c2_low":      c2["l"],
            }

    # BEARISH CRT
    if c1["c"] < c1["o"]:
        if c2["h"] > c1["h"] and c2["c"] < c1["h"]:
            return {
                "type":        "Bearish",
                "c1_close":    c1["c"],
                "c2_close":    c2["c"],
                "swept_level": c1["h"],
                "c1_open":     c1["o"],
                "c1_high":     c1["h"],
                "c1_low":      c1["l"],
                "c2_high":     c2["h"],
            }

    return None

# ─────────────────────────────────────────────────────
#  TRADINGVIEW LINK
# ─────────────────────────────────────────────────────
def tv_link(symbol: str, tf: str) -> str:
    base = symbol.replace("USDT", "")
    pair = f"BINANCE:{base}USDT.P"
    iv   = TV_INTERVAL.get(tf, "D")
    return f"https://www.tradingview.com/chart/?symbol={pair}&interval={iv}"

# ─────────────────────────────────────────────────────
#  SCAN WORKER
# ─────────────────────────────────────────────────────
def scan_one(symbol: str, tf: str, body_min: float, wick_max: float):
    klines = get_klines(symbol, tf)
    signal = detect_crt(klines, body_min, wick_max)
    if signal:
        return {
            "Symbol":       symbol,
            "TF":           tf,
            "Setup":        signal["type"],
            "C1 Close":     signal["c1_close"],
            "C2 Close":     signal["c2_close"],
            "Swept Level":  signal["swept_level"],
            "TV Link":      tv_link(symbol, tf),
        }
    return None

# ─────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")

    body_min_pct = st.slider(
        "Min Body Ratio (%)",
        min_value=40, max_value=90, value=60, step=5,
        help="C1 body must be >= this % of total candle range"
    )
    wick_max_pct = st.slider(
        "Max Wick Ratio (%)",
        min_value=5, max_value=40, value=20, step=5,
        help="Each wick of C1 must be <= this % of total candle range"
    )

    st.markdown("---")
    st.markdown("### 🕐 Timeframes")
    tf_options = list(TIMEFRAMES.keys())
    selected_tfs = st.multiselect(
        "Select Timeframes",
        options=tf_options,
        default=tf_options,
    )

    st.markdown("---")
    st.markdown("### 🎯 Setup Filter")
    setup_filter = st.selectbox(
        "Show",
        options=["All", "Bullish Only", "Bearish Only"],
        index=0,
    )

    st.markdown("---")
    max_workers = st.slider(
        "Parallel Workers",
        min_value=2, max_value=20, value=10, step=2,
        help="Higher = faster scan but more API load"
    )

    st.markdown("---")
    st.markdown("""
    <div style="font-size:9px;color:#4a6a8a;letter-spacing:1px;line-height:1.8;text-transform:uppercase">
    CRT Scanner v2.0<br/>
    Binance USDT-M Futures<br/>
    Educational Use Only<br/>
    Not Financial Advice
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
#  MAIN HEADER
# ─────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <div class="main-title">CRT <span>Scanner</span></div>
  <div class="main-sub">Candle Range Theory · Binance USDT-M Perpetual Futures</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
#  SCAN BUTTON
# ─────────────────────────────────────────────────────
col_btn, col_info = st.columns([2, 5])
with col_btn:
    scan_clicked = st.button("▶  SCAN NOW", use_container_width=True)
with col_info:
    st.markdown("""
    <div style="font-size:10px;color:#4a6a8a;padding-top:14px;letter-spacing:1px">
    Scans all Binance USDT-M Perpetual Futures<br/>
    Monthly → Weekly → Daily → 4H → 1H
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────
#  SCAN LOGIC
# ─────────────────────────────────────────────────────
if scan_clicked:
    if not selected_tfs:
        st.warning("⚠️ Please select at least one timeframe.")
    else:
        body_min = body_min_pct / 100
        wick_max = wick_max_pct / 100

        # Fetch symbols
        with st.spinner("Fetching Binance Futures symbols..."):
            symbols = get_futures_symbols()

        if not symbols:
            st.error("Could not fetch symbols. Check your connection.")
        else:
            total_tasks = len(symbols) * len(selected_tfs)
            st.info(f"📡 Scanning **{len(symbols)} coins** × **{len(selected_tfs)} timeframes** = **{total_tasks} checks**")

            # Progress
            progress_bar  = st.progress(0)
            progress_text = st.empty()
            results_box   = st.empty()

            results       = []
            done          = 0

            # Build all tasks
            tasks = [
                (sym, tf)
                for sym in symbols
                for tf in selected_tfs
            ]

            # Run with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(scan_one, sym, tf, body_min, wick_max): (sym, tf)
                    for sym, tf in tasks
                }

                for future in as_completed(futures):
                    done += 1
                    pct = done / total_tasks

                    try:
                        res = future.result()
                        if res:
                            results.append(res)
                    except Exception:
                        pass

                    # Update progress every 10 tasks
                    if done % 10 == 0 or done == total_tasks:
                        progress_bar.progress(pct)
                        progress_text.markdown(
                            f"<span style='font-size:11px;color:#4a6a8a;letter-spacing:1px'>"
                            f"Checked {done}/{total_tasks} · Found {len(results)} signals</span>",
                            unsafe_allow_html=True,
                        )

            progress_bar.progress(1.0)
            progress_text.empty()

            # ── RESULTS ──────────────────────────────
            st.session_state["results"]      = results
            st.session_state["scan_time"]    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["coins_scanned"] = len(symbols)

# ─────────────────────────────────────────────────────
#  DISPLAY RESULTS
# ─────────────────────────────────────────────────────
results      = st.session_state.get("results", [])
scan_time    = st.session_state.get("scan_time", "—")
coins_scanned = st.session_state.get("coins_scanned", 0)

# ── STAT CARDS ────────────────────────────────────────
bull_count = sum(1 for r in results if r["Setup"] == "Bullish")
bear_count = sum(1 for r in results if r["Setup"] == "Bearish")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="stat-card">
      <div class="stat-num num-total">{len(results) or "—"}</div>
      <div class="stat-lbl">Total Signals</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="stat-card">
      <div class="stat-num num-bull">{bull_count or "—"}</div>
      <div class="stat-lbl">Bullish CRT</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="stat-card">
      <div class="stat-num num-bear">{bear_count or "—"}</div>
      <div class="stat-lbl">Bearish CRT</div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="stat-card">
      <div class="stat-num num-scanned">{coins_scanned or "—"}</div>
      <div class="stat-lbl">Coins Scanned</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div style="font-size:9px;color:#4a6a8a;letter-spacing:1px;text-align:right;margin-top:8px">
Last scan: {scan_time}
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── TABLE ─────────────────────────────────────────────
if results:
    df = pd.DataFrame(results)

    # Apply setup filter
    if "setup_filter" in locals():
        if setup_filter == "Bullish Only":
            df = df[df["Setup"] == "Bullish"]
        elif setup_filter == "Bearish Only":
            df = df[df["Setup"] == "Bearish"]

    # Format price columns
    def fmt_price(v):
        if v >= 10000: return f"{v:,.2f}"
        if v >= 1:     return f"{v:.4f}"
        return f"{v:.6f}"

    df["C1 Close"]    = df["C1 Close"].apply(fmt_price)
    df["C2 Close"]    = df["C2 Close"].apply(fmt_price)
    df["Swept Level"] = df["Swept Level"].apply(fmt_price)

    # Make TV Link clickable
    df["Chart"] = df["TV Link"].apply(
        lambda url: f'<a href="{url}" target="_blank">📈 TradingView</a>'
    )
    df = df.drop(columns=["TV Link"])

    # Reorder columns
    df = df[["Symbol", "TF", "Setup", "C1 Close", "C2 Close", "Swept Level", "Chart"]]

    st.markdown(
        df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

    # Download CSV
    csv_df = pd.DataFrame(st.session_state["results"])
    csv_data = csv_df.to_csv(index=False)
    st.download_button(
        label="⬇️  Download CSV",
        data=csv_data,
        file_name=f"crt_signals_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

elif scan_clicked:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px">
      <div style="font-size:48px;color:#162440;font-family:'IBM Plex Mono',monospace;margin-bottom:12px">◇</div>
      <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#4a6a8a;line-height:2">
        No CRT signals found on current candles.<br/>
        Try again after candle close.
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px">
      <div style="font-size:48px;color:#162440;font-family:'IBM Plex Mono',monospace;margin-bottom:12px">◈</div>
      <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#4a6a8a;line-height:2.2">
        Press SCAN NOW to start<br/>
        Scans all Binance USDT-M Perpetual Futures<br/>
        Monthly · Weekly · Daily · 4H · 1H
      </div>
    </div>
    """, unsafe_allow_html=True)
