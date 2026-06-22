import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter

# ================= 1. 網頁與 CSS 配置 =================
st.set_page_config(page_title="台股動態觀測站", layout="wide")

# 注入 CSS 魔法：打造 App 卡片風格
st.markdown("""
<style>
    .summary-card {
        background-color: #f8f9fa;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #edf2f7;
    }
    .tag-pill {
        background-color: #e2e8f0;
        color: #4a5568;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 14px;
        margin-right: 8px;
        display: inline-block;
    }
    .grid-btn {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        font-weight: bold;
        color: #2d3748;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

if 'custom_themes' not in st.session_state:
    st.session_state['custom_themes'] = {}

# ================= 2. 核心資料庫 =================
BASE_STOCK_DB = {
    "AI伺服器": {"2330": "台積電", "2317": "鴻海", "2382": "廣達", "3231": "緯創", "2376": "技嘉", "6669": "緯穎"},
    "散熱管理": {"3017": "奇鋐", "3324": "雙鴻", "2421": "建準", "8996": "高力", "3483": "力致", "3653": "健策"},
    "電源與BBU": {"2308": "台達電", "2301": "光寶科", "6409": "旭隼", "6121": "新普", "6781": "AES-KY"},
    "CoWoS封裝": {"3131": "弘塑", "6187": "萬潤", "5443": "均豪", "6640": "均華", "3583": "辛耘", "6515": "穎崴"},
    "矽光子CPO": {"4979": "華星光", "3450": "聯鈞", "3081": "聯亞", "3363": "上詮", "6442": "光聖", "3163": "波若威"},
    "功率元件(新)": {"8255": "朋程", "3645": "達邁", "5425": "台半", "8261": "富鼎", "3317": "尼克森"} # 示範新增族群
}
STOCK_DB = {**BASE_STOCK_DB, **st.session_state['custom_themes']}
SYMBOL_TO_THEME = {sym: theme for theme, stocks in STOCK_DB.items() for sym in stocks}
LEADERS = ["2330", "2317", "3450", "4979", "3037", "2383", "3017", "2308", "2327", "2454", "3661"]

def get_tw_stock_name(symbol):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find('title').text
        return title.split('(')[0].strip() if title else f"自選_{symbol}"
    except: return f"自選_{symbol}"

# ================= 3. 資料抓取引擎 =================
@st.cache_data(ttl=1800)
def get_market_summary_and_tags():
    """抓取新聞，產生無連結的摘要與熱門標籤"""
    try:
        url_tw = "https://news.google.com/rss/search?q=台股+OR+半導體+OR+外資&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        res = requests.get(url_tw, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(res.text, 'xml')
        
        titles = [item.title.text.split(' - ')[0] for item in soup.find_all('item')[:8]]
        
        # 產生萃取式摘要 (組合前三條重大新聞)
        if titles:
            summary_text = "今日盤面焦點： " + "；".join(titles[:3]) + "。市場資金輪動快速，建議留意籌碼面變化與均線支撐。"
        else:
            summary_text = "目前市場無重大突發消息，呈現量縮整理格局。"
            
        # 擷取熱門關鍵字 (簡單的中文分詞模擬)
        all_text = "".join(titles)
        keywords = ["台積電", "AI", "外資", "散熱", "鴻海", "聯發科", "降息", "ETF", "營收", "法說會", "半導體"]
        found_tags = [kw for kw in keywords if kw in all_text]
        tags = found_tags[:4] if found_tags else ["盤整", "觀望"]
        
        return summary_text, tags
    except:
        return "無法取得即時新聞，請檢查網路連線。", ["連線異常"]

@st.cache_data(ttl=600)
def get_indices():
    # 換成更符合台股習慣的指數 (加權, 櫃買, 台指期模擬)
    indices_dict = {"加權指數": "^TWII", "櫃買指數": "^TWO", "費城半導體": "^SOX"}
    res = {}
    for name, symbol in indices_dict.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if len(hist) >= 2:
                close, prev = float(hist['Close'].iloc[-1]), float(hist['Close'].iloc[-2])
                res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
            else: res[name] = {"現價": 0, "漲跌幅": 0}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

@st.cache_data(ttl=300)
def fetch_single_stock(symbol):
    try:
        symbol = str(symbol).strip()
        tkr = f"{symbol}.TW"
        hist = yf.Ticker(tkr).history(period="6mo")
        if hist.empty:
            tkr = f"{symbol}.TWO"
            hist = yf.Ticker(tkr).history(period="6mo")
        if hist.empty or len(hist) < 20: return None, ""
        name = get_tw_stock_name(symbol)
        display_name = f"🎯 搜尋結果: {name} ({symbol})"
        hist['MA5'], hist['MA20'] = hist['Close'].rolling(5).mean(), hist['Close'].rolling(20).mean()
        return hist, display_name
    except: return None, ""

@st.cache_data(ttl=600)
def get_stock_data_v89(stock_dict):
    data_list, price_history_dict = [], {}
    if not stock_dict: return pd.DataFrame(data_list), price_history_dict

    tickers = [f"{s}.TW" for s in stock_dict.keys()] + [f"{s}.TWO" for s in stock_dict.keys()]
    try:
        batch = yf.download(tickers, period="6mo", group_by="ticker", progress=False, threads=True)
    except: return pd.DataFrame(), {}

    for symbol, name in stock_dict.items():
        try:
            hist = pd.DataFrame()
            for suffix in [".TW", ".TWO"]:
                tkr = f"{symbol}{suffix}"
                if tkr in batch.columns.get_level_values(0):
                    hist = batch[tkr].copy().dropna(subset=['Close', 'Volume', 'Open', 'High', 'Low'])
                    if not hist.empty: break
            if hist.empty: continue
            
            close, prev_close = float(hist['Close'].iloc[-1]), float(hist['Close'].iloc[-2])
            change_pct = ((close - prev_close) / prev_close) * 100
            
            hist['MA20'] = hist['Close'].rolling(20).mean()
            vol_today, vol_ma5 = float(hist['Volume'].iloc[-1]), hist['Volume'].rolling(5).mean().iloc[-1]
            
            obv = (np.sign(hist['Close'].diff()) * hist['Volume']).fillna(0).cumsum()
            obv_up = obv.iloc[-1] > obv.rolling(10).mean().iloc[-1]
            
            try:
                hist_poc = hist.tail(20).copy()
                bins = np.linspace(hist_poc['Low'].min(), hist_poc['High'].max(), 40)
                hist_poc['Price_Bin'] = pd.cut((hist_poc['High']+hist_poc['Low']+hist_poc['Close'])/3, bins=bins, include_lowest=True)
                poc_price = hist_poc.groupby('Price_Bin')['Volume'].sum().idxmax().mid
            except: poc_price = close

            action = "🟡 盤整觀望"
            if close < hist['MA20'].iloc[-1]: action = "🛑 破線防守"
            elif close > hist['MA20'].iloc[-1] and obv_up: action = "🚀 多頭排列"

            crown = "👑 " if symbol in LEADERS else ""
            display_name = f"{crown}{name} ({symbol})"
            data_list.append({
                "代號": symbol, "所屬題材": SYMBOL_TO_THEME.get(symbol, "📌 自選股"),
                "指標股": display_name, "漲跌幅(%)": round(change_pct, 2), "現價": round(close, 2), 
                "POC鐵板價": round(poc_price, 2), "波段策略": action,
                "籌碼動能": "🔥 爆量" if vol_today > vol_ma5 * 1.5 else "-"
            })
            price_history_dict[display_name] = hist.tail(90)
        except: pass
    return pd.DataFrame(data_list), price_history_dict

def plot_advanced_k_volume(hist_df, name):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    trade_dates = hist_df.index.strftime('%y/%m/%d')
    fig.add_trace(go.Candlestick(x=trade_dates, open=hist_df['Open'], high=hist_df['High'], low=hist_df['Low'], close=hist_df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=trade_dates, y=hist_df['MA20'], name='20MA', line=dict(color='#1E90FF', width=1.5)), row=1, col=1)
    colors = ['#ff4b4b' if r['Close'] >= r['Open'] else '#00cc96' for i, r in hist_df.iterrows()]
    fig.add_trace(go.Bar(x=trade_dates, y=hist_df['Volume'], name='成交量', marker_color=colors), row=2, col=1)
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, showlegend=False, margin=dict(t=30, b=10, r=10, l=10))
    fig.update_xaxes(type='category', nticks=10)
    return fig

def color_strategy(val):
    if "🚀" in str(val): return 'color: #ff4b4b; font-weight: bold;'
    if "🛑" in str(val): return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 4. UI 版面配置 (模擬截圖風格) =================
st.title("概覽")

with st.spinner("🚀 系統載入中..."):
    df_all, hist_all = get_stock_data_v89(STOCK_DB)

# --- 區塊 1：AI 市場摘要卡片 ---
summary_text, tags = get_market_summary_and_tags()
st.markdown(f"""
<div class="summary-card">
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <span style="background-color: #e0f2fe; color: #0369a1; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 12px; margin-right: 10px;">🤖 AI 市場摘要</span>
        <span style="color: #718096; font-size: 12px;">盤中整理</span>
    </div>
    <h4 style="margin-top: 0; color: #1a202c; font-size: 16px; line-height: 1.5;">{summary_text}</h4>
    <div style="margin-top: 15px;">
        {''.join([f'<span class="tag-pill">#{t}</span>' for t in tags])}
    </div>
</div>
""", unsafe_allow_html=True)

# --- 區塊 2：四大按鈕列 (純視覺排版) ---
st.markdown("##### 快速導覽")
col_b1, col_b2, col_b3, col_b4 = st.columns(4)
col_b1.markdown('<div class="grid-btn">🔥 族群熱力</div>', unsafe_allow_html=True)
col_b2.markdown('<div class="grid-btn">📈 均線選股</div>', unsafe_allow_html=True)
col_b3.markdown('<div class="grid-btn">🎯 籌碼突破</div>', unsafe_allow_html=True)
col_b4.markdown('<div class="grid-btn">💼 庫存健檢</div>', unsafe_allow_html=True)
st.write("") # 留白

# --- 區塊 3：三大指數區 ---
st.markdown("##### 大盤動態")
idx_data = get_indices()
col_i1, col_i2, col_i3 = st.columns(3)
cols_idx = [col_i1, col_i2, col_i3]
for i, (n, d) in enumerate(idx_data.items()):
    color = "#ff4b4b" if d['漲跌幅'] >= 0 else "#00cc96"
    arrow = "▲" if d['漲跌幅'] >= 0 else "▼"
    cols_idx[i].markdown(f"""
    <div class="metric-card">
        <div style="color: #718096; font-size: 14px;">{n}</div>
        <div style="font-size: 24px; font-weight: bold; color: #1a202c; margin: 5px 0;">{d['現價']:,}</div>
        <div style="color: {color}; font-size: 14px; font-weight: bold;">{arrow} {abs(d['漲跌幅'])}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 區塊 4：核心工具區 (使用 Tabs 來整合原本的功能) ---
tab_group, tab_scan, tab_chart = st.tabs(["🔥 族群熱力圖", "📈 技術面選股", "🔍 線型 X光機"])

with tab_group:
    if not df_all.empty:
        st.write("各族群平均漲跌幅 (資金流向)")
        group_df = df_all.groupby('所屬題材')['漲跌幅(%)'].mean().reset_index().sort_values("漲跌幅(%)", ascending=False)
        st.dataframe(group_df, use_container_width=True, hide_index=True)

with tab_scan:
    if not df_all.empty:
        filter_opt = st.radio("篩選條件", ["全部顯示", "🚀 多頭排列 (站上月線)"], horizontal=True)
        df_display = df_all.copy()
        if filter_opt == "🚀 多頭排列 (站上月線)": 
            df_display = df_display[df_display['波段策略'].str.contains("🚀")]
        st.dataframe(df_display[['所屬題材', '指標股', '漲跌幅(%)', '現價', 'POC鐵板價', '波段策略', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), use_container_width=True, hide_index=True)

with tab_chart:
    st.write("直接輸入代號，調閱完整技術指標與量能")
    search_sym = st.text_input("🎯 輸入全台任意代號 (如: 2330)", "")
    if search_sym:
        with st.spinner("分析中..."):
            s_hist, s_name = fetch_single_stock(search_sym)
            if s_hist is not None: st.plotly_chart(plot_advanced_k_volume(s_hist, s_name), use_container_width=True)
            else: st.error("找不到該代號")
