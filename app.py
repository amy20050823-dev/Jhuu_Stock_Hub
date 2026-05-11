import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import time
import random

# ================= 1. 網頁配置 =================
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

if 'custom_themes' not in st.session_state:
    st.session_state['custom_themes'] = {}

def get_safe_session():
    session = requests.Session()
    # 隨機化 User-Agent 模擬不同瀏覽器
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ]
    session.headers.update({
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    })
    return session

# ================= 1.6 自動抓取中文股名小爬蟲 =================
def get_tw_stock_name(symbol):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{symbol}"
        res = get_safe_session().get(url, timeout=3)
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
    "高速傳輸/線材": {"4966": "譜瑞-KY", "5269": "祥碩", "6756": "威鋒電子", "6661": "威健", "6653": "嘉基", "3665": "貿聯-KY", "3023": "信邦", "6102": "倚強科"},
    "AI機器人/自動化": {"2359": "所羅門", "2365": "昆盈", "6414": "樺漢", "8374": "羅昇", "4510": "高鋒", "1590": "亞德客-KY", "2049": "上銀", "4545": "銘鈺"},
    "AI PC/工業電腦": {"2357": "華碩", "2353": "宏碁", "2395": "研華", "6245": "立端", "8114": "振樺電", "6206": "飛捷"},
    "PCB/銅箔基板": {"2383": "台光電", "6213": "聯茂", "6274": "台燿", "2368": "金像電", "5469": "瀚宇博", "6153": "嘉聯益"},
    "PCB上游玻纖布": {"1815": "富喬", "5340": "建榮", "5475": "德宏"},
    "記憶體與模組": {"2408": "南亞科", "2344": "華邦電", "8299": "群聯", "3260": "威剛", "2451": "創見", "4967": "十銓"}, 
    "被動元件": {"2327": "國巨", "2492": "華新科", "3026": "禾伸堂", "6127": "九暘", "2478": "大毅"},
    "消費性IC/MCU": {"2454": "聯發科", "4919": "盛群", "2337": "旺宏", "3034": "聯詠", "2401": "凌陽", "4952": "凌通"},
    "重電與能源轉型": {"1513": "中興電", "1519": "華城", "1503": "士電", "1514": "亞力", "1605": "華新", "1515": "力山", "6806": "森崴能源"},
    "航運與航空": {"2603": "長榮", "2609": "陽明", "2615": "萬海", "2618": "長榮航", "2610": "華航", "2634": "漢翔"}
}

STOCK_DB = {**BASE_STOCK_DB, **st.session_state['custom_themes']}
SYMBOL_TO_THEME = {sym: theme for theme, stocks in STOCK_DB.items() for sym in stocks}
LEADERS = ["2330", "2317", "3450", "4979", "3037", "2383", "3017", "2308", "2327", "2454", "3661", "1519", "2603"]

# ================= 4. 核心抓取與策略函數 =================

def chip_card_html(title, value, status, color):
    """自定義籌碼看板 HTML，縮小字體並優化排版"""
    return f"""
    <div style="padding: 10px; border-radius: 10px; border: 1px solid #f0f2f6; background-color: #ffffff; text-align: center; height: 100%;">
        <div style="color: #666; font-size: 14px; margin-bottom: 5px;">{title}</div>
        <div style="color: #111; font-size: 24px; font-weight: bold; margin-bottom: 5px;">{value}</div>
        <div style="color: {color}; font-size: 13px;">{status}</div>
    </div>
    """

@st.cache_data(ttl=3600)
def get_market_chips():
    return {
        "三大法人買賣超": {"外資": "-109.84 億", "投信": "+121.88 億", "自營": "+37.30 億"},
        "外資台指未平倉": {"淨口數": "-54,225 口", "狀態": "● 警戒 (空單留倉)", "color": "#ff4b4b"},
        "散戶小台多空比": {"比例": "+11.54%", "狀態": "● 散戶做多 (反向偏空)", "color": "#ff4b4b"},
        "Put/Call Ratio": {"比例": "162.33%", "狀態": "● 買權強勢 (下檔有撐)", "color": "#00cc96"}
    }

@st.cache_data(ttl=1800)
def get_market_news():
    news = []
    try:
        url_tw = "https://news.google.com/rss/search?q=台股+OR+股市&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        res = requests.get(url_tw, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(res.text, 'xml')
        for item in soup.find_all('item')[:15]:
            news.append({"title": item.title.text.split(' - ')[0], "link": item.link.text})
    except: pass
    return news

@st.cache_data(ttl=600)
def get_indices():
    indices_dict = {"加權指數": "^TWII", "那斯達克": "^IXIC", "費半指數": "^SOX", "美光(MU)": "MU", "三星(韓國)": "005930.KS", "WTI原油": "CL=F"}
    res = {}
    for name, symbol in indices_dict.items():
        try:
            # 使用單檔查詢模式
            ticker = yf.Ticker(symbol, session=get_safe_session())
            hist = ticker.history(period="1mo")
            hist = hist.dropna(subset=['Close'])
            if len(hist) >= 2:
                close, prev = float(hist['Close'].iloc[-1]), float(hist['Close'].iloc[-2])
                res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
            else: res[name] = {"現價": 0, "漲跌幅": 0}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

@st.cache_data(ttl=1200)
def get_stock_advanced_data(stock_dict, vip_symbols=[]):
    data_list, price_history_dict = [], {}
    if not stock_dict: return pd.DataFrame(data_list), price_history_dict

    symbols = list(stock_dict.keys())
    # 💡 V66 核心：捨棄 yf.download 批次下載，改用隨機間隔的 Ticker 單檔下載
    progress_text = f"正在逐檔掃描 {len(symbols)} 檔標的，此模式較慢但最穩定..."
    my_bar = st.progress(0, text=progress_text)
    
    session = get_safe_session()
    for i, symbol in enumerate(symbols):
        try:
            name = stock_dict[symbol]
            hist = pd.DataFrame()
            # 優先嘗試 .TW 再嘗試 .TWO
            for suffix in [".TW", ".TWO"]:
                tkr_str = f"{symbol}{suffix}"
                ticker = yf.Ticker(tkr_str, session=session)
                temp_hist = ticker.history(period="6mo")
                if not temp_hist.empty and len(temp_hist) >= 60:
                    hist = temp_hist
                    break
            
            if hist.empty: continue
            
            # --- 隨機休息 0.1~0.5 秒模仿人類 ---
            time.sleep(random.uniform(0.1, 0.4))
            my_bar.progress((i + 1) / len(symbols))

            # --- 指標運算 ---
            close = float(hist['Close'].iloc[-1])
            open_p, high_p, low_p = float(hist['Open'].iloc[-1]), float(hist['High'].iloc[-1]), float(hist['Low'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
            change_pct = ((close - prev_close) / prev_close) * 100
            
            hist['MA5'], hist['MA20'], hist['MA60'] = hist['Close'].rolling(5).mean(), hist['Close'].rolling(20).mean(), hist['Close'].rolling(60).mean()
            vol_today, vol_ma5 = float(hist['Volume'].iloc[-1]), hist['Volume'].rolling(5).mean().iloc[-1]
            bb_std = hist['Close'].rolling(20).std().iloc[-1]
            bb_width = (4 * bb_std) / hist['MA20'].iloc[-1]
            
            low_9, high_9 = hist['Low'].rolling(9).min(), hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
            k_s = rsv.ewm(com=2).mean()
            d_s = k_s.ewm(com=2).mean()
            kd_golden = (k_s.iloc[-1] > d_s.iloc[-1]) and (k_s.iloc[-2] <= d_s.iloc[-2])

            exp1, exp2 = hist['Close'].ewm(span=12, adjust=False).mean(), hist['Close'].ewm(span=26, adjust=False).mean()
            dif, macd = exp1 - exp2, (exp1 - exp2).ewm(span=9, adjust=False).mean()
            osc = dif - macd
            
            obv = (np.sign(hist['Close'] - hist['Close'].shift(1)) * hist['Volume']).fillna(0).cumsum()
            obv_is_up_right = (obv.iloc[-1] >= obv.rolling(20).max().iloc[-1] * 0.95) and (obv.iloc[-1] > obv.rolling(20).mean().iloc[-1])
            obv_uptrend = obv.iloc[-1] > obv.rolling(10).mean().iloc[-1]
            
            res_20 = hist['High'].rolling(20).max().shift(1).iloc[-1]
            far_from_res, is_breakout = (res_20 - close) / close > 0.05, close > res_20
            
            # --- 標籤判定 ---
            action, action_prio = "🟡 盤整 0軸下 無動能", 4 
            if close < hist['MA20'].iloc[-1]: action, action_prio = "🛑 破線停損 (籌碼流出)", 8
            elif (kd_golden or (osc.iloc[-1] > osc.iloc[-2])) and obv_uptrend and obv_is_up_right and (far_from_res or is_breakout): action, action_prio = "🚀 可進場，kd obv上 無壓力(或突破)", 1
            elif close > hist['MA20'].iloc[-1] and close > hist['MA60'].iloc[-1]: action, action_prio = "🟢 多頭續抱", 3

            crown = "👑 " if symbol in LEADERS else ""
            data_list.append({
                "資料日期": hist.index[-1].strftime('%m/%d'), "代號": symbol, "所屬題材": SYMBOL_TO_THEME.get(symbol, "📌 自選股"),
                "指標股": f"{crown}{name} ({symbol})", "漲跌幅(%)": round(change_pct, 2), "現價": round(close, 2),
                "波段策略": action, "策略權重": action_prio, "黑馬潛力": "🐎 爆發準備" if (close > hist['MA20'].iloc[-1] and (bb_width < 0.15) and obv_uptrend) else "-",
                "籌碼動能": "爆量流入" if vol_today > vol_ma5 * 1.5 else "量能平穩"
            })
            price_history_dict[f"{crown}{name} ({symbol})"] = hist.tail(60)
        except: pass
    
    my_bar.empty()
    return pd.DataFrame(data_list), price_history_dict

def color_strategy(val):
    if any(x in str(val) for x in ["🚀", "💎", "🟢"]): return 'color: #ff4b4b; font-weight: bold;'
    if any(x in str(val) for x in ["🛑", "⚠️", "🔥"]): return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 5. UI 介面 =================
st.title("台股題材動態觀測站 V66 穩壓版")

st.sidebar.header("💼 我的持股健檢")
my_holdings_input = st.sidebar.text_input("輸入股票代號 (如: 8064, 5433)", "")
my_holdings_dict, vip_list = {}, []
if my_holdings_input:
    for s in my_holdings_input.split(','):
        s = s.strip()
        if s:
            name = get_tw_stock_name(s)
            my_holdings_dict[s], vip_list.append(s)

st.sidebar.markdown("---")
if st.sidebar.button("強制刷新 (清除快取並重啟掃描)"):
    st.cache_data.clear()
    st.rerun()

all_flat = {}
for th, stks in STOCK_DB.items(): all_flat.update(stks)
if my_holdings_dict: all_flat.update(my_holdings_dict)

df_all, hist_all = get_stock_advanced_data(all_flat, vip_symbols=vip_list)

tab1, tab2, tab3 = st.tabs(["首頁：大盤與籌碼", "細部題材：技術面", "波段選股"])

with tab1:
    idx_data = get_indices()
    cols = st.columns(len(idx_data))
    for i, (n, d) in enumerate(idx_data.items()): cols[i].metric(n, d["現價"], f"{d['漲跌幅']}%")
    
    st.markdown("---")
    st.subheader("📊 大盤籌碼戰情室")
    chip_data = get_market_chips()
    
    # 💡 V66 修正：自定義 HTML 縮小「口數」與「多空比」字體
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(chip_card_html("三大法人買賣超", f"外資 {chip_data['三大法人買賣超']['外資']}", f"投信 {chip_data['三大法人買賣超']['投信']}", "#333"), unsafe_allow_html=True)
    with c2:
        st.markdown(chip_card_html("外資台指淨未平倉", chip_data['外資台指未平倉']['淨口數'], chip_data['外資台指未平倉']['狀態'], chip_data['外資台指未平倉']['color']), unsafe_allow_html=True)
    with c3:
        st.markdown(chip_card_html("散戶小台多空比", chip_data['散戶小台多空比']['比例'], chip_data['散戶小台多空比']['狀態'], chip_data['散戶小台多空比']['color']), unsafe_allow_html=True)
    with c4:
        st.markdown(chip_card_html("Put/Call Ratio", chip_data['Put/Call Ratio']['比例'], chip_data['Put/Call Ratio']['狀態'], chip_data['Put/Call Ratio']['color']), unsafe_allow_html=True)

    st.markdown("---")
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        st.subheader("今日族群熱門排行")
        if not df_all.empty:
            theme_rank = df_all.groupby('所屬題材')['漲跌幅(%)'].mean().reset_index().sort_values("漲跌幅(%)", ascending=False)
            st.dataframe(theme_rank, height=400, use_container_width=True, hide_index=True)
        else: st.warning("正在等待 Yahoo IP 解鎖中，請點擊左側『強制刷新』嘗試...")
    with col_r:
        st.subheader("題材偵察機 (盤面新聞)")
        news_list = get_market_news()
        with st.container(height=400):
            for n in news_list: st.markdown(f"🔗 [{n['title']}]({n['link']})")

with tab2:
    sel_theme = st.selectbox("請選擇族群", list(STOCK_DB.keys()))
    if not df_all.empty:
        df_f = df_all[df_all['所屬題材'] == sel_theme].sort_values("策略權重")
        st.dataframe(df_f[['資料日期', '指標股', '漲跌幅(%)', '現價', '波段策略', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), use_container_width=True)

with tab3:
    if not df_all.empty:
        df_s = df_all.sort_values("策略權重")
        st.markdown("### 全市場波段選股總表")
        st.dataframe(df_s[['資料日期', '所屬題材', '指標股', '漲跌幅(%)', '現價', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略']), height=600, use_container_width=True)
