import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup

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

# 💡 V76 新增：提前在表格計算 POC
@st.cache_data(ttl=600)
def get_stock_data_v76(stock_dict):
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
            
            hist['MA5'], hist['MA20'], hist['MA60'] = hist['Close'].rolling(5).mean(), hist['Close'].rolling(20).mean(), hist['Close'].rolling(60).mean()
            vol_today, vol_ma5 = float(hist['Volume'].iloc[-1]), hist['Volume'].rolling(5).mean().iloc[-1]
            bb_width = (4 * hist['Close'].rolling(20).std()) / hist['MA20']
            
            rsv = (hist['Close'] - hist['Low'].rolling(9).min()) / (hist['High'].rolling(9).max() - hist['Low'].rolling(9).min()) * 100
            k_s = rsv.ewm(com=2).mean()
            dif = hist['Close'].ewm(span=12).mean() - hist['Close'].ewm(span=26).mean()
            osc = dif - dif.ewm(span=9).mean()
            obv = (np.sign(hist['Close'].diff()) * hist['Volume']).fillna(0).cumsum()
            
            obv_up = obv.iloc[-1] > obv.rolling(10).mean().iloc[-1]
            obv_high = obv.iloc[-1] >= obv.rolling(20).max().iloc[-1] * 0.95
            res_20 = hist['High'].rolling(20).max().shift(1).iloc[-1]
            
            # 💡 計算 POC (抓出過去 90 天最密集的價位)
            try:
                hist_90 = hist.tail(90).copy()
                min_p, max_p = hist_90['Low'].min(), hist_90['High'].max()
                if min_p < max_p:
                    bins = np.linspace(min_p, max_p, 30)
                    hist_90['Price_Bin'] = pd.cut(hist_90['Close'], bins=bins, include_lowest=True)
                    # 避免舊版 pandas 報錯，不加 observed=False
                    poc_price = hist_90.groupby('Price_Bin')['Volume'].sum().idxmax().mid
                else:
                    poc_price = close
            except:
                poc_price = close

            action, prio = "🟡 盤整 0軸下 無動能", 4
            if close < hist['MA20'].iloc[-1]: action, prio = "🛑 破線停損 (籌碼流出)", 8
            elif (k_s.iloc[-1] > k_s.iloc[-2] or osc.iloc[-1] > osc.iloc[-2]) and obv_up and obv_high and (close > res_20 or (res_20-close)/close > 0.05):
                action, prio = "🚀 可進場，kd obv上 無壓力(或突破)", 1
            elif close > hist['MA20'].iloc[-1] and close > hist['MA60'].iloc[-1]: action, prio = "🟢 多頭續抱", 3

            crown = "👑 " if symbol in LEADERS else ""
            display_name = f"{crown}{name} ({symbol})"
            data_list.append({
                "資料日期": hist.index[-1].strftime('%m/%d'), "代號": symbol, "所屬題材": SYMBOL_TO_THEME.get(symbol, "📌 自選股"),
                "指標股": display_name, "漲跌幅(%)": round(change_pct, 2), "現價": round(close, 2), 
                "POC價位": round(poc_price, 2),  # 💡 成功加入新欄位
                "波段策略": action, "策略權重": prio, "黑馬潛力": "🐎 爆發準備" if (close > hist['MA20'].iloc[-1] and bb_width.iloc[-1] < 0.15 and obv_up) else "-",
                "籌碼動能": "爆量流入" if vol_today > vol_ma5 * 1.5 else "量能平穩"
            })
            
            price_history_dict[display_name] = hist.tail(90)
        except: pass
    return pd.DataFrame(data_list), price_history_dict

def plot_advanced_k_volume(hist_df, name):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.15, 0.2])
    
    # 計算 POC
    try:
        min_p, max_p = hist_df['Low'].min(), hist_df['High'].max()
        bins = np.linspace(min_p, max_p, 30)
        hist_df['Price_Bin'] = pd.cut(hist_df['Close'], bins=bins, include_lowest=True)
        poc_price = hist_df.groupby('Price_Bin')['Volume'].sum().idxmax().mid
    except: poc_price = hist_df['Close'].iloc[-1]

    # K線與均線
    fig.add_trace(go.Candlestick(x=hist_df.index, open=hist_df['Open'], high=hist_df['High'], low=hist_df['Low'], close=hist_df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA5'], name='5MA', line=dict(color='#FFA500', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA20'], name='20MA', line=dict(color='#1E90FF', width=1.5)), row=1, col=1)
    
    fig.add_hline(y=poc_price, line_dash="dash", line_color="#ff4b4b", line_width=2, 
                 annotation_text=f"POC 密集區: {poc_price:.2f}", annotation_position="top left", 
                 annotation_font_color="#ff4b4b", row=1, col=1)
    
    # 成交量
    colors = ['#ff4b4b' if r['Close'] >= r['Open'] else '#00cc96' for i, r in hist_df.iterrows()]
    fig.add_trace(go.Bar(x=hist_df.index, y=hist_df['Volume'], name='成交量', marker_color=colors), row=2, col=1)
    
    # MACD
    exp1 = hist_df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = hist_df['Close'].ewm(span=26, adjust=False).mean()
    dif = exp1 - exp2
    macd = dif.ewm(span=9, adjust=False).mean()
    osc = dif - macd
    osc_colors = ['#ff4b4b' if val >= 0 else '#00cc96' for val in osc]
    fig.add_trace(go.Bar(x=hist_df.index, y=osc, name='MACD柱', marker_color=osc_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=dif, name='DIF', line=dict(color='#1E90FF', width=1)), row=3, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=macd, name='MACD線', line=dict(color='#FFA500', width=1)), row=3, col=1)

    # OBV 籌碼
    obv = (np.sign(hist_df['Close'].diff()) * hist_df['Volume']).fillna(0).cumsum()
    obv_ma10 = obv.rolling(10).mean()
    fig.add_trace(go.Scatter(x=hist_df.index, y=obv, name='OBV主力線', line=dict(color='#9932CC', width=2)), row=4, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=obv_ma10, name='OBV均線', line=dict(color='#ccc', width=1, dash='dot')), row=4, col=1)

    # 💡 在圖表標題加上 POC，防走失
    fig.update_layout(height=750, xaxis_rangeslider_visible=False, showlegend=False, margin=dict(t=40, b=10),
                      title=dict(text=f"{name} 動能與籌碼分析 (POC鐵板價: {poc_price:.2f})", font=dict(size=16)))
    return fig

def color_strategy(val):
    if any(x in str(val) for x in ["🚀", "💎", "🟢"]): return 'color: #ff4b4b; font-weight: bold;'
    if any(x in str(val) for x in ["🛑", "⚠️", "🔥"]): return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 5. UI 介面 =================
st.title("台股題材動態觀測站 V76 POC解碼版")

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

all_flat = {**{sym: name for t in STOCK_DB.values() for sym, name in t.items()}, **my_holdings}
with st.spinner("🚀 正在極速掃描技術面指標與計算 POC 鐵板價..."):
    df_all, hist_all = get_stock_data_v76(all_flat)

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
        df_f = df_all[df_all['所屬題材'] == sel_theme].sort_values("策略權重").drop(columns=['策略權重'])
        # 💡 將 POC價位 放入顯示欄位中
        st.dataframe(df_f[['資料日期', '指標股', '漲跌幅(%)', '現價', 'POC價位', '波段策略', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), use_container_width=True)
        
        st.markdown("---")
        target = st.selectbox("查看詳細技術線型", df_f['指標股'].tolist(), key="t2")
        if target in hist_all: st.plotly_chart(plot_advanced_k_volume(hist_all[target], target), use_container_width=True)

with tab3:
    if not df_all.empty:
        if my_holdings:
            st.markdown("### 💼 我的持股健檢")
            df_my = df_all[df_all['代號'].isin(my_holdings.keys())].sort_values("策略權重").drop(columns=['策略權重'])
            st.dataframe(df_my[['指標股', '漲跌幅(%)', '現價', 'POC價位', '波段策略', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), use_container_width=True)
        
        st.markdown("### 🐎 今日潛在爆發黑馬")
        df_h = df_all[df_all['黑馬潛力'] != "-"].sort_values("策略權重").drop(columns=['策略權重'])
        st.dataframe(df_h[['所屬題材', '指標股', '漲跌幅(%)', '現價', 'POC價位', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略', '黑馬潛力']) if not df_h.empty else pd.DataFrame(), use_container_width=True)
        
        st.markdown("---")
        
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            st.markdown("### 🎯 全市場波段選股總表")
        with col_f2:
            filter_opt = st.radio("⚡ 一鍵快速篩選", ["全部顯示", "🚀 只看進場", "🟢 只看多頭", "🛑 只看停損"], horizontal=True)
        
        df_display = df_all.sort_values("策略權重").drop(columns=['策略權重'])
        
        if filter_opt == "🚀 只看進場": df_display = df_display[df_display['波段策略'].str.contains("🚀")]
        elif filter_opt == "🟢 只看多頭": df_display = df_display[df_display['波段策略'].str.contains("🟢")]
        elif filter_opt == "🛑 只看停損": df_display = df_display[df_display['波段策略'].str.contains("🛑")]
            
        st.dataframe(df_display[['資料日期', '所屬題材', '指標股', '漲跌幅(%)', '現價', 'POC價位', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), height=600, use_container_width=True)
        
        st.markdown("---")
        target_a = st.selectbox("查看全市場詳細技術線型", df_display['指標股'].tolist(), key="t3")
        if target_a in hist_all: st.plotly_chart(plot_advanced_k_volume(hist_all[target_a], target_a), use_container_width=True)
