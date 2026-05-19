"""
Stock Intelligence Dashboard
Run with: streamlit run dashboard.py
"""

import sys
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

sys.path.insert(0, ".")
from tools import _get_insider_trades, _ticker_to_cik

# ------------------------------------------------------------------ #
# Page config

st.set_page_config(
    page_title="Stock Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .signal-card {
        border-radius: 10px;
        padding: 12px 16px;
        text-align: center;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .green  { background-color: #1a3a2a; color: #4caf7d; border: 1px solid #2d6a4f; }
    .red    { background-color: #3a1a1a; color: #ef5350; border: 1px solid #6a2d2d; }
    .yellow { background-color: #3a3010; color: #ffc107; border: 1px solid #6a5a10; }
    .grey   { background-color: #252525; color: #aaaaaa; border: 1px solid #444; }
    div[data-testid="metric-container"] { background: #1e1e1e; border-radius: 8px; padding: 12px; }
    .insider-buy  { color: #4caf7d; font-weight: 600; }
    .insider-sell { color: #ef5350; font-weight: 600; }
    h1, h2, h3 { color: #f0f0f0; }
    .section-header {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #888;
        border-bottom: 1px solid #333;
        padding-bottom: 4px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
# Stock universe by sector

UNIVERSE = {
    "Tech":         ["AAPL","MSFT","NVDA","AMD","GOOGL","META","AMZN","TSLA","PLTR","NET","CRWD","DDOG","SNOW","SHOP","NOW","ADBE","CRM","ORCL","INTC","QCOM","AVGO","MU","AMAT","LRCX"],
    "AI / Emerging":["AI","SOUN","IONQ","RKLB","BBAI","SMCI","MSTR","HOOD","COIN","ARM","LUNR"],
    "Finance":      ["JPM","BAC","GS","MS","V","MA","PYPL","SQ","SCHW","BLK","WFC","AXP"],
    "Healthcare":   ["LLY","UNH","ABBV","JNJ","PFE","MRNA","AMGN","GILD","ISRG","TMO","DHR"],
    "Energy":       ["XOM","CVX","OXY","SLB","PSX","VLO","EOG","PXD","HAL","COP"],
    "Consumer":     ["COST","WMT","HD","TGT","NKE","SBUX","MCD","AMZN","TSLA","LOW"],
    "ETFs":         ["SPY","QQQ","VTI","ARKK","SMH","SOXX","XLK","XLF","XLE","IWM"],
}
ALL_SECTORS = list(UNIVERSE.keys())

# ------------------------------------------------------------------ #
# Sidebar navigation

with st.sidebar:
    st.markdown("## 📊 Stock Intel")
    mode = st.radio("", ["🔍 Research a Stock", "💡 Discover Picks"], label_visibility="collapsed")
    st.markdown("---")
    if mode == "💡 Discover Picks":
        st.markdown("**Filters**")
        selected_sectors = st.multiselect("Sectors", ALL_SECTORS, default=ALL_SECTORS[:4])
        min_score = st.slider("Min score (0–10)", 0, 10, 5)
        sort_by = st.selectbox("Sort by", ["Score", "Rev Growth", "PEG Ratio", "Analyst"])
        show_only = st.selectbox("Show only", ["All", "Buys / Strong Buys", "Above 50d MA", "Low PEG (< 2)"])
        st.markdown("---")
        st.caption("Scores stocks on valuation, growth, analyst consensus, momentum, and margin. Data: Yahoo Finance.")

# ------------------------------------------------------------------ #
# Scoring engine

def score_stock(info: dict) -> tuple[int, dict]:
    """Score 0–10. Returns (score, breakdown_dict)."""
    pts = 0
    breakdown = {}

    peg = info.get("pegRatio")
    if peg and peg > 0:
        if peg < 1:    s = 3
        elif peg < 2:  s = 2
        elif peg < 3:  s = 1
        else:          s = 0
        pts += s; breakdown["PEG"] = s
    else:
        breakdown["PEG"] = "—"

    rg = info.get("revenueGrowth")
    if rg is not None:
        if rg > 0.3:   s = 2
        elif rg > 0.1: s = 1
        elif rg > 0:   s = 0
        else:          s = -1
        pts += max(s, 0); breakdown["Growth"] = s
    else:
        breakdown["Growth"] = "—"

    rec = (info.get("recommendationKey") or "").lower()
    rec_scores = {"strong_buy": 2, "buy": 1, "hold": 0, "underperform": -1, "sell": -1}
    rs = rec_scores.get(rec, 0)
    pts += max(rs, 0); breakdown["Analyst"] = rs

    price = info.get("currentPrice") or 0
    ma50  = info.get("fiftyDayAverage") or 0
    if price and ma50:
        s = 1 if price > ma50 else 0
        pts += s; breakdown["Momentum"] = s
    else:
        breakdown["Momentum"] = "—"

    margin = info.get("profitMargins")
    if margin is not None:
        if margin > 0.2:   s = 2
        elif margin > 0.1: s = 1
        elif margin > 0:   s = 0
        else:              s = -1
        pts += max(s, 0); breakdown["Margin"] = s
    else:
        breakdown["Margin"] = "—"

    return min(max(pts, 0), 10), breakdown


@st.cache_data(ttl=3600, show_spinner=False)
def scan_universe(sectors: list) -> pd.DataFrame:
    tickers = []
    for s in sectors:
        tickers.extend(UNIVERSE.get(s, []))
    tickers = list(dict.fromkeys(tickers))  # dedupe, preserve order

    rows = []
    progress = st.progress(0, text="Scanning stocks…")
    for i, sym in enumerate(tickers):
        progress.progress((i + 1) / len(tickers), text=f"Scanning {sym}…")
        try:
            info = yf.Ticker(sym).info
            if not info.get("currentPrice") and not info.get("regularMarketPrice"):
                continue
            price  = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            ma50   = info.get("fiftyDayAverage") or 0
            rg     = info.get("revenueGrowth")
            peg    = info.get("pegRatio")
            margin = info.get("profitMargins")
            rec    = (info.get("recommendationKey") or "—").replace("_", " ").title()
            target = info.get("targetMeanPrice")
            upside = ((target - price) / price * 100) if target and price else None
            score, _ = score_stock(info)
            above_ma = price > ma50 if ma50 else None
            rows.append({
                "Ticker":    sym,
                "Name":      (info.get("shortName") or info.get("longName") or sym)[:22],
                "Price":     price,
                "Score":     score,
                "PEG":       round(peg, 2) if peg else None,
                "Rev Growth":round(rg * 100, 1) if rg is not None else None,
                "Margin":    round(margin * 100, 1) if margin is not None else None,
                "Analyst":   rec,
                "Target":    round(target, 2) if target else None,
                "Upside %":  round(upside, 1) if upside is not None else None,
                "Above 50d": above_ma,
                "Sector":    next((s for s, t in UNIVERSE.items() if sym in t), "—"),
            })
        except Exception:
            continue
    progress.empty()
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ #
# Header + input

st.markdown("## 📊 Stock Intelligence Dashboard")
st.markdown("Real data. SEC filings. Insider moves. All free.")

# ------------------------------------------------------------------ #
# DISCOVER PAGE

if mode == "💡 Discover Picks":
    if not selected_sectors:
        st.warning("Select at least one sector in the sidebar.")
        st.stop()

    with st.spinner("Fetching data across your selected universe…"):
        df = scan_universe(tuple(selected_sectors))

    if df.empty:
        st.error("No data returned. Try different sectors.")
        st.stop()

    # Apply filters
    df = df[df["Score"] >= min_score]
    if show_only == "Buys / Strong Buys":
        df = df[df["Analyst"].isin(["Buy", "Strong Buy"])]
    elif show_only == "Above 50d MA":
        df = df[df["Above 50d"] == True]
    elif show_only == "Low PEG (< 2)":
        df = df[df["PEG"].notna() & (df["PEG"] < 2)]

    sort_map = {"Score": "Score", "Rev Growth": "Rev Growth", "PEG Ratio": "PEG", "Analyst": "Analyst"}
    df = df.sort_values(sort_map[sort_by], ascending=(sort_by == "PEG Ratio"), na_position="last")

    # ---- Top 3 picks ----
    top3 = df.head(3)
    st.markdown("### 🏆 Top Picks")
    cols = st.columns(3)
    for i, (_, row) in enumerate(top3.iterrows()):
        with cols[i]:
            upside_str = f"+{row['Upside %']:.1f}% upside" if row["Upside %"] and row["Upside %"] > 0 else ""
            score_color = "#4caf7d" if row["Score"] >= 7 else ("#ffc107" if row["Score"] >= 5 else "#ef5350")
            st.markdown(f"""
            <div style="background:#1e1e1e; border-radius:12px; padding:16px; border:1px solid #333; height:180px;">
              <div style="font-size:22px; font-weight:800; color:#f0f0f0;">{row['Ticker']}</div>
              <div style="font-size:12px; color:#888; margin-bottom:8px;">{row['Name']} · {row['Sector']}</div>
              <div style="font-size:28px; font-weight:700; color:#f0f0f0;">${row['Price']:,.2f}</div>
              <div style="font-size:12px; color:#aaa;">{row['Analyst']} · {upside_str}</div>
              <div style="margin-top:8px;">
                <span style="background:{score_color}22; color:{score_color}; border:1px solid {score_color}55;
                  border-radius:6px; padding:2px 10px; font-size:13px; font-weight:700;">
                  Score {row['Score']}/10
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Full table ----
    st.markdown(f"### All Picks — {len(df)} stocks")

    def color_score(val):
        if not isinstance(val, (int, float)): return ""
        if val >= 7: return "color: #4caf7d; font-weight: 700"
        if val >= 5: return "color: #ffc107; font-weight: 600"
        return "color: #ef5350"

    def color_growth(val):
        if not isinstance(val, (int, float)): return ""
        if val > 20:  return "color: #4caf7d"
        if val > 0:   return "color: #aaa"
        return "color: #ef5350"

    def color_upside(val):
        if not isinstance(val, (int, float)): return ""
        if val > 20:  return "color: #4caf7d; font-weight:600"
        if val > 0:   return "color: #aaa"
        return "color: #ef5350"

    display = df[["Ticker","Name","Sector","Price","Score","PEG","Rev Growth","Margin","Analyst","Upside %"]].copy()
    display["Price"]      = display["Price"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    display["PEG"]        = display["PEG"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    display["Rev Growth"] = display["Rev Growth"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    display["Margin"]     = display["Margin"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    display["Upside %"]   = display["Upside %"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")

    st.dataframe(
        display.reset_index(drop=True),
        hide_index=True,
        use_container_width=True,
        height=min(60 + len(display) * 35, 600),
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 Click any ticker in the table, then switch to **Research a Stock** in the sidebar and paste it in for a full deep-dive.")
    st.markdown('<div style="color:#444;font-size:11px;text-align:center;">Scores: valuation (PEG) + growth + analyst consensus + momentum + margin. Not financial advice.</div>', unsafe_allow_html=True)
    st.stop()

# ------------------------------------------------------------------ #
# RESEARCH PAGE (existing single-stock view)

col_input, col_btn, col_spacer = st.columns([2, 1, 5])
with col_input:
    ticker_input = st.text_input("Ticker", value="NVDA", label_visibility="collapsed", placeholder="Enter ticker...")
with col_btn:
    analyze = st.button("Analyze", use_container_width=True, type="primary")

ticker = ticker_input.strip().upper()

if not ticker:
    st.stop()

# ------------------------------------------------------------------ #
# Load data (cached 5 min)

@st.cache_data(ttl=300)
def load_yf(sym):
    t = yf.Ticker(sym)
    return t.info, t.history(period="3mo"), t.news

@st.cache_data(ttl=300)
def load_options(sym):
    t = yf.Ticker(sym)
    expirations = t.options
    return t, expirations

@st.cache_data(ttl=300)
def load_chain(sym, expiry):
    t = yf.Ticker(sym)
    chain = t.option_chain(expiry)
    return chain.calls, chain.puts

@st.cache_data(ttl=3600)
def load_insider(sym, days=90):
    return _get_insider_trades(sym, days, buys_only=False)

def compute_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> float:
    strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
    pain = {}
    for s in strikes:
        call_loss = ((calls["strike"] - s).clip(lower=0) * calls["openInterest"]).sum()
        put_loss  = ((s - puts["strike"]).clip(lower=0)  * puts["openInterest"]).sum()
        pain[s] = call_loss + put_loss
    return min(pain, key=pain.get) if pain else 0

def flag_unusual(df: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
    df = df.copy()
    df["unusual"] = (
        (df["volume"] > 0) &
        (df["openInterest"] > 0) &
        (df["volume"] / df["openInterest"].replace(0, float("nan")) >= threshold)
    )
    return df

def parse_insider_sentiment(insider_text: str) -> tuple[float, float]:
    """Return (total_buy_value, total_sell_value) from insider text."""
    buy_val = sell_val = 0.0
    for line in insider_text.split("\n"):
        if "BUY" in line and "shares @" in line:
            pass  # parsed below
        if "= $" in line:
            try:
                val = float(line.split("= $")[-1].replace(",","").replace("*** LARGE BUY ***","").strip())
                if "SELL" in insider_text.split(line)[0].split("\n")[-2]:
                    sell_val += val
                else:
                    buy_val += val
            except Exception:
                pass
    # fallback: use summary line
    for line in insider_text.split("\n"):
        if "Total insider buying:" in line:
            try: buy_val = float(line.split("$")[-1].replace(",","").strip())
            except: pass
        if "Total insider selling:" in line:
            try: sell_val = float(line.split("$")[-1].replace(",","").strip())
            except: pass
    return buy_val, sell_val

def compute_conviction(
    row: pd.Series,
    side: str,          # "CALLS" or "PUTS"
    expiry: str,        # "2025-06-20"
    current_price: float,
    info: dict,
    insider_text: str,
) -> tuple[int, dict]:
    """
    Score 0–10 combining options flow quality + fundamentals + insider + momentum + analyst.
    Returns (score, breakdown) where breakdown explains each component.
    """
    breakdown = {}
    total = 0

    # ── 1. OPTIONS FLOW QUALITY (0–3 pts) ──────────────────────────────
    oi  = row.get("openInterest", 0) or 0
    vol = row.get("volume", 0) or 0
    ratio = vol / oi if oi > 0 else 0
    if ratio >= 10:   flow_pts = 3
    elif ratio >= 5:  flow_pts = 2
    elif ratio >= 3:  flow_pts = 1
    else:             flow_pts = 0
    total += flow_pts
    breakdown["Flow strength"] = (flow_pts, 3, f"Vol/OI {ratio:.1f}× — {'explosive' if ratio>=10 else 'strong' if ratio>=5 else 'moderate'} new position")

    # ── 2. TIMING — days to expiry (0–1 pt) ────────────────────────────
    try:
        days_out = (datetime.strptime(expiry, "%Y-%m-%d").date() - datetime.now().date()).days
    except Exception:
        days_out = 0
    if 7 <= days_out <= 45: timing_pts = 1
    elif days_out < 7:      timing_pts = 0   # too short, likely closing
    else:                   timing_pts = 0   # too far, less directional
    total += timing_pts
    breakdown["Expiry timing"] = (timing_pts, 1, f"{days_out}d out — {'sweet spot 1–6 wks' if timing_pts else 'outside ideal window'}")

    # ── 3. POSITION TYPE — OTM is more directional (0–1 pt) ────────────
    strike = row.get("strike", current_price)
    itm    = row.get("inTheMoney", False)
    if side == "CALLS":
        otm_pts = 0 if itm else 1   # OTM call = pure directional bet
    else:
        otm_pts = 0 if itm else 1   # OTM put = pure directional bet
    total += otm_pts
    breakdown["Contract type"] = (otm_pts, 1, f"{'ITM — could be hedge' if itm else 'OTM — directional bet, higher conviction'}")

    # ── 4. FUNDAMENTAL QUALITY (0–2 pts) ───────────────────────────────
    fund_score, _ = score_stock(info)
    fund_pts = 2 if fund_score >= 7 else (1 if fund_score >= 4 else 0)
    total += fund_pts
    breakdown["Fundamentals"] = (fund_pts, 2, f"Stock score {fund_score}/10")

    # ── 5. INSIDER ALIGNMENT (0–2 pts, -1 if opposed) ──────────────────
    buy_val, sell_val = parse_insider_sentiment(insider_text)
    net_insider = buy_val - sell_val
    if side == "CALLS":
        if net_insider > 0:     ins_pts = 2    # insiders buying + bullish options = strong
        elif net_insider < -500_000: ins_pts = -1  # insiders selling while calls swept
        else:                   ins_pts = 0
    else:  # PUTS
        if net_insider < -500_000: ins_pts = 1  # insiders selling + put sweep = aligned
        elif net_insider > 0:   ins_pts = -1    # insiders buying but puts swept = conflict
        else:                   ins_pts = 0
    total += ins_pts
    if ins_pts == 2:   ins_label = f"Insiders net buying ${buy_val/1e6:.1f}M — ALIGNED ✓"
    elif ins_pts == 1: ins_label = f"Insiders selling — aligns with put sweep ✓"
    elif ins_pts == -1:ins_label = f"Insiders {'buying' if side=='PUTS' else 'selling'} — CONFLICTS with this options bet ✗"
    else:              ins_label = "No significant insider activity"
    breakdown["Insider activity"] = (ins_pts, 2, ins_label)

    # ── 6. MOMENTUM (0–1 pt) ────────────────────────────────────────────
    ma50  = info.get("fiftyDayAverage")  or 0
    ma200 = info.get("twoHundredDayAverage") or 0
    if side == "CALLS":
        mom_pts = 1 if (ma50 and current_price > ma50) else 0
        mom_label = f"Price {'above' if mom_pts else 'below'} 50d MA — {'bullish setup' if mom_pts else 'fighting the trend'}"
    else:
        mom_pts = 1 if (ma50 and current_price < ma50) else 0
        mom_label = f"Price {'below' if mom_pts else 'above'} 50d MA — {'bearish setup' if mom_pts else 'fighting the trend'}"
    total += mom_pts
    breakdown["Momentum"] = (mom_pts, 1, mom_label)

    # ── 7. ANALYST CONSENSUS (0–1 pt) ───────────────────────────────────
    rec = (info.get("recommendationKey") or "").lower()
    if side == "CALLS":
        an_pts = 1 if rec in ("strong_buy", "buy") else 0
        an_label = f"Analysts say {rec.replace('_',' ').title()} — {'aligned' if an_pts else 'cautious'}"
    else:
        an_pts = 1 if rec in ("sell", "underperform") else 0
        an_label = f"Analysts say {rec.replace('_',' ').title()} — {'aligned with put' if an_pts else 'not bearish'}"
    total += an_pts
    breakdown["Analyst consensus"] = (an_pts, 1, an_label)

    final = max(0, min(10, total))
    return final, breakdown

with st.spinner(f"Loading {ticker}..."):
    try:
        info, hist, news = load_yf(ticker)
    except Exception as e:
        st.error(f"Could not load {ticker}: {e}")
        st.stop()

# ------------------------------------------------------------------ #
# Price header

name = info.get("longName", ticker)
price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
prev_close = info.get("previousClose", price)
change = price - prev_close
change_pct = (change / prev_close * 100) if prev_close else 0
arrow = "▲" if change >= 0 else "▼"
price_color = "#4caf7d" if change >= 0 else "#ef5350"

st.markdown(f"""
<div style="margin: 4px 0 20px 0;">
  <span style="font-size:26px; font-weight:700; color:#f0f0f0;">{name}</span>
  <span style="font-size:15px; color:#888; margin-left:8px;">({ticker}) · {info.get('sector','—')} · {info.get('exchange','—')}</span><br>
  <span style="font-size:40px; font-weight:800; color:#f0f0f0;">${price:,.2f}</span>
  <span style="font-size:20px; font-weight:600; color:{price_color}; margin-left:12px;">{arrow} ${abs(change):.2f} ({change_pct:+.2f}%)</span>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
# Signal bar

def signal(label, value, condition, note=""):
    if condition is None:
        css = "grey"; icon = "—"
    elif condition == "good":
        css = "green"; icon = "✓"
    elif condition == "warn":
        css = "yellow"; icon = "⚠"
    else:
        css = "red"; icon = "✗"
    return f'<div class="signal-card {css}">{icon} {label}<br><small style="font-weight:400">{note}</small></div>'

peg       = info.get("pegRatio")
pe        = info.get("trailingPE")
rev_g     = info.get("revenueGrowth")
margins   = info.get("profitMargins")
rec       = info.get("recommendationKey", "")
price50   = info.get("fiftyDayAverage")
beta      = info.get("beta")
short_pct = info.get("shortPercentOfFloat")

val_cond  = "good" if peg and peg < 1.5 else ("warn" if peg and peg < 3 else ("bad" if peg else None))
val_note  = f"PEG {peg:.2f}" if peg else "No PEG data"

grow_cond = "good" if rev_g and rev_g > 0.2 else ("warn" if rev_g and rev_g > 0 else ("bad" if rev_g else None))
grow_note = f"{rev_g*100:.1f}% rev growth" if rev_g else "No data"

rec_map   = {"strong_buy":"good","buy":"good","hold":"warn","underperform":"bad","sell":"bad"}
an_cond   = rec_map.get(rec.lower(), None)
an_note   = rec.replace("_"," ").title() if rec else "No rating"

mom_cond  = "good" if price50 and price > price50 else ("bad" if price50 else None)
mom_note  = f"{'Above' if price > price50 else 'Below'} 50d MA" if price50 else "No data"

short_cond = "good" if short_pct and short_pct < 0.05 else ("warn" if short_pct and short_pct < 0.15 else ("bad" if short_pct else None))
short_note = f"{short_pct*100:.1f}% short" if short_pct else "No data"

st.markdown('<div class="section-header">Signal Summary</div>', unsafe_allow_html=True)
s1, s2, s3, s4, s5 = st.columns(5)
with s1: st.markdown(signal("Valuation", peg, val_cond, val_note), unsafe_allow_html=True)
with s2: st.markdown(signal("Growth", rev_g, grow_cond, grow_note), unsafe_allow_html=True)
with s3: st.markdown(signal("Analyst", rec, an_cond, an_note), unsafe_allow_html=True)
with s4: st.markdown(signal("Momentum", price50, mom_cond, mom_note), unsafe_allow_html=True)
with s5: st.markdown(signal("Short Interest", short_pct, short_cond, short_note), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
# Three columns: Chart | Fundamentals | Insider + News

col_chart, col_fund, col_right = st.columns([3, 2, 2])

# --- Price Chart ---
with col_chart:
    st.markdown('<div class="section-header">3-Month Price</div>', unsafe_allow_html=True)
    if not hist.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["Close"],
            mode="lines",
            line=dict(color=price_color, width=2),
            fill="tozeroy",
            fillcolor=f"{'rgba(76,175,125,0.08)' if change >= 0 else 'rgba(239,83,80,0.08)'}",
            name="Close",
        ))
        fig.add_hline(y=price50, line_dash="dash", line_color="#555", annotation_text="50d MA", annotation_font_color="#888")
        target = info.get("targetMeanPrice")
        if target:
            fig.add_hline(y=target, line_dash="dot", line_color="#ffc107",
                          annotation_text=f"Target ${target:.0f}", annotation_font_color="#ffc107")
        fig.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=4, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#555"),
            yaxis=dict(showgrid=True, gridcolor="#2a2a2a", color="#555"),
            showlegend=False,
        )
        st.plotly_chart(fig, config={"displayModeBar": False}, use_container_width=True)

# --- Fundamentals ---
with col_fund:
    st.markdown('<div class="section-header">Fundamentals</div>', unsafe_allow_html=True)

    def row(label, val):
        return {"Metric": label, "Value": str(val) if val not in (None, "N/A") else "—"}

    def pct(v):
        return f"{v*100:.1f}%" if v is not None else "—"

    def money(v):
        if v is None: return "—"
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        return f"${v/1e6:.0f}M"

    rows = [
        row("Market Cap",    money(info.get("marketCap"))),
        row("P/E (TTM)",     f"{pe:.1f}" if pe else "—"),
        row("Fwd P/E",       f"{info.get('forwardPE'):.1f}" if info.get('forwardPE') else "—"),
        row("PEG Ratio",     f"{peg:.2f}" if peg else "—"),
        row("EPS (TTM)",     f"${info.get('trailingEps'):.2f}" if info.get('trailingEps') else "—"),
        row("Revenue",       money(info.get("totalRevenue"))),
        row("Rev Growth",    pct(rev_g)),
        row("Gross Margin",  pct(info.get("grossMargins"))),
        row("Profit Margin", pct(margins)),
        row("ROE",           pct(info.get("returnOnEquity"))),
        row("Free Cash Flow",money(info.get("freeCashflow"))),
        row("Debt/Equity",   f"{info.get('debtToEquity'):.1f}" if info.get('debtToEquity') else "—"),
        row("Beta",          f"{beta:.2f}" if beta else "—"),
        row("Dividend Yield",pct(info.get("dividendYield"))),
        row("Analyst Target",f"${info.get('targetMeanPrice'):.2f}" if info.get('targetMeanPrice') else "—"),
        row("# Analysts",    info.get("numberOfAnalystOpinions", "—")),
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, width="stretch", height=480)

# --- Insider Trades + News ---
with col_right:
    # Insider trades
    st.markdown('<div class="section-header">Insider Trades (90 days)</div>', unsafe_allow_html=True)
    with st.spinner("Loading SEC filings..."):
        insider_text = load_insider(ticker, days=90)

    if "No insider" in insider_text:
        st.markdown('<span style="color:#888; font-size:13px;">No trades filed in 90 days.</span>', unsafe_allow_html=True)
    else:
        lines = insider_text.split("\n")
        buy_count = sell_count = 0
        buy_val = sell_val = 0.0
        entries = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("[") and ("] BUY" in line or "] SELL" in line):
                action = "BUY" if "] BUY" in line else "SELL"
                date = line[1:11]
                who = line.split("] BUY" if action == "BUY" else "] SELL")[-1].strip()
                val_line = lines[i+1].strip() if i+1 < len(lines) else ""
                val_part = val_line.split("= $")[-1].replace("*** LARGE BUY ***","").strip().replace(",","")
                try:
                    val = float(val_part)
                except ValueError:
                    val = 0
                entries.append({"date": date, "action": action, "who": who, "value": val})
                if action == "BUY":
                    buy_count += 1; buy_val += val
                else:
                    sell_count += 1; sell_val += val
            i += 1

        ratio = buy_val / sell_val if sell_val else float("inf")
        ratio_color = "#4caf7d" if ratio > 1 else "#ef5350"
        ratio_label = "BULLISH" if ratio > 1 else "BEARISH"
        st.markdown(
            f'<div style="font-size:12px; margin-bottom:8px;">'
            f'Buy/Sell ratio: <b style="color:{ratio_color}">{ratio:.2f}x — {ratio_label}</b> &nbsp;|&nbsp; '
            f'<span style="color:#4caf7d">{buy_count} buys</span> / <span style="color:#ef5350">{sell_count} sells</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for e in entries[:12]:
            color = "#4caf7d" if e["action"] == "BUY" else "#ef5350"
            icon  = "▲" if e["action"] == "BUY" else "▼"
            val_str = f"${e['value']:,.0f}" if e["value"] else ""
            st.markdown(
                f'<div style="font-size:12px; padding:4px 0; border-bottom:1px solid #222;">'
                f'<span style="color:{color}; font-weight:700;">{icon} {e["action"]}</span> '
                f'<span style="color:#ccc;">{e["who"][:30]}</span> '
                f'<span style="color:#888; float:right;">{val_str}</span>'
                f'<br><span style="color:#555; font-size:11px;">{e["date"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # News
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Recent News</div>', unsafe_allow_html=True)
    if news:
        for item in news[:6]:
            title = item.get("content", {}).get("title") or item.get("title", "")
            url   = item.get("content", {}).get("canonicalUrl", {}).get("url") or item.get("link", "#")
            pub   = item.get("content", {}).get("provider", {}).get("displayName") or item.get("publisher", "")
            if title:
                st.markdown(
                    f'<div style="font-size:12px; padding:5px 0; border-bottom:1px solid #222;">'
                    f'<a href="{url}" target="_blank" style="color:#90caf9; text-decoration:none;">{title}</a>'
                    f'<br><span style="color:#555; font-size:11px;">{pub}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown('<span style="color:#888; font-size:13px;">No news available.</span>', unsafe_allow_html=True)

# ------------------------------------------------------------------ #
# ------------------------------------------------------------------ #
# Options Flow section

st.markdown("---")
st.markdown("### Options Flow")

_, expirations = load_options(ticker)

if not expirations:
    st.info("No options data available for this ticker.")
else:
    # Controls row
    oc1, oc2, oc3, oc4 = st.columns([2, 1, 1, 3])
    with oc1:
        expiry = st.selectbox("Expiration", expirations, label_visibility="visible")
    with oc2:
        chain_view = st.radio("Show", ["Both", "Calls", "Puts"], horizontal=True, label_visibility="visible")
    with oc3:
        atm_only = st.checkbox("Near money only", value=True)

    calls_raw, puts_raw = load_chain(ticker, expiry)

    # Clean up
    for df in [calls_raw, puts_raw]:
        for col in ["volume", "openInterest"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        df["impliedVolatility"] = pd.to_numeric(df["impliedVolatility"], errors="coerce")

    calls_raw = flag_unusual(calls_raw)
    puts_raw  = flag_unusual(puts_raw)

    # Key metrics
    total_call_vol = int(calls_raw["volume"].sum())
    total_put_vol  = int(puts_raw["volume"].sum())
    pc_ratio = total_put_vol / total_call_vol if total_call_vol else 0
    max_pain = compute_max_pain(calls_raw, puts_raw)
    unusual_calls = calls_raw[calls_raw["unusual"]]
    unusual_puts  = puts_raw[puts_raw["unusual"]]
    avg_iv_calls  = calls_raw["impliedVolatility"].median()
    avg_iv_puts   = puts_raw["impliedVolatility"].median()

    pc_color = "#4caf7d" if pc_ratio < 0.7 else ("#ffc107" if pc_ratio < 1.0 else "#ef5350")
    pc_label = "BULLISH" if pc_ratio < 0.7 else ("NEUTRAL" if pc_ratio < 1.0 else "BEARISH")

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"""
        <div style="background:#1e1e1e;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:11px;color:#888;text-transform:uppercase;">Put/Call Ratio</div>
          <div style="font-size:26px;font-weight:800;color:{pc_color};">{pc_ratio:.2f}</div>
          <div style="font-size:11px;color:{pc_color};">{pc_label}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div style="background:#1e1e1e;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:11px;color:#888;text-transform:uppercase;">Max Pain</div>
          <div style="font-size:26px;font-weight:800;color:#f0f0f0;">${max_pain:,.0f}</div>
          <div style="font-size:11px;color:#888;">price favors MMs</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div style="background:#1e1e1e;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:11px;color:#888;text-transform:uppercase;">Call Volume</div>
          <div style="font-size:26px;font-weight:800;color:#4caf7d;">{total_call_vol:,}</div>
          <div style="font-size:11px;color:#555;">IV median {avg_iv_calls*100:.0f}%</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div style="background:#1e1e1e;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:11px;color:#888;text-transform:uppercase;">Put Volume</div>
          <div style="font-size:26px;font-weight:800;color:#ef5350;">{total_put_vol:,}</div>
          <div style="font-size:11px;color:#555;">IV median {avg_iv_puts*100:.0f}%</div>
        </div>""", unsafe_allow_html=True)
    with m5:
        unusual_total = len(unusual_calls) + len(unusual_puts)
        flag_color = "#ffc107" if unusual_total > 0 else "#555"
        st.markdown(f"""
        <div style="background:#1e1e1e;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:11px;color:#888;text-transform:uppercase;">Unusual Activity</div>
          <div style="font-size:26px;font-weight:800;color:{flag_color};">{unusual_total}</div>
          <div style="font-size:11px;color:{flag_color};">{"⚡ contracts flagged" if unusual_total else "nothing unusual"}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Unusual activity alerts with conviction scores
    if unusual_total > 0:
        with st.expander(f"⚡ Unusual Activity — {unusual_total} contract(s) flagged", expanded=True):
            st.caption("Conviction score (0–10) stacks options flow + fundamentals + insider alignment + momentum + analyst consensus. Higher = more signals pointing the same direction.")

            # legend
            st.markdown("""
            <div style="display:flex;gap:12px;margin-bottom:12px;font-size:11px;">
              <span style="background:#1a3a2a;color:#4caf7d;border:1px solid #2d6a4f;padding:2px 8px;border-radius:4px;">8–10 HIGH conviction</span>
              <span style="background:#3a3010;color:#ffc107;border:1px solid #6a5a10;padding:2px 8px;border-radius:4px;">5–7 MODERATE</span>
              <span style="background:#3a1a1a;color:#ef5350;border:1px solid #6a2d2d;padding:2px 8px;border-radius:4px;">0–4 LOW — be careful</span>
            </div>
            """, unsafe_allow_html=True)

            for label, df_u in [("CALLS", unusual_calls), ("PUTS", unusual_puts)]:
                if df_u.empty: continue
                for _, r in df_u.iterrows():
                    conv_score, conv_breakdown = compute_conviction(
                        r, label, expiry, price, info, insider_text
                    )
                    ratio_u = r["volume"] / r["openInterest"] if r["openInterest"] else 0
                    opt_color = "#4caf7d" if label == "CALLS" else "#ef5350"
                    itm_label = "ITM" if r.get("inTheMoney") else "OTM"

                    if conv_score >= 8:   score_color, score_label = "#4caf7d", "HIGH"
                    elif conv_score >= 5: score_color, score_label = "#ffc107", "MODERATE"
                    else:                 score_color, score_label = "#ef5350", "LOW"

                    action_text = {
                        "HIGH":     "Strong setup — signals aligned. Consider entering with defined risk.",
                        "MODERATE": "Interesting but mixed signals. Watch for price confirmation first.",
                        "LOW":      "Flags don't stack up. Could be a hedge or noise — sit this one out.",
                    }[score_label]

                    st.markdown(f"""
                    <div style="background:#111;border-left:4px solid {opt_color};padding:12px 16px;margin:8px 0;border-radius:6px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                          <span style="color:{opt_color};font-weight:700;font-size:15px;">{label}</span>
                          <span style="color:#f0f0f0;font-weight:700;font-size:15px;margin-left:8px;">Strike ${r['strike']:,.0f}</span>
                          <span style="color:#888;font-size:12px;margin-left:8px;">{itm_label} · Exp {expiry}</span>
                        </div>
                        <div style="text-align:right;">
                          <span style="background:{score_color}22;color:{score_color};border:1px solid {score_color}55;
                            border-radius:6px;padding:4px 14px;font-size:18px;font-weight:800;">
                            {conv_score}/10
                          </span>
                          <div style="color:{score_color};font-size:11px;font-weight:600;margin-top:2px;">{score_label} CONVICTION</div>
                        </div>
                      </div>

                      <div style="margin:8px 0;font-size:12px;color:#aaa;">
                        Vol <b style="color:#f0f0f0">{r['volume']:,}</b> vs OI <b style="color:#f0f0f0">{r['openInterest']:,}</b>
                        <span style="color:{opt_color}"> ({ratio_u:.1f}×)</span> ·
                        IV <b>{r['impliedVolatility']*100:.0f}%</b> ·
                        Last <b>${r['lastPrice']:.2f}</b> ·
                        Bid/Ask <b>${r['bid']:.2f} / ${r['ask']:.2f}</b>
                      </div>

                      <div style="font-size:12px;color:{score_color};font-style:italic;margin-bottom:8px;">
                        → {action_text}
                      </div>

                      <div style="display:flex;flex-wrap:wrap;gap:6px;">
                    """, unsafe_allow_html=True)

                    for signal_name, (pts, max_pts, desc) in conv_breakdown.items():
                        if isinstance(pts, (int, float)) and pts < 0:
                            chip_color, chip_bg = "#ef5350", "#3a1a1a"
                            pts_str = f"{pts}"
                        elif isinstance(pts, (int, float)) and pts > 0:
                            chip_color, chip_bg = "#4caf7d", "#1a3a2a"
                            pts_str = f"+{pts}"
                        else:
                            chip_color, chip_bg = "#888", "#222"
                            pts_str = "0"
                        st.markdown(f"""
                        <div title="{desc}" style="background:{chip_bg};color:{chip_color};border:1px solid {chip_color}44;
                          border-radius:4px;padding:3px 8px;font-size:11px;cursor:help;">
                          <b>{pts_str}/{max_pts}</b> {signal_name}
                          <div style="font-size:10px;color:#777;max-width:200px;">{desc[:60]}{'…' if len(desc)>60 else ''}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("</div></div>", unsafe_allow_html=True)

    # Filter to near-the-money strikes
    if atm_only:
        band = price * 0.15
        calls_disp = calls_raw[(calls_raw["strike"] >= price - band) & (calls_raw["strike"] <= price + band)]
        puts_disp  = puts_raw[(puts_raw["strike"] >= price - band)   & (puts_raw["strike"] <= price + band)]
    else:
        calls_disp, puts_disp = calls_raw, puts_raw

    # IV smile chart
    iv_calls = calls_disp[calls_disp["impliedVolatility"].notna()].sort_values("strike")
    iv_puts  = puts_disp[puts_disp["impliedVolatility"].notna()].sort_values("strike")

    if not iv_calls.empty or not iv_puts.empty:
        fig_iv = go.Figure()
        if not iv_calls.empty:
            fig_iv.add_trace(go.Scatter(
                x=iv_calls["strike"], y=iv_calls["impliedVolatility"] * 100,
                mode="lines+markers", name="Call IV",
                line=dict(color="#4caf7d", width=2),
                marker=dict(size=5),
            ))
        if not iv_puts.empty:
            fig_iv.add_trace(go.Scatter(
                x=iv_puts["strike"], y=iv_puts["impliedVolatility"] * 100,
                mode="lines+markers", name="Put IV",
                line=dict(color="#ef5350", width=2),
                marker=dict(size=5),
            ))
        fig_iv.add_vline(x=price, line_dash="dash", line_color="#ffc107",
                         annotation_text=f"Current ${price:.0f}", annotation_font_color="#ffc107")
        fig_iv.add_vline(x=max_pain, line_dash="dot", line_color="#888",
                         annotation_text=f"Max Pain ${max_pain:.0f}", annotation_font_color="#888")
        fig_iv.update_layout(
            title=dict(text="IV Smile — Implied Volatility by Strike", font=dict(size=13, color="#aaa")),
            height=240,
            margin=dict(l=0, r=0, t=36, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#555", title="Strike"),
            yaxis=dict(showgrid=True, gridcolor="#2a2a2a", color="#555", title="IV %"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaa")),
        )
        st.plotly_chart(fig_iv, use_container_width=True, config={"displayModeBar": False})

    # Options chain tables
    def format_chain(df: pd.DataFrame, side: str) -> pd.DataFrame:
        color_col = "🟢" if side == "CALLS" else "🔴"
        out = pd.DataFrame()
        out["Strike"]  = df["strike"].apply(lambda x: f"${x:,.0f}")
        out["Last"]    = df["lastPrice"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")
        out["Bid"]     = df["bid"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")
        out["Ask"]     = df["ask"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")
        out["Volume"]  = df["volume"].apply(lambda x: f"{int(x):,}")
        out["OI"]      = df["openInterest"].apply(lambda x: f"{int(x):,}")
        out["IV"]      = df["impliedVolatility"].apply(lambda x: f"{x*100:.0f}%" if pd.notna(x) else "—")
        out["ITM"]     = df["inTheMoney"].apply(lambda x: "✓" if x else "")
        out["⚡"]      = df["unusual"].apply(lambda x: "⚡" if x else "")
        return out

    chain_cols = st.columns(2) if chain_view == "Both" else [st.container()]

    if chain_view in ("Both", "Calls"):
        with chain_cols[0]:
            st.markdown('<div class="section-header" style="color:#4caf7d;">CALLS</div>', unsafe_allow_html=True)
            st.dataframe(
                format_chain(calls_disp.sort_values("strike"), "CALLS"),
                hide_index=True, use_container_width=True,
                height=min(60 + len(calls_disp) * 35, 500),
            )

    if chain_view in ("Both", "Puts"):
        with chain_cols[1] if chain_view == "Both" else chain_cols[0]:
            st.markdown('<div class="section-header" style="color:#ef5350;">PUTS</div>', unsafe_allow_html=True)
            st.dataframe(
                format_chain(puts_disp.sort_values("strike"), "PUTS"),
                hide_index=True, use_container_width=True,
                height=min(60 + len(puts_disp) * 35, 500),
            )

    # Open Interest bar chart
    oi_calls = calls_disp.groupby("strike")["openInterest"].sum().reset_index()
    oi_puts  = puts_disp.groupby("strike")["openInterest"].sum().reset_index()
    if not oi_calls.empty or not oi_puts.empty:
        fig_oi = go.Figure()
        if not oi_calls.empty:
            fig_oi.add_trace(go.Bar(x=oi_calls["strike"], y=oi_calls["openInterest"],
                                    name="Call OI", marker_color="#4caf7d", opacity=0.75))
        if not oi_puts.empty:
            fig_oi.add_trace(go.Bar(x=oi_puts["strike"], y=oi_puts["openInterest"],
                                    name="Put OI",  marker_color="#ef5350", opacity=0.75))
        fig_oi.add_vline(x=price, line_dash="dash", line_color="#ffc107",
                         annotation_text=f"${price:.0f}", annotation_font_color="#ffc107")
        fig_oi.add_vline(x=max_pain, line_dash="dot", line_color="#888",
                         annotation_text=f"Max Pain", annotation_font_color="#888")
        fig_oi.update_layout(
            title=dict(text="Open Interest by Strike — where the big money is sitting", font=dict(size=13, color="#aaa")),
            barmode="group", height=240,
            margin=dict(l=0, r=0, t=36, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#555"),
            yaxis=dict(showgrid=True, gridcolor="#2a2a2a", color="#555"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaa")),
        )
        st.plotly_chart(fig_oi, use_container_width=True, config={"displayModeBar": False})

# ------------------------------------------------------------------ #
# Footer

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div style="color:#444; font-size:11px; text-align:center;">'
    'Data: Yahoo Finance (15min delay) · SEC EDGAR (48hr lag) · '
    'Not financial advice. Do your own research.'
    '</div>',
    unsafe_allow_html=True,
)
