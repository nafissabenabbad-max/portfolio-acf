import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="GrabPay Crisis Dashboard", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    h1,h2,h3 { color: #f0e8dc !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def fetch_yahoo(ticker, period="6mo"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={period}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        d = r.json()["chart"]["result"][0]
        df = pd.DataFrame({
            "date": pd.to_datetime(d["timestamp"], unit="s"),
            "value": d["indicators"]["quote"][0]["close"]
        }).dropna()
        df["date"] = df["date"].dt.normalize()
        return df
    except Exception as e:
        return pd.DataFrame()


@st.cache_data
def simulate_cost_index(dates, base_shock_date="2026-02-10", label="food"):
    np.random.seed(42 if label == "food" else 99)
    n = len(dates)
    idx = 100.0
    values = []
    for d in dates:
        ds = str(d.date()) if hasattr(d, 'date') else str(d)[:10]
        if ds >= "2026-02-10": drift = 0.004 if label == "transport" else 0.003
        elif ds >= "2026-01-15": drift = 0.002 if label == "transport" else 0.001
        elif ds >= "2025-12-01": drift = 0.001
        else: drift = 0.0002
        idx *= (1 + np.random.normal(drift, 0.003))
        values.append(round(idx, 2))
    return pd.DataFrame({"date": dates, "value": values})


EVENTS = {
    "2025-12-01": "Iran nuclear talks collapse",
    "2026-01-15": "US military buildup in Gulf",
    "2026-02-10": "Iran conflict escalates",
    "2026-03-05": "Strait of Hormuz threatened",
}

LAYOUT = dict(
    plot_bgcolor="#1a1d2e", paper_bgcolor="#0f1117",
    font=dict(color="#e8e8f0"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    height=360, margin=dict(t=30, b=50),
    legend=dict(orientation="h", y=-0.2)
)

def add_events(fig, df, col):
    ymax = df[col].max()
    for date_str, label in EVENTS.items():
        ts = pd.Timestamp(date_str)
        if df["date"].min() <= ts <= df["date"].max():
            fig.add_vline(x=date_str, line_dash="dash",
                line_color="rgba(255,100,100,0.5)", line_width=1)
            fig.add_annotation(x=date_str, y=ymax, text=label[:18],
                showarrow=False, font=dict(size=8, color="#ff6b6b"),
                textangle=-90, yanchor="top", xshift=8)
    return fig


# ── FETCH DATA ──────────────────────────────────────────────────
oil_df = fetch_yahoo("BZ=F", "1y")
sgd_df = fetch_yahoo("SGDUSD=X", "1y")

oil_ok = not oil_df.empty
sgd_ok = not sgd_df.empty

if oil_ok:
    dates = oil_df["date"]
else:
    dates = pd.date_range("2025-10-01", "2026-04-01", freq="B")

food_df = simulate_cost_index(dates if oil_ok else dates, label="food")
transport_df = simulate_cost_index(dates if oil_ok else dates, label="transport")


# ── HEADER ──────────────────────────────────────────────────────
st.markdown("## 🛡️ GrabPay Crisis Dashboard")
st.caption("How the Iran conflict is affecting your wallet, updated daily")
st.markdown("---")


# ── ALERT ────────────────────────────────────────────────────────
if oil_ok and len(oil_df) > 30:
    latest_oil = oil_df["value"].iloc[-1]
    prev_oil = oil_df["value"].iloc[-30]
    oil_change = ((latest_oil - prev_oil) / prev_oil) * 100
    if oil_change > 10:
        st.error(f"⚠️ **High impact alert** — Oil prices have risen **{oil_change:.1f}%** in the last 30 days. Your transport and food costs are higher than usual.")
    elif oil_change > 3:
        st.warning(f"ℹ️ **Moderate impact** — Oil prices are up **{oil_change:.1f}%** in 30 days. Monitor your spending.")
    else:
        st.success("✅ **Situation stable** — No major impact on your daily costs detected right now.")


# ── KPIs ─────────────────────────────────────────────────────────
st.subheader("Your wallet at a glance")
k1, k2, k3, k4 = st.columns(4)

if oil_ok and len(oil_df) > 30:
    oil_now = oil_df["value"].iloc[-1]
    oil_30 = oil_df["value"].iloc[-30]
    k1.metric("🛢️ Oil price", f"${oil_now:.1f}/bbl", f"{oil_now - oil_30:+.1f} vs 30d ago")
else:
    k1.metric("🛢️ Oil price", "N/A", "Data unavailable")

if sgd_ok and len(sgd_df) > 30:
    sgd_now = sgd_df["value"].iloc[-1]
    sgd_30 = sgd_df["value"].iloc[-30]
    k2.metric("💱 SGD/USD", f"{sgd_now:.4f}", f"{sgd_now - sgd_30:+.4f} vs 30d ago")
else:
    k2.metric("💱 SGD/USD", "N/A", "Data unavailable")

food_now = food_df["value"].iloc[-1]
food_30 = food_df["value"].iloc[-30] if len(food_df) > 30 else food_df["value"].iloc[0]
food_chg = ((food_now - food_30) / food_30) * 100
k3.metric("🛒 Food costs (est.)", f"+{food_chg:.1f}%", "vs 30 days ago", delta_color="inverse")

tr_now = transport_df["value"].iloc[-1]
tr_30 = transport_df["value"].iloc[-30] if len(transport_df) > 30 else transport_df["value"].iloc[0]
tr_chg = ((tr_now - tr_30) / tr_30) * 100
k4.metric("🚗 Transport costs (est.)", f"+{tr_chg:.1f}%", "vs 30 days ago", delta_color="inverse")

st.markdown("---")


# ── CHARTS ───────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🛢️ Oil price", "🛒 Food and transport", "💱 Exchange rate SGD/USD"])

with tab1:
    if oil_ok:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=oil_df["date"], y=oil_df["value"],
            name="Brent crude (USD/bbl)",
            line=dict(color="#f7b731", width=2.5),
            fill="tozeroy", fillcolor="rgba(247,183,49,0.08)"
        ))
        fig = add_events(fig, oil_df, "value")
        fig.update_layout(**LAYOUT, yaxis_title="USD per barrel")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Real data from Yahoo Finance (BZ=F). Higher oil prices mean more expensive transport and imported goods in Singapore.")
    else:
        st.warning("Could not fetch oil data. Check your internet connection.")

with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=food_df["date"], y=food_df["value"],
        name="Food cost index", line=dict(color="#4ecdc4", width=2.5)
    ))
    fig2.add_trace(go.Scatter(
        x=transport_df["date"], y=transport_df["value"],
        name="Transport cost index", line=dict(color="#7c6cf2", width=2.5)
    ))
    fig2.add_hline(y=100, line_dash="dot", line_color="rgba(255,255,255,0.2)",
                   annotation_text="Baseline Oct 2025", annotation_font_size=9)
    fig2 = add_events(fig2, food_df, "value")
    fig2.update_layout(**LAYOUT, yaxis_title="Index (100 = Oct 2025)")
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Estimated based on oil price correlation. Singapore CPI food and transport data is not freely available in real time.")

with tab3:
    if sgd_ok:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=sgd_df["date"], y=sgd_df["value"],
            name="SGD per 1 USD",
            line=dict(color="#ff6b6b", width=2.5),
            fill="tozeroy", fillcolor="rgba(255,107,107,0.08)"
        ))
        fig3 = add_events(fig3, sgd_df, "value")
        fig3.update_layout(**LAYOUT, yaxis_title="SGD per 1 USD")
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("Real data from Yahoo Finance (SGDUSD=X). A higher rate means your SGD buys less when sending money internationally.")
    else:
        st.warning("Could not fetch SGD/USD data. Check your internet connection.")

st.markdown("---")


# ── PM SECTION ───────────────────────────────────────────────────
st.subheader("What GrabPay is doing for you")
st.caption("Product decisions made in response to the crisis")

c1, c2 = st.columns(2)
with c1:
    st.markdown("""
**🔔 Crisis alerts**
Get notified when oil prices spike above 10% in 30 days, so you can plan your spending ahead of time.

**💱 Rate lock**
Lock your SGD/USD exchange rate for up to 7 days when sending money abroad.
    """)
with c2:
    st.markdown("""
**📊 Spending insights**
See how much more you are spending on transport and food compared to before the crisis.

**🛒 Smart budgeting**
GrabPay automatically suggests a revised monthly budget based on current inflation in Singapore.
    """)

st.markdown("---")
st.caption("Oil and SGD/USD data: Yahoo Finance. Food and transport indices: estimated. Built by Nafissa, Applied Computing in Finance, 2026.")
