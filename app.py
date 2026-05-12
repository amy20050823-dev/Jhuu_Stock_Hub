import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
import time
import random

# ================= 1. 網頁配置 =================
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

if 'custom_themes' not in st.session_state:
    st.session_state['custom_themes'] = {}

# ================= 1.6 自動抓取中文股名 =================
def get_tw_stock_name(symbol):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find('title').text
        return title.split('(')[0].strip() if title else f"自選_{symbol}"
    except: return f"自選_{symbol}"

# ================= 3. 產業題材資料庫 =================
BASE_STOCK_DB = {
    "輝達GTC/AI伺服器": {"2330": "台積電", "2317": "鴻海", "2382": "廣達", "3231": "緯創", "2376": "技嘉", "6669": "緯穎", "3706": "神達", "2356": "英業達", "2422": "佳能"},
    "散熱管理/水冷": {"3017": "奇鋐", "3324": "雙鴻", "2421": "建準", "6230": "超眾", "8996": "高力", "3483": "力致", "3338": "泰碩", "3653": "健策"},
    "電源與BBU": {"2308": "台達電", "2301": "光寶科", "6409": "旭隼", "6121": "新普", "3211": "順達", "3323": "加百裕", "6781": "AES-KY", "2324": "仁寶"},
    "CoWoS/先進封裝": {"3131": "弘塑", "6187": "萬潤", "5443": "均豪", "6640": "均華", "6196": "帆宣", "3583": "辛耘", "2338": "光罩", "6515": "穎崴"},
    "特用化學與光阻材料": {"4770": "上品", "1773": "勝一", "4755": "三福化", "1727": "中華化", "4763": "材料-KY", "1717": "長興", "5434": "崇越", "3010": "華立"},
    "傳統與面板級封測": {"3711": "日月光投控", "2449": "京元電子", "6257": "矽格", "3481": "群創", "8064": "東捷", "3580": "友威科"},
    "半導體前端設備": {"3413": "京鼎", "3680": "家登", "8091": "翔名", "3055": "蔚華科"},
    "廠務工程與無塵室": {"2404": "漢唐", "3402": "漢科", "6139": "亞翔", "5536": "聖暉*", "2493": "揚博", "6117": "迎廣"},
    "ASIC/IP矽智財": {"3443": "智原", "3661": "世芯-KY", "6643": "M31", "6533": "晶心科", "3529": "力旺", "3228": "金麗科", "6531": "愛普*"},
    "ABF載板/先進基板": {"3037": "欣興", "8046": "南電", "3189": "景碩", "8050": "廣積"},
    "CPO/矽光子": {"4979": "華星光", "3450": "聯鈞", "3081": "聯亞", "3363": "上詮", "6442": "光聖", "6451": "訊芯-KY", "3163": "波若威", "4908": "前鼎", "3234": "光環"},
    "網通/石英元件": {"3042": "晶技", "3221": "台嘉碩", "8182": "加高", "2484": "希華", "3596": "智易", "5388": "中磊", "3380": "明泰", "6285": "啟碁"},
    "低軌衛星": {"2313": "華通", "3491": "昇達科", "6271": "同欣電", "3466": "致振", "3152": "璟德", "2485": "兆赫"},
    "AI機器人/自動化": {"2359": "所羅門", "2365": "昆盈", "6414": "樺漢", "8374": "羅昇", "4510": "高鋒", "1590": "亞德客-KY", "2049": "上銀", "4545": "銘鈺"},
    "AI PC/工業電腦": {"2357": "華碩", "2353": "宏碁", "2395": "研華", "6245": "立端", "8114": "振樺電", "6206": "飛捷"}
}

STOCK_DB = {**BASE_STOCK_DB, **st.session_state['custom_themes']}
SYMBOL_TO_THEME = {sym: theme for theme, stocks in STOCK_DB.items() for sym in stocks}
LEADERS = ["2330", "2317", "3450", "4979", "3037", "2383", "3017", "2308", "2327", "2454", "3661", "1519", "2603"]

# ================= 4. 核心抓取 =================
@st.cache_data(ttl=1800)
def get_market_news():
    news = []
    try:
        url_tw = "https://news.google.com/rss/search?q=台股+OR+股市&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        res = requests.get(url_tw, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(res.text, 'xml')
        for item in soup.find_all('item')[:12]:
            news.append({"title": item.title.text.split(' - ')[0], "link": item.link.text})
    except: pass
    return news

@st.cache_data(ttl=600)
def get_indices():
    indices_dict = {"加權指數": "^TWII", "那斯達克": "^IXIC", "費半指數": "^SOX", "美光(MU)": "MU", "三星(韓國)": "005930.KS", "WTI原油": "CL=F"}
    res = {}
    for name, symbol in indices_dict.items():
        try:
            hist = yf.Ticker(symbol).history(period="1mo")
            if not hist.empty:
                close, prev = float(hist['Close'].iloc[-1]), float(hist['Close'].iloc[-2])
                res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
            else: res[name] = {"現價": 0, "漲跌幅": 0}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

@st.cache_data(ttl=600)
def get_stock_advanced_data(stock_dict):
    data_list = []
    if not stock_dict: return pd.DataFrame(data_list)

    tickers = [f"{s}.TW" for s in stock_dict.keys()] + [f"{s}.TWO" for s in stock_dict.keys()]
    try:
        # 💡 使用最穩定的批次下載
        batch = yf.download(tickers, period="6mo", group_by="ticker", progress=False, threads=True)
    except: return pd.DataFrame()

    for symbol, name in stock_dict.items():
        try:
            hist = pd.DataFrame()
            for suffix in [".TW", ".TWO"]:
                tkr = f"{symbol}{suffix}"
                if tkr in batch.columns.get_level_values(0):
                    hist = batch[tkr].copy().dropna(subset=['Close'])
                    if not hist.empty: break
            
            if hist.empty: continue
            
            close, prev_close = float(hist['Close'].iloc[-1]), float(hist['Close'].iloc[-2])
            change_pct = ((close - prev_close) / prev_close) * 100
            
            ma20, ma60 = hist['Close'].rolling(20).mean(), hist['Close'].rolling(60).mean()
            vol_today, vol_ma5 = float(hist['Volume'].iloc[-1]), hist['Volume'].rolling(5).mean().iloc[-1]
            bb_width = (4 * hist['Close'].rolling(20).std()) / ma20
            
            rsv = (hist['Close'] - hist['Low'].rolling(9).min()) / (hist['High'].rolling(9).max() - hist['Low'].rolling(9).min()) * 100
            k_s = rsv.ewm(com=2).mean()
            dif = hist['Close'].ewm(span=12).mean() - hist['Close'].ewm(span=26).mean()
            osc = dif - dif.ewm(span=9).mean()
            obv = (np.sign(hist['Close'].diff()) * hist['Volume']).fillna(0).cumsum()
            
            obv_up = obv.iloc[-1] > obv.rolling(10).mean().iloc[-1]
            obv_high = obv.iloc[-1] >= obv.rolling(20).max().iloc[-1] * 0.95
            res_20 = hist['High'].rolling(20).max().shift(1).iloc[-1]
            
            # ====== 黃金推薦序權重 ======
            action, prio = "🟡 盤整 0軸下 無動能", 4
            if close < ma20.iloc[-1]: action, prio = "🛑 破線停損 (籌碼流出)", 8
            elif (k_s.iloc[-1] > k_s.iloc[-2] or osc.iloc[-1] > osc.iloc[-2]) and obv_up and obv_high and (close > res_20 or (res_20-close)/close > 0.05):
                action, prio = "🚀 可進場，kd obv上 無壓力(或突破)", 1
            elif close > ma20.iloc[-1] and close > ma60.iloc[-1]: action, prio = "🟢 多頭續抱", 3

            crown = "👑 " if symbol in LEADERS else ""
            data_list.append({
                "資料日期": hist.index[-1].strftime('%m/%d'), "代號": symbol, "所屬題材": SYMBOL_TO_THEME.get(symbol, "📌 自選股"),
                "指標股": f"{crown}{name} ({symbol})", "漲跌幅(%)": round(change_pct, 2), "現價": round(close, 2),
                "波段策略": action, "策略權重": prio, "黑馬潛力": "🐎 爆發準備" if (close > ma20.iloc[-1] and bb_width.iloc[-1] < 0.15 and obv_up) else "-",
                "籌碼動能": "爆量流入" if vol_today > vol_ma5 * 1.5 else "量能平穩"
            })
        except: pass
    return pd.DataFrame(data_list)

def color_strategy(val):
    if any(x in str(val) for x in ["🚀", "💎", "🟢"]): return 'color: #ff4b4b; font-weight: bold;'
    if any(x in str(val) for x in ["🛑", "⚠️", "🔥"]): return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 5. UI 介面 =================
st.title("台股題材動態觀測站")

# 側邊欄 1：手動增股
st.sidebar.header("🛠️ 新增自定義題材")
c_theme = st.sidebar.text_input("題材名稱", "")
c_stocks = st.sidebar.text_input("代號 (例: 2485, 3324)", "")
if st.sidebar.button("加入題材庫"):
    if c_theme and c_stocks:
        curr = st.session_state['custom_themes'].get(c_theme, {})
        for s in c_stocks.split(','):
            s = s.strip()
            if s: curr[s] = get_tw_stock_name(s)
        st.session_state['custom_themes'][c_theme] = curr
        st.sidebar.success("更新成功！")

st.sidebar.markdown("---")

# 側邊欄 2：持股健檢
st.sidebar.header("💼 我的持股健檢")
my_input = st.sidebar.text_input("代號 (如: 2301, 5388)", "")
my_holdings = {}
if my_input:
    for s in my_input.split(','):
        s = s.strip()
        if s: my_holdings[s] = get_tw_stock_name(s)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 強制刷新資料"):
    st.cache_data.clear()
    st.rerun()

# 合併清單並抓取
all_flat = {**{sym: name for t in STOCK_DB.values() for sym, name in t.items()}, **my_holdings}
with st.spinner("🚀 正在極速掃描技術面指標..."):
    df_all = get_stock_advanced_data(all_flat)

tab1, tab2, tab3 = st.tabs(["📊 首頁：大盤熱度", "🔍 細部題材：技術面", "🎯 波段選股 & 黑馬"])

with tab1:
    idx_data = get_indices()
    cols = st.columns(len(idx_data))
    for i, (n, d) in enumerate(idx_data.items()): cols[i].metric(n, d["現價"], f"{d['漲跌幅']}%")
    st.markdown("---")
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        st.subheader("今日族群熱門排行")
        if not df_all.empty:
            st.dataframe(df_all.groupby('所屬題材')['漲跌幅(%)'].mean().reset_index().sort_values("漲跌幅(%)", ascending=False), height=400, use_container_width=True, hide_index=True)
    with col_r:
        st.subheader("題材偵察機 (盤面新聞)")
        for n in get_market_news(): st.markdown(f"🔗 [{n['title']}]({n['link']})")

with tab2:
    sel_theme = st.selectbox("選擇族群", list(STOCK_DB.keys()))
    if not df_all.empty:
        df_f = df_all[df_all['所屬題材'] == sel_theme].sort_values("策略權重")
        st.dataframe(df_f[['資料日期', '指標股', '漲跌幅(%)', '現價', '波段策略', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), use_container_width=True)

with tab3:
    if not df_all.empty:
        if my_holdings:
            st.markdown("### 💼 我的持股健檢")
            st.dataframe(df_all[df_all['代號'].isin(my_holdings.keys())].sort_values("策略權重"), use_container_width=True)
        
        st.markdown("### 🐎 今日潛在爆發黑馬")
        df_h = df_all[df_all['黑馬潛力'] != "-"].sort_values("策略權重")
        st.dataframe(df_h if not df_h.empty else pd.DataFrame(), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🎯 全市場波段選股總表 (黃金排序)")
        st.dataframe(df_all.sort_values("策略權重")[['資料日期', '所屬題材', '指標股', '漲跌幅(%)', '現價', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), height=600, use_container_width=True)
