import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
import io
import pdfplumber

# ================= 1. 網頁配置 =================
st.set_page_config(page_title="台股題材觀測", layout="wide")

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

# ================= 3. 產業題材與 ETF 資料庫 =================
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

# 💡 V87：滿血回歸的 9 檔 ETF 完整十檔成分股資料庫
ETF_DB = {
    "0050 (元大台灣50)": {
        "2330": {"name": "台積電", "weight": 52.5, "theme": "半導體"}, "2317": {"name": "鴻海", "weight": 8.2, "theme": "AI伺服器"},
        "2454": {"name": "聯發科", "weight": 4.5, "theme": "IC設計"}, "2382": {"name": "廣達", "weight": 2.5, "theme": "AI伺服器"},
        "2308": {"name": "台達電", "weight": 2.2, "theme": "電源與BBU"}, "2303": {"name": "聯電", "weight": 1.8, "theme": "半導體"},
        "2881": {"name": "富邦金", "weight": 1.5, "theme": "金融"}, "2882": {"name": "國泰金", "weight": 1.4, "theme": "金融"},
        "3711": {"name": "日月光", "weight": 1.3, "theme": "封測"}, "2891": {"name": "中信金", "weight": 1.2, "theme": "金融"}
    },
    "0056 (元大高股息)": {
        "3034": {"name": "聯詠", "weight": 4.2, "theme": "IC設計"}, "2603": {"name": "長榮", "weight": 4.1, "theme": "航運"},
        "2454": {"name": "聯發科", "weight": 3.8, "theme": "IC設計"}, "3044": {"name": "健鼎", "weight": 3.5, "theme": "PCB"},
        "2345": {"name": "智邦", "weight": 3.2, "theme": "網通"}, "2379": {"name": "瑞昱", "weight": 3.0, "theme": "IC設計"},
        "3008": {"name": "大立光", "weight": 2.8, "theme": "光學"}, "2317": {"name": "鴻海", "weight": 2.5, "theme": "AI伺服器"},
        "2330": {"name": "台積電", "weight": 2.0, "theme": "半導體"}, "3231": {"name": "緯創", "weight": 1.8, "theme": "AI PC"}
    },
    "00878 (國泰永續高股息)": {
        "2454": {"name": "聯發科", "weight": 4.5, "theme": "IC設計"}, "3034": {"name": "聯詠", "weight": 4.2, "theme": "IC設計"},
        "2474": {"name": "可成", "weight": 3.8, "theme": "機殼"}, "2357": {"name": "華碩", "weight": 3.6, "theme": "AI PC"},
        "2382": {"name": "廣達", "weight": 3.5, "theme": "AI伺服器"}, "2377": {"name": "微星", "weight": 3.2, "theme": "AI PC"},
        "2376": {"name": "技嘉", "weight": 3.0, "theme": "AI伺服器"}, "2324": {"name": "仁寶", "weight": 2.8, "theme": "AI PC"},
        "3702": {"name": "大聯大", "weight": 2.5, "theme": "通路"}, "4904": {"name": "遠傳", "weight": 2.2, "theme": "電信"}
    },
    "00919 (群益台灣精選高息)": {
        "2603": {"name": "長榮", "weight": 11.2, "theme": "航運"}, "2303": {"name": "聯電", "weight": 6.5, "theme": "半導體"},
        "3034": {"name": "聯詠", "weight": 6.2, "theme": "IC設計"}, "2454": {"name": "聯發科", "weight": 5.8, "theme": "IC設計"},
        "2891": {"name": "中信金", "weight": 4.8, "theme": "金融"}, "6121": {"name": "新普", "weight": 4.2, "theme": "電源與BBU"},
        "3293": {"name": "鈊象", "weight": 3.8, "theme": "遊戲"}, "6239": {"name": "力成", "weight": 3.5, "theme": "封測"},
        "2404": {"name": "漢唐", "weight": 3.2, "theme": "無塵室"}, "8112": {"name": "至上", "weight": 3.0, "theme": "通路"}
    },
    "00981A (統一台股增長主動式)": {
        "2330": {"name": "台積電", "weight": 8.9, "theme": "半導體"}, "2383": {"name": "台光電", "weight": 5.2, "theme": "PCB"},
        "2327": {"name": "國巨", "weight": 4.2, "theme": "被動元件"}, "3711": {"name": "日月光投控", "weight": 3.0, "theme": "封測"},
        "2303": {"name": "聯電", "weight": 2.7, "theme": "半導體"}, "5274": {"name": "信驊", "weight": 2.7, "theme": "IC設計"},
        "3017": {"name": "奇鋐", "weight": 2.5, "theme": "散熱"}, "2345": {"name": "智邦", "weight": 2.3, "theme": "網通"},
        "2308": {"name": "台達電", "weight": 2.0, "theme": "電源與BBU"}, "6515": {"name": "穎崴", "weight": 1.4, "theme": "半導體設備"}
    },
    "00980A (野村臺灣智慧優選主動式)": {
        "2330": {"name": "台積電", "weight": 9.5, "theme": "半導體"}, "2317": {"name": "鴻海", "weight": 5.8, "theme": "AI伺服器"},
        "2454": {"name": "聯發科", "weight": 4.5, "theme": "IC設計"}, "2382": {"name": "廣達", "weight": 4.2, "theme": "AI伺服器"},
        "3231": {"name": "緯創", "weight": 3.8, "theme": "AI PC"}, "2383": {"name": "台光電", "weight": 3.5, "theme": "PCB"},
        "3017": {"name": "奇鋐", "weight": 3.2, "theme": "散熱"}, "2308": {"name": "台達電", "weight": 2.8, "theme": "電源與BBU"},
        "3711": {"name": "日月光投控", "weight": 2.5, "theme": "封測"}, "2345": {"name": "智邦", "weight": 2.2, "theme": "網通"}
    },
    "00403A (統一台股升級50主動式)": {
        "2330": {"name": "台積電", "weight": 28.5, "theme": "半導體"}, "2317": {"name": "鴻海", "weight": 7.2, "theme": "AI伺服器"},
        "2454": {"name": "聯發科", "weight": 5.5, "theme": "IC設計"}, "2382": {"name": "廣達", "weight": 4.1, "theme": "AI伺服器"},
        "3231": {"name": "緯創", "weight": 3.8, "theme": "AI PC"}, "2308": {"name": "台達電", "weight": 3.2, "theme": "電源與BBU"},
        "3017": {"name": "奇鋐", "weight": 2.8, "theme": "散熱"}, "2383": {"name": "台光電", "weight": 2.5, "theme": "PCB"},
        "3711": {"name": "日月光投控", "weight": 2.2, "theme": "封測"}, "2345": {"name": "智邦", "weight": 1.9, "theme": "網通"}
    },
    "00990A (元大AI新經濟主動式)": {
        "2330": {"name": "台積電", "weight": 9.8, "theme": "半導體"}, "2382": {"name": "廣達", "weight": 6.5, "theme": "AI伺服器"},
        "2317": {"name": "鴻海", "weight": 5.2, "theme": "AI伺服器"}, "3231": {"name": "緯創", "weight": 4.8, "theme": "AI PC"},
        "3017": {"name": "奇鋐", "weight": 4.2, "theme": "散熱"}, "3324": {"name": "雙鴻", "weight": 3.8, "theme": "散熱"},
        "2376": {"name": "技嘉", "weight": 3.5, "theme": "AI伺服器"}, "6669": {"name": "緯穎", "weight": 3.1, "theme": "AI伺服器"},
        "2383": {"name": "台光電", "weight": 2.9, "theme": "PCB"}, "8210": {"name": "勤誠", "weight": 2.5, "theme": "機殼"}
    },
    "00984A (安聯台灣高息主動式)": {
        "2603": {"name": "長榮", "weight": 8.5, "theme": "航運"}, "3034": {"name": "聯詠", "weight": 6.2, "theme": "IC設計"},
        "2891": {"name": "中信金", "weight": 5.8, "theme": "金融"}, "2303": {"name": "聯電", "weight": 5.1, "theme": "半導體"},
        "2454": {"name": "聯發科", "weight": 4.5, "theme": "IC設計"}, "3293": {"name": "鈊象", "weight": 4.2, "theme": "遊戲"},
        "6121": {"name": "新普", "weight": 3.8, "theme": "電源與BBU"}, "2886": {"name": "兆豐金", "weight": 3.5, "theme": "金融"},
        "2404": {"name": "漢唐", "weight": 3.2, "theme": "無塵室"}, "6239": {"name": "力成", "weight": 3.0, "theme": "封測"}
    }
}

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
        hist['MA5'] = hist['Close'].rolling(5).mean()
        hist['MA20'] = hist['Close'].rolling(20).mean()
        return hist, display_name
    except: return None, ""

# 💡 回歸的 ETF 市場量能數據抓取
@st.cache_data(ttl=300)
def get_etf_market_data(etf_name):
    try:
        symbol = etf_name.split(" ")[0].strip()
        tkr = f"{symbol}.TW"
        hist = yf.Ticker(tkr).history(period="5d")
        if hist.empty:
            tkr = f"{symbol}.TWO"
            hist = yf.Ticker(tkr).history(period="5d")
        
        if len(hist) >= 2:
            vol_today = int(hist['Volume'].iloc[-1])
            vol_yest = int(hist['Volume'].iloc[-2])
            price = round(hist['Close'].iloc[-1], 2)
            price_yest = round(hist['Close'].iloc[-2], 2)
            change_pct = round(((price - price_yest) / price_yest) * 100, 2)
            return vol_today, vol_yest, price, change_pct
    except: pass
    return 0, 0, 0, 0

@st.cache_data(ttl=600)
def get_stock_data_v87(stock_dict):
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
            
            try:
                hist_poc = hist.tail(20).copy()
                min_p, max_p = hist_poc['Low'].min(), hist_poc['High'].max()
                if min_p < max_p:
                    bins = np.linspace(min_p, max_p, 40) 
                    typical_price = (hist_poc['High'] + hist_poc['Low'] + hist_poc['Close']) / 3
                    hist_poc['Price_Bin'] = pd.cut(typical_price, bins=bins, include_lowest=True)
                    poc_price = hist_poc.groupby('Price_Bin')['Volume'].sum().idxmax().mid
                else: poc_price = close
            except: poc_price = close

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
                "POC價位(月)": round(poc_price, 2),
                "波段策略": action, "策略權重": prio, "黑馬潛力": "🐎 爆發準備" if (close > hist['MA20'].iloc[-1] and bb_width.iloc[-1] < 0.15 and obv_up) else "-",
                "籌碼動能": "爆量流入" if vol_today > vol_ma5 * 1.5 else "量能平穩"
            })
            
            price_history_dict[display_name] = hist.tail(90)
        except: pass
    return pd.DataFrame(data_list), price_history_dict

def plot_advanced_k_volume(hist_df, name):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.15, 0.2])
    trade_dates = hist_df.index.strftime('%y/%m/%d')
    last_idx = trade_dates[-1]

    try:
        hist_poc = hist_df.tail(20).copy()
        min_p, max_p = hist_poc['Low'].min(), hist_poc['High'].max()
        bins = np.linspace(min_p, max_p, 40)
        typical_price = (hist_poc['High'] + hist_poc['Low'] + hist_poc['Close']) / 3
        hist_poc['Price_Bin'] = pd.cut(typical_price, bins=bins, include_lowest=True)
        poc_price = hist_poc.groupby('Price_Bin')['Volume'].sum().idxmax().mid
    except: poc_price = hist_df['Close'].iloc[-1]

    fig.add_trace(go.Candlestick(x=trade_dates, open=hist_df['Open'], high=hist_df['High'], low=hist_df['Low'], close=hist_df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=trade_dates, y=hist_df['MA5'], name='5MA', line=dict(color='#FFA500', width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=trade_dates, y=hist_df['MA20'], name='20MA', line=dict(color='#1E90FF', width=1.8)), row=1, col=1)
    
    fig.add_hline(y=poc_price, line_dash="dash", line_color="#ff4b4b", line_width=2, row=1, col=1)
    fig.add_annotation(x=last_idx, y=hist_df['MA5'].iloc[-1], text="← 5MA短線", showarrow=False, xshift=45, font=dict(color='#FFA500', size=11), row=1, col=1)
    fig.add_annotation(x=last_idx, y=hist_df['MA20'].iloc[-1], text="← 20MA月線", showarrow=False, xshift=55, font=dict(color='#1E90FF', size=11), row=1, col=1)
    fig.add_annotation(x=trade_dates[4], y=poc_price, text=f"← POC(月) 鐵板價 ({poc_price:.1f})", showarrow=False, yshift=10, font=dict(color='#ff4b4b', size=11, family="Arial Black"), row=1, col=1)
    
    colors = ['#ff4b4b' if r['Close'] >= r['Open'] else '#00cc96' for i, r in hist_df.iterrows()]
    fig.add_trace(go.Bar(x=trade_dates, y=hist_df['Volume'], name='成交量', marker_color=colors), row=2, col=1)
    
    exp1 = hist_df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = hist_df['Close'].ewm(span=26, adjust=False).mean()
    dif = exp1 - exp2
    macd = dif.ewm(span=9, adjust=False).mean()
    osc = dif - macd
    osc_colors = ['#ff4b4b' if val >= 0 else '#00cc96' for val in osc]
    fig.add_trace(go.Bar(x=trade_dates, y=osc, name='MACD柱', marker_color=osc_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=trade_dates, y=dif, name='DIF', line=dict(color='#1E90FF', width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=trade_dates, y=macd, name='MACD線', line=dict(color='#FFA500', width=1.2)), row=3, col=1)
    fig.add_annotation(x=last_idx, y=dif.iloc[-1], text="← MACD快線", showarrow=False, xshift=50, font=dict(color='#1E90FF', size=11), row=3, col=1)

    obv = (np.sign(hist_df['Close'].diff()) * hist_df['Volume']).fillna(0).cumsum()
    obv_ma10 = obv.rolling(10).mean()
    fig.add_trace(go.Scatter(x=trade_dates, y=obv, name='OBV主力線', line=dict(color='#9932CC', width=2.2)), row=4, col=1)
    fig.add_trace(go.Scatter(x=trade_dates, y=obv_ma10, name='OBV均線', line=dict(color='#ccc', width=1, dash='dot')), row=4, col=1)
    fig.add_annotation(x=last_idx, y=obv.iloc[-1], text="← OBV主力籌碼", showarrow=False, xshift=65, font=dict(color='#9932CC', size=11, family="Arial Black"), row=4, col=1)

    fig.update_layout(height=780, xaxis_rangeslider_visible=False, showlegend=False, margin=dict(t=40, b=10, r=120),
                      title=dict(text=f"{name} 走勢與法人級指標分析", font=dict(size=16)))
    fig.update_xaxes(type='category', nticks=15)
    return fig

def color_strategy(val):
    if any(x in str(val) for x in ["🚀", "💎", "🟢"]): return 'color: #ff4b4b; font-weight: bold;'
    if any(x in str(val) for x in ["🛑", "⚠️", "🔥"]): return 'color: #00cc96; font-weight: bold;'
    return ''

# 💡 回歸的高亮設定
def highlight_overlap(val):
    if val == "🔥 重疊": return 'color: #ff4b4b; font-weight: bold; background-color: #ffe6e6;'
    return ''

# 💡 內建 PDF 爬蟲引擎
@st.cache_data(ttl=3600)
def parse_etf_pdf_in_memory(pdf_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(pdf_url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            return pd.DataFrame([{"解析結果": f"下載失敗，網站阻擋或網址無效 (狀態碼: {res.status_code})"}])
            
        with pdfplumber.open(io.BytesIO(res.content)) as pdf:
            for page in pdf.pages[:2]:
                tables = page.extract_tables()
                for table in tables:
                    clean_table = [row for row in table if any(cell for cell in row)]
                    if len(clean_table) > 3: 
                        df = pd.DataFrame(clean_table[1:], columns=clean_table[0])
                        return df
        return pd.DataFrame([{"解析結果": "成功下載 PDF，但在前兩頁找不到可辨識的持股表格。"}])
    except Exception as e:
        return pd.DataFrame([{"解析結果": f"系統發生錯誤：{str(e)}"}])


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
my_input = st.sidebar.text_input("代號 (如: 2301, 1727)", "")
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
with st.spinner("🚀 正在以 20天(月線) 週期極速掃描籌碼密集區..."):
    df_all, hist_all = get_stock_data_v87(all_flat)

tab1, tab2, tab3, tab4 = st.tabs(["📊 首頁：大盤熱度", "🔍 細部題材：技術面", "🎯 波段選股 & 黑馬", "🛡️ ETF 戰情室 & PDF 爬蟲"])

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
        st.dataframe(df_f[['資料日期', '指標股', '漲跌幅(%)', '現價', 'POC價位(月)', '波段策略', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🔍 個股技術線型 X 光機")
        col_t2_1, col_t2_2 = st.columns(2)
        with col_t2_1: target = st.selectbox("📋 從清單選擇", df_f['指標股'].tolist(), key="t2_dropdown")
        with col_t2_2: search_t2 = st.text_input("🎯 或輸入任意代號搜尋 (如: 2330)", "", key="t2_search")
            
        if search_t2:
            with st.spinner(f"正在調閱 {search_t2} 月線籌碼..."):
                s_hist, s_name = fetch_single_stock(search_t2)
                if s_hist is not None: st.plotly_chart(plot_advanced_k_volume(s_hist, s_name), use_container_width=True, key=f"tab2_search_{search_t2}")
                else: st.error(f"找不到 {search_t2}，請確認代號是否正確！")
        else:
            if target in hist_all: st.plotly_chart(plot_advanced_k_volume(hist_all[target], target), use_container_width=True, key=f"tab2_list_{target}")

with tab3:
    if not df_all.empty:
        if my_holdings:
            st.markdown("### 💼 我的持股健檢")
            df_my = df_all[df_all['代號'].isin(my_holdings.keys())].sort_values("策略權重").drop(columns=['策略權重'])
            st.dataframe(df_my[['指標股', '漲跌幅(%)', '現價', 'POC價位(月)', '波段策略', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), use_container_width=True)
            
            st.markdown("#### 🔍 我的持股線型觀測")
            my_target = st.selectbox("選擇要分析的個人持股", df_my['指標股'].tolist(), key="my_t3_select")
            if my_target in hist_all:
                st.plotly_chart(plot_advanced_k_volume(hist_all[my_target], my_target), use_container_width=True, key=f"my_chart_{my_target}")
            st.markdown("---")
        
        st.markdown("### 🐎 今日潛在爆發黑馬")
        df_h = df_all[df_all['黑馬潛力'] != "-"].sort_values("策略權重").drop(columns=['策略權重'])
        st.dataframe(df_h[['所屬題材', '指標股', '漲跌幅(%)', '現價', 'POC價位(月)', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略', '黑馬潛力']) if not df_h.empty else pd.DataFrame(), use_container_width=True)
        
        st.markdown("---")
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1: st.markdown("### 🎯 全市場波段選股總表")
        with col_f2: filter_opt = st.radio("⚡ 一鍵快速篩選", ["全部顯示", "🚀 只看進場", "🟢 只看多頭", "🛑 只看停損"], horizontal=True)
        
        df_display = df_all.sort_values("策略權重").drop(columns=['策略權重'])
        
        if filter_opt == "🚀 只看進場": df_display = df_display[df_display['波段策略'].str.contains("🚀")]
        elif filter_opt == "🟢 只看多頭": df_display = df_display[df_display['波段策略'].str.contains("🟢")]
        elif filter_opt == "🛑 只看停損": df_display = df_display[df_display['波段策略'].str.contains("🛑")]
            
        st.dataframe(df_display[['資料日期', '所屬題材', '指標股', '漲跌幅(%)', '現價', 'POC價位(月)', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), height=600, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🔍 個股技術線型 X 光機")
        col_t3_1, col_t3_2 = st.columns(2)
        with col_t3_1: target_a = st.selectbox("📋 從全市場清單選擇", df_display['指標股'].tolist(), key="t3_dropdown")
        with col_t3_2: search_t3 = st.text_input("🎯 或輸入全台任意代號搜尋 (如: 2330)", "", key="t3_search")
            
        if search_t3:
            with st.spinner(f"正在調閱 {search_t3} 月線籌碼..."):
                s_hist, s_name = fetch_single_stock(search_t3)
                if s_hist is not None: st.plotly_chart(plot_advanced_k_volume(s_hist, s_name), use_container_width=True, key=f"tab3_search_{search_t3}")
                else: st.error(f"找不到 {search_t3}，請確認代號是否正確！")
        else:
            if target_a in hist_all: st.plotly_chart(plot_advanced_k_volume(hist_all[target_a], target_a), use_container_width=True, key=f"tab3_list_{target_a}")

# 💡 V87：完美的 第四頁 ETF 戰情室 + PDF 爬蟲
with tab4:
    st.markdown("### ⚔️ ETF 籌碼對決戰情室 (前十大持股)")
    st.write("精選台股最具代表性的熱門 ETF 與主動式 ETF 進行持股對決，一秒看穿籌碼重疊度與近期量能！")
    
    etf_list = list(ETF_DB.keys())
    
    col_e1, col_e2 = st.columns(2)
    with col_e1: etf1 = st.selectbox("選擇第一檔 (紅方)", etf_list, index=1)
    with col_e2: etf2 = st.selectbox("選擇第二檔 (藍方)", etf_list, index=2)
        
    if etf1 and etf2:
        holdings1 = ETF_DB[etf1]
        holdings2 = ETF_DB[etf2]
        
        common_stocks = set(holdings1.keys()).intersection(set(holdings2.keys()))
        overlap_score = 0
        for sym in common_stocks:
            overlap_score += min(holdings1[sym]['weight'], holdings2[sym]['weight'])
            
        st.markdown("---")
        st.markdown(f"#### 📊 前十大持股重疊度：**{overlap_score:.1f}%**")
        st.progress(overlap_score / 100.0)
        
        def build_etf_df(holdings, common):
            data = []
            for sym, info in holdings.items():
                marker = "🔥 重疊" if sym in common else ""
                data.append({"代號": sym, "名稱": info['name'], "題材": info['theme'], "權重(%)": info['weight'], "狀態": marker})
            return pd.DataFrame(data).sort_values("權重(%)", ascending=False).reset_index(drop=True)

        df_etf1 = build_etf_df(holdings1, common_stocks)
        df_etf2 = build_etf_df(holdings2, common_stocks)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(f"##### 🥊 {etf1}")
            v_today1, v_yest1, p1, c1 = get_etf_market_data(etf1)
            if v_today1 > 0:
                mc1, mc2 = st.columns(2)
                mc1.metric("現價", p1, f"{c1}%")
                mc2.metric("今日成交量(股)", f"{v_today1:,}", f"{(v_today1 - v_yest1):,} (較昨日)")
            st.dataframe(df_etf1.style.map(highlight_overlap, subset=['狀態']), use_container_width=True, hide_index=True)
            
        with col_m2:
            st.markdown(f"##### 🥊 {etf2}")
            v_today2, v_yest2, p2, c2 = get_etf_market_data(etf2)
            if v_today2 > 0:
                mc1, mc2 = st.columns(2)
                mc1.metric("現價", p2, f"{c2}%")
                mc2.metric("今日成交量(股)", f"{v_today2:,}", f"{(v_today2 - v_yest2):,} (較昨日)")
            st.dataframe(df_etf2.style.map(highlight_overlap, subset=['狀態']), use_container_width=True, hide_index=True)

    st.markdown("---")
    
    st.markdown("### 🕵️‍♀️ 主動式 ETF 月報 PDF 即時解析器 (進階功能)")
    st.info("主動式 ETF 每月會於投信官網釋出 PDF 月報。將 PDF 的真實網址貼在下方，系統將在雲端拆解並嘗試抓出持股明細表！")
    
    pdf_url_input = st.text_input("🔗 貼上投信官網月報 PDF 網址：", "")
    
    if st.button("🚀 啟動空中攔截解析"):
        if pdf_url_input:
            with st.spinner("正在潛入投信官網、下載並拆解 PDF...（這可能需要幾秒鐘）"):
                df_parsed = parse_etf_pdf_in_memory(pdf_url_input)
                if "解析結果" in df_parsed.columns:
                    st.warning(df_parsed.iloc[0]["解析結果"])
                else:
                    st.success("🎉 解析成功！以下是從 PDF 抽出的表格數據：")
                    st.dataframe(df_parsed, use_container_width=True)
        else:
            st.error("請先貼上 PDF 網址喔！")
