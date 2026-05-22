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
    trade_
