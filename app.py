# ========= IMPORT =========
import streamlit as st
import yfinance as yf
import pandas_ta as ta
import os
import sqlite3
import datetime as dt
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
DB_FILE = "coinclerk.db"

# ========= SQLITE =========
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS signals(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 ticker TEXT,
                 price REAL,
                 rsi REAL,
                 macd REAL,
                 signal TEXT,
                 created_at TEXT
              );"""
        )
        conn.commit()
init_db()

# ========= CONFIG =========
st.set_page_config(layout="centered", page_title="CoinClerk")
st.title("📊 CoinClerk – Tín hiệu MUA/BÁN")

# ========= SIDEBAR =========
with st.sidebar:
    st.header("⚙️ Settings")

    input_method = st.radio("Input method:", ["Quick pick (commodities)", "Other / Manual"])

    if input_method == "Quick pick (commodities)":
        commo_dict = {
            "Silver": "SI=F",
            "Gold": "GC=F",
            "WTI Crude Oil": "CL=F",
            "Copper": "HG=F",
            "Platinum": "PL=F",
            "Natural Gas": "NG=F",
            "Soybean": "ZS=F",
            "Corn": "ZC=F",
            "Wheat": "ZW=F",
        }
        ticker = st.selectbox("Commodity:", list(commo_dict.values()),
                              format_func=lambda x: [k for k, v in commo_dict.items() if v == x][0])
    else:
        ticker = st.text_input("Ticker (Yahoo format):", "AAPL").upper()

    interval = st.selectbox("Timeframe:", ["1d", "1h", "1wk"])
    period = st.selectbox("Period:", ["1mo", "3mo", "6mo"])

# ========= DATA =========
df = yf.download(ticker, period=period, interval=interval, progress=False)
if df.empty:
    st.error("Không tải được dữ liệu – kiểm tra mã hoặc khoảng thời gian.")
    st.stop()
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# ========= INDICATORS =========
df["RSI"] = ta.rsi(df.Close)
macd = ta.macd(df.Close)
if macd is not None:
    df = df.join(macd)

last = df.iloc[-1]

def safe_float(col, default=0.0):
    val = col.item() if hasattr(col, 'item') else col
    return float(val) if val is not None and pd.notna(val) else default

rsi_val   = safe_float(last["RSI"], 50.0)
macd_main = safe_float(last.get("MACD_12_26_9"), 0.0)
macd_sig  = safe_float(last.get("MACDs_12_26_9"), 0.0)

# ========= SIGNAL (TIẾNG VIỆT) =========
if rsi_val < 30 and macd_main > macd_sig:
    signal_txt = "MUA"
    st.success("💚 Tín hiệu: MUA")
elif rsi_val > 70 and macd_main < macd_sig:
    signal_txt = "BÁN"
    st.error("❤️ Tín hiệu: BÁN")
else:
    signal_txt = "GIỮ"
    st.info("💛 Tín hiệu: GIỮ")

st.line_chart(df[["Close", "RSI"]])

# ========= SQLITE =========
with sqlite3.connect(DB_FILE) as conn:
    conn.execute(
        "INSERT INTO signals(ticker, price, rsi, macd, signal, created_at) VALUES (?,?,?,?,?,?)",
        (ticker, float(last.Close), rsi_val, macd_main, signal_txt,
         dt.datetime.now().isoformat())
    )
    conn.commit()

# ========= HISTORY =========
st.subheader("📜 Lịch sử khuyến nghị")
df_hist = pd.read_sql(
    "SELECT * FROM signals WHERE ticker=? ORDER BY created_at DESC LIMIT 50",
    sqlite3.connect(DB_FILE),
    params=(ticker,)
)
if not df_hist.empty:
    if "created_at" in df_hist.columns:
        df_hist["created_at"] = pd.to_datetime(
            df_hist["created_at"], errors="coerce"
        ).dt.strftime("%d/%m/%Y %H:%M")
    st.dataframe(df_hist)
else:
    st.info("Chưa có lịch sử cho mã này.")
