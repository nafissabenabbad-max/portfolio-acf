import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="Stock Dashboard", page_icon="📈", layout="wide")
st.markdown("""<style>
    .stApp { background-color: #0f1117; }
    h1,h2,h3,p,label,div { color: #e8e8f0; }
</style>""", unsafe_allow_html=True)

st.title("📈 Stock Market Dashboard")
st.caption("Tech stocks & ETFs — including Halal alternatives | Data via Yahoo Finance")

TICKERS = {
    "Tech Stocks": {"NVDA":"Nvidia","AAPL":"Apple","AMZN":"Amazon","MSFT":"Microsoft","GOOGL":"Alphabet"},
    "ETFs": {"SPY":"S&P 500","QQQ":"Nasdaq-100","SPUS":"S&P 500 Halal (SPUS)","HLAL":"Global Halal ETF"}
}

@st.cache_data(ttl=300)
def get_data(ticker, period="6mo"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={period}&interval=1d"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        d = r.json()["chart"]["result"][0]
        df = pd.DataFrame({"date": pd.to_datetime(d["timestamp"], unit="s"),
                           "close": d["indicators"]["quote"][0]["close"]}).dropna()
        return df
    except:
        return pd.DataFrame()

st.sidebar.title("Controls")
cat = st.sidebar.selectbox("Category", list(TICKERS.keys()))
sel = st.sidebar.multiselect("Tickers", list(TICKERS[cat].keys()), default=list(TICKERS[cat].keys())[:3])
period = st.sidebar.selectbox("Period", ["1mo","3mo","6mo","1y","2y"], index=2)
st.sidebar.info("SPUS and HLAL are Shariah-compliant ETFs (no alcohol, tobacco, interest-based finance, or weapons).")

if not sel: st.warning("Select at least one ticker."); st.stop()

data = {t: get_data(t, period) for t in sel}
data = {t: df for t,df in data.items() if not df.empty}
if not data: st.error("Could not fetch data."); st.stop()

# KPIs
cols = st.columns(len(data))
for i, (ticker, df) in enumerate(data.items()):
    price = df["close"].iloc[-1]
    change = ((price - df["close"].iloc[-2]) / df["close"].iloc[-2]) * 100 if len(df)>1 else 0
    cols[i].metric(f"{ticker} — {TICKERS[cat].get(ticker,'')}", f"${price:.2f}", f"{change:+.2f}% today")

st.markdown("---")
COLORS = ["#7c6cf2","#4ecdc4","#f7b731","#ff6b6b","#a8e6cf","#ffd3a5"]

# Chart 1 — indexed performance
st.subheader("Performance (indexed to 100 at start of period)")
fig = go.Figure()
for i,(t,df) in enumerate(data.items()):
    idx = (df["close"]/df["close"].iloc[0]*100).round(2)
    fig.add_trace(go.Scatter(x=df["date"], y=idx, name=t,
        line=dict(color=COLORS[i%len(COLORS)], width=2.5)))
fig.add_hline(y=100, line_dash="dot", line_color="rgba(255,255,255,0.2)")
fig.update_layout(plot_bgcolor="#1a1d2e", paper_bgcolor="#0f1117", font=dict(color="#e8e8f0"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Index"),
    legend=dict(orientation="h", y=-0.15), height=400, margin=dict(t=10,b=60))
st.plotly_chart(fig, use_container_width=True)

# Chart 2 — rolling volatility
st.subheader("Rolling 20-day Annualized Volatility (%)")
fig2 = go.Figure()
for i,(t,df) in enumerate(data.items()):
    vol = df["close"].pct_change().rolling(20).std() * (252**0.5) * 100
    fig2.add_trace(go.Scatter(x=df["date"], y=vol.round(2), name=t,
        line=dict(color=COLORS[i%len(COLORS)], width=2)))
fig2.update_layout(plot_bgcolor="#1a1d2e", paper_bgcolor="#0f1117", font=dict(color="#e8e8f0"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Volatility %"),
    legend=dict(orientation="h", y=-0.15), height=320, margin=dict(t=10,b=60))
st.plotly_chart(fig2, use_container_width=True)

# Summary table
st.subheader("Summary Statistics")
rows = []
for t,df in data.items():
    ret = df["close"].pct_change().dropna()
    rows.append({"Ticker":t,"Name":TICKERS[cat].get(t,""),
        "Current":f"${df['close'].iloc[-1]:.2f}",
        "Period Return":f"{((df['close'].iloc[-1]/df['close'].iloc[0])-1)*100:+.1f}%",
        "Avg Daily":f"{ret.mean()*100:+.3f}%",
        "Volatility":f"{ret.std()*(252**0.5)*100:.1f}%",
        "Max Drawdown":f"{((df['close']/df['close'].cummax())-1).min()*100:.1f}%"})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
