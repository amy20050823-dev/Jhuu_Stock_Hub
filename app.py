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

# ================= 1. 網頁配置 =================
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

if 'custom_themes' not in st.session_state:
    st.session_state['custom_themes'] = {}

# ================= 1.6 自動抓取中文股名小爬蟲 =================
def get_tw_stock_name(symbol):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find('title').text
        name = title.split('(')[0].strip()
        return name if name else f"自選_{symbol}"
    except:
        return f"自選_{symbol}"

# ================= 3. 產業題材資料庫 =================
BASE_STOCK_DB = {
    "輝達GTC/AI伺服器": {"2330": "台積電", "2317": "鴻海", "2382": "廣達", "3231": "緯創", "2376": "技嘉", "6669": "緯穎", "3706": "神達", "2356": "英業達", "2422": "佳能"},
    "散熱管理/水冷": {"3017": "奇鋐", "3324": "雙鴻", "2421": "建準", "6230": "超眾", "8996": "高力", "3483": "力致", "3338": "泰碩", "3653": "健策"},
    "電源與BBU": {"2308": "台達電", "2301": "光寶科", "6409": "旭隼", "6121": "新普", "3211": "順達", "3323": "加百裕", "6781": "AES-KY", "2324": "仁寶"},
    "CoWoS/先進封裝": {"3131": "弘塑", "6187": "萬潤", "5443": "均豪", "6640": "均華", "6196": "帆宣", "3583": "辛耘", "2338": "光罩", "6515": "穎崴"},
    "傳統與面板級封測": {"3711": "日月光投控", "2449": "京元電子", "6257": "矽格", "3481": "群創", "8064": "東捷", "3580": "友威科"},
    "半導體前端設備": {"3413": "京鼎", "3680": "家登", "8091": "翔名", "3055": "蔚華科"},
    "半導體化學與耗材": {"5434": "崇越", "4770": "上品", "4755": "三福化", "1773": "勝一", "3010": "華立", "6223": "旺矽", "6217": "中探針", "1560": "研伸", "1558": "伸興"},
    "廠務工程與無塵室": {"2404": "漢唐", "3402": "漢科", "6139": "亞翔", "5536": "聖暉*", "2493": "揚博", "6117": "迎廣"},
    "ASIC/IP矽智財": {"3443": "智原", "3661": "世芯-KY", "6643": "M31", "6533": "晶心科", "3529": "力旺", "3228": "金麗科", "6531": "愛普*"},
    "ABF載板/先進基板": {"3037": "欣興", "8046": "南電", "3189": "景碩", "8050": "廣積"},
    "CPO/矽光子": {"4979": "華星光", "3450": "聯鈞", "3081": "聯亞", "3363": "上詮", "6442": "光聖", "6451": "訊芯-KY", "3163": "波若威", "4908": "前鼎", "3234": "光環"},
    "網通/石英元件": {"3042": "晶技", "3221": "台嘉碩", "8182": "加高", "2484": "希華", "3596": "智易", "5388": "中磊", "3380": "明泰", "6285": "啟碁"},
    "低軌衛星": {"2313": "華通", "3491": "昇達科", "6271": "同欣電", "3466": "致振", "3152": "璟德"},
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

SYMBOL_TO_THEME = {}
for theme_full, stocks in STOCK_DB.items():
    for sym in stocks:
        SYMBOL_TO_THEME[sym] = theme_full

LEADERS = ["2330", "2317", "3450", "4979", "3037", "2383", "3017", "2308", "2327", "2454", "3661", "1519", "2603"]

# ================= 4. 核心抓取與策略函數 =================
@st.cache_data(ttl=1800)
def get_market_news():
    news = []
    try:
        url_tw = "https://news.google.com/rss/search?q=台股+OR+股市&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url_tw, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'xml')
        for item in soup.find_all('item')[:20]:
            title = item.title.text.split(' - ')[0]
            news.append({"title": title, "link": item.link.text})
    except: pass
    return news

@st.cache_data(ttl=600)
def get_indices():
    indices_dict = {"加權指數": "^TWII", "那斯達克": "^IXIC", "費半指數": "^SOX", "美光(MU)": "MU", "三星(韓國)": "005930.KS", "WTI原油": "CL=F"}
    res = {}
    for name, symbol in indices_dict.items():
        try:
            hist = yf.Ticker(symbol).history(period="1mo")
            hist = hist.dropna(subset=['Close'])
            if len(hist) >= 2:
                close, prev = float(hist['Close'].iloc[-1]), float(hist['Close'].iloc[-2])
                res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
            else: res[name] = {"現價": 0, "漲跌幅": 0}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

@st.cache_data(ttl=600)
def get_stock_advanced_data(stock_dict, vip_symbols=[]):
    data_list = []
    price_history_dict = {} 
    if not stock_dict: return pd.DataFrame(data_list), price_history_dict

    tickers_to_dl = []
    for sym in stock_dict.keys():
        tickers_to_dl.extend([f"{sym}.TW", f"{sym}.TWO"])
    
    try:
        batch_long = yf.download(tickers_to_dl, period="6mo", group_by="ticker", progress=False, threads=False)
        batch_short = yf.download(tickers_to_dl, period="5d", group_by="ticker", progress=False, threads=False)
    except:
        batch_long = pd.DataFrame()
        batch_short = pd.DataFrame()

    for symbol, name in stock_dict.items():
        try:
            hist_long, hist_short, tkr_suffix = pd.DataFrame(), pd.DataFrame(), ""
            
            for suffix in [".TW", ".TWO"]:
                tkr = f"{symbol}{suffix}"
                if isinstance(batch_long.columns, pd.MultiIndex):
                    if tkr in batch_long.columns.get_level_values(0):
                        temp_hist = batch_long[tkr].copy().dropna(subset=['Close', 'Volume', 'Open', 'High', 'Low']) 
                        if len(temp_hist) > 0: 
                            hist_long = temp_hist
                            tkr_suffix = tkr
                else:
                    temp_hist = batch_long.copy().dropna(subset=['Close', 'Volume', 'Open', 'High', 'Low'])
                    if len(temp_hist) > 0: 
                        hist_long = temp_hist
                        tkr_suffix = tkr
                
                if isinstance(batch_short.columns, pd.MultiIndex):
                    if tkr in batch_short.columns.get_level_values(0):
                        temp_hist_s = batch_short[tkr].copy().dropna(subset=['Close', 'Volume', 'Open', 'High', 'Low']) 
                        if len(temp_hist_s) > 0: hist_short = temp_hist_s
                else:
                    temp_hist_s = batch_short.copy().dropna(subset=['Close', 'Volume', 'Open', 'High', 'Low'])
                    if len(temp_hist_s) > 0: hist_short = temp_hist_s
                
                if not hist_long.empty: break
            
            if (hist_long.empty or len(hist_long) < 40) and (symbol in vip_symbols):
                for suffix in [".TW", ".TWO"]:
                    try:
                        tkr = f"{symbol}{suffix}"
                        rescue_data = yf.Ticker(tkr).history(period="6mo")
                        if not rescue_data.empty and len(rescue_data) >= 60:
                            hist_long = rescue_data.dropna(subset=['Close', 'Volume', 'Open', 'High', 'Low'])
                            tkr_suffix = tkr
                            rescue_short = yf.Ticker(tkr).history(period="5d")
                            if not rescue_short.empty: hist_short = rescue_short.dropna(subset=['Close', 'Volume', 'Open', 'High', 'Low'])
                            break
                    except: pass
            
            if hist_long.empty or len(hist_long) < 60: continue

            if not hist_short.empty:
                hist = pd.concat([hist_long, hist_short])
                hist = hist[~hist.index.duplicated(keep='last')].sort_index()
            else: hist = hist_long

            crown = "👑 " if symbol in LEADERS else ""
            display_name = f"{crown}{name} ({symbol})"
            last_date_str = hist.index[-1].strftime('%m/%d')

            close = float(hist['Close'].iloc[-1])
            open_p = float(hist['Open'].iloc[-1])
            high_p = float(hist['High'].iloc[-1])
            low_p = float(hist['Low'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
            change_pct = ((close - prev_close) / prev_close) * 100
            
            hist['Close'] = hist['Close'].astype(float)
            hist['Volume'] = hist['Volume'].astype(float)
            
            hist['MA5'] = hist['Close'].rolling(5).mean()
            hist['MA20'] = hist['Close'].rolling(20).mean()
            hist['MA60'] = hist['Close'].rolling(60).mean()
            vol_today = float(hist['Volume'].iloc[-1])
            vol_ma5 = hist['Volume'].rolling(5).mean().iloc[-1]
            
            bb_std = hist['Close'].rolling(20).std().iloc[-1]
            upper_bb = hist['MA20'].iloc[-1] + 2 * bb_std
            bb_width = (4 * bb_std) / hist['MA20'].iloc[-1]
            
            low_9, high_9 = hist['Low'].rolling(9).min(), hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
            k_s = rsv.ewm(com=2).mean()
            d_s = k_s.ewm(com=2).mean()
            kd_golden = (k_s.iloc[-1] > d_s.iloc[-1]) and (k_s.iloc[-2] <= d_s.iloc[-2])
            kd_dead = (k_s.iloc[-1] < d_s.iloc[-1]) and (k_s.iloc[-2] >= d_s.iloc[-2])

            exp1, exp2 = hist['Close'].ewm(span=12, adjust=False).mean(), hist['Close'].ewm(span=26, adjust=False).mean()
            dif = exp1 - exp2
            macd = dif.ewm(span=9, adjust=False).mean()
            osc = dif - macd
            macd_golden = (dif.iloc[-1] > macd.iloc[-1]) and (dif.iloc[-2] <= macd.iloc[-2])
            osc_turning_red = (osc.iloc[-1] > 0) and (osc.iloc[-2] <= 0)
            osc_shrinking = (osc.iloc[-1] < osc.iloc[-2]) and (osc.iloc[-1] > 0) 

            obv = (np.sign(hist['Close'] - hist['Close'].shift(1)) * hist['Volume']).fillna(0).cumsum()
            obv_20_max, obv_20_avg = obv.rolling(20).max().iloc[-1], obv.rolling(20).mean().iloc[-1]
            obv_is_up_right = (obv.iloc[-1] >= obv_20_max * 0.95) and (obv.iloc[-1] > obv_20_avg)
            obv_uptrend = obv.iloc[-1] > obv.rolling(10).mean().iloc[-1]
            
            price_h_20, obv_h_20 = hist['Close'].rolling(20).max().shift(1).iloc[-1], obv.rolling(20).max().shift(1).iloc[-1]
            price_l_20, obv_l_20 = hist['Close'].rolling(20).min().shift(1).iloc[-1], obv.rolling(20).min().shift(1).iloc[-1]
            
            top_div = (close >= price_h_20) and (obv.iloc[-1] < obv_h_20) 
            bottom_div = (close <= price_l_20) and (obv.iloc[-1] > obv_l_20) 
            
            # 💡 V61 修正盲點：壓力線與突破判斷
            res_20 = hist['High'].rolling(20).max().shift(1).iloc[-1]
            # 1. 距離天花板還很遠 (大於 5%)
            far_from_res = (res_20 - close) / close > 0.05
            # 2. 今天直接帶量把天花板捅破了！
            is_breakout = close > res_20
            # 3. 剛好撞到天花板而且沒突破
            near_res = (abs(res_20 - close) / close < 0.02) and (close <= res_20)

            price_history_dict[display_name] = hist.tail(60)

            real_body = abs(close - open_p) if abs(close - open_p) > 0 else 0.001
            total_len = (high_p - low_p) if (high_p - low_p) > 0 else 0.001
            upper_sh, lower_sh = high_p - max(close, open_p), min(close, open_p) - low_p
            has_upper_sh = (upper_sh > real_body * 1.5) and (upper_sh / total_len > 0.5)
            has_lower_sh = (lower_sh > real_body * 1.5) and (lower_sh / total_len > 0.5)

            action, action_prio = "🟡 盤整 0軸下 無動能", 99
            
            if close < hist['MA20'].iloc[-1] and obv.iloc[-1] < obv.rolling(5).mean().iloc[-1]:
                action, action_prio = "🛑 破線停損 (籌碼流出)", 0
            elif top_div or (near_res and close < open_p):
                action, action_prio = "⚠️ 假突破警告 (頂背離/壓)", 1
            elif k_s.iloc[-1] > 80 and has_upper_sh:
                action, action_prio = "🔥 短線過熱 (上影線)", 2
            elif (k_s.iloc[-1] > 80 and k_s.iloc[-1] < d_s.iloc[-1]) or (osc.iloc[-1] < osc.iloc[-2] and osc.iloc[-1] > 0):
                action, action_prio = "💸 獲利了結 (動能減弱)", 3
            # 💡 完美進場點升級：無壓力「或是」已強勢突破！
            elif ( (k_s.iloc[-1] > d_s.iloc[-1] and k_s.iloc[-2] <= d_s.iloc[-2]) or (osc.iloc[-1] > osc.iloc[-2]) ) and obv_uptrend and obv_is_up_right and (far_from_res or is_breakout):
                action, action_prio = "🚀 可進場，kd obv上 無壓力(或突破)", 4
            elif bottom_div and k_s.iloc[-1] < 30:
                action, action_prio = "💎 主力吃貨及底背離", 5
            elif close > hist['MA20'].iloc[-1] and close > hist['MA60'].iloc[-1] and dif.iloc[-1] > 0:
                action, action_prio = "🟢 多頭續抱", 6
            
            display_action = action
            if has_upper_sh and "過熱" not in action: display_action += " (⚡上影線)"
            if has_lower_sh: display_action += " (🔨下影線護盤)"

            data_list.append({
                "資料日期": hist.index[-1].strftime('%m/%d'), "代號": symbol, "所屬題材": SYMBOL_TO_THEME.get(symbol, "📌 自選股"),
                "指標股": display_name, "漲跌幅(%)": round(((close-prev_close)/prev_close)*100, 2), "現價": round(close, 2),
                "波段策略": display_action, "策略權重": action_prio, "黑馬潛力": "🐎 爆發準備" if (close > hist['MA20'].iloc[-1] and (bb_width < 0.15) and obv_uptrend) else "-",
                "籌碼動能": "爆量流入" if float(hist['Volume'].iloc[-1]) > vol_ma5 * 1.5 else ("量縮觀望" if float(hist['Volume'].iloc[-1]) < vol_ma5 * 0.7 else "量能平穩")
            })
        except: pass
    return pd.DataFrame(data_list), price_history_dict

def plot_k_volume(hist_df, name):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    hist_df['Open'], hist_df['High'], hist_df['Low'], hist_df['Close'], hist_df['Volume'] = hist_df['Open'].astype(float), hist_df['High'].astype(float), hist_df['Low'].astype(float), hist_df['Close'].astype(float), hist_df['Volume'].astype(float)
    
    fig.add_trace(go.Candlestick(x=hist_df.index, open=hist_df['Open'], high=hist_df['High'], low=hist_df['Low'], close=hist_df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA5'], name='5MA', line=dict(color='#FFA500')), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA20'], name='20MA', line=dict(color='#1E90FF')), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA60'], name='60MA', line=dict(color='#8A2BE2')), row=1, col=1)
    
    colors = ['#ff4b4b' if r['Close'] >= r['Open'] else '#00cc96' for i, r in hist_df.iterrows()]
    fig.add_trace(go.Bar(x=hist_df.index, y=hist_df['Volume'], name='成交量', marker_color=colors), row=2, col=1)
    fig.update_layout(height=550, xaxis_rangeslider_visible=False, showlegend=False, margin=dict(t=30, b=10))
    return fig

def color_strategy(val):
    if any(x in str(val) for x in ["🚀", "💎", "🟢", "🔨"]): return 'color: #ff4b4b; font-weight: bold;'
    if any(x in str(val) for x in ["🛑", "⚠️", "🔥", "💸", "⚡"]): return 'color: #00cc96; font-weight: bold;'
    return ''

def color_pct(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #ff4b4b; font-weight: bold;'
        if val < 0: return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 5. UI 介面 =================
st.title("台股題材動態觀測")

st.sidebar.header("🛠️ 新增自定義題材")
custom_theme_name = st.sidebar.text_input("題材名稱 (例: 📰 低軌衛星)", "")
custom_theme_stocks = st.sidebar.text_input("股票代號 (例: 2485)", "")

if st.sidebar.button("加入 / 更新題材庫"):
    if custom_theme_name and custom_theme_stocks:
        with st.spinner("自動合併與抓取股票名稱中..."):
            current_stocks = {}
            if custom_theme_name in BASE_STOCK_DB: current_stocks.update(BASE_STOCK_DB[custom_theme_name])
            if custom_theme_name in st.session_state['custom_themes']: current_stocks.update(st.session_state['custom_themes'][custom_theme_name])
            for s in custom_theme_stocks.split(','):
                s = s.strip()
                if s: current_stocks[s] = get_tw_stock_name(s)
            st.session_state['custom_themes'][custom_theme_name] = current_stocks
        st.sidebar.success(f"已成功擴充 {custom_theme_name}！")

st.sidebar.markdown("---")
st.sidebar.header("💼 我的持股健檢")
my_holdings_input = st.sidebar.text_input("輸入股票代號 (如: 8064, 5433)", "")
my_holdings_dict, vip_list = {}, []

if my_holdings_input:
    for s in my_holdings_input.split(','):
        s = s.strip()
        if s:
            name = get_tw_stock_name(s)
            my_holdings_dict[s] = f"持股 {name}"
            vip_list.append(s)

for theme, stocks in st.session_state['custom_themes'].items(): vip_list.extend(list(stocks.keys()))

st.sidebar.markdown("---")
if st.sidebar.button("強制刷新 (清除快取並重新載入)"):
    st.cache_data.clear()
    st.rerun()

all_flat = {}
for th, stks in STOCK_DB.items(): all_flat.update(stks)
if my_holdings_dict: all_flat.update(my_holdings_dict)

with st.spinner("🚀 隱形戰機模式啟動：單線程安靜抓取資料，繞過 Yahoo 警報系統..."):
    df_all, hist_all = get_stock_advanced_data(all_flat, vip_symbols=vip_list)

tab1, tab2, tab3 = st.tabs(["首頁：大盤與熱度", "細部題材：技術面", "波段選股"])

with tab1:
    idx_data = get_indices()
    cols = st.columns(len(idx_data))
    for i, (n, d) in enumerate(idx_data.items()): cols[i].metric(n, d["現價"], f"{d['漲跌幅']}%")
    st.markdown("---")
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        st.subheader("今日熱門排行")
        if not df_all.empty:
            theme_rank = df_all.groupby('所屬題材')['漲跌幅(%)'].mean().reset_index()
            theme_rank.columns = ['題材', '漲跌(%)']
            theme_rank['漲跌(%)'] = theme_rank['漲跌(%)'].round(2)
            st.dataframe(theme_rank.sort_values("漲跌(%)", ascending=False), height=400, use_container_width=True, hide_index=True)
        else:
            st.error("⚠️ Yahoo 伺服器仍未放行，請休息 5 分鐘後再點擊左下角『強制刷新』！")
    with col_r:
        st.subheader("題材偵察機 (盤面新聞)")
        news_list = get_market_news()
        with st.container(height=400):
            for n in news_list: st.markdown(f"🔗 [{n['title']}]({n['link']})")

with tab2:
    sel_theme = st.selectbox("請選擇族群", list(STOCK_DB.keys()))
    if not df_all.empty:
        df_f = df_all[df_all['所屬題材'] == sel_theme]
        st.dataframe(df_f[['資料日期', '指標股', '漲跌幅(%)', '現價', '波段策略', '籌碼動能']].style.map(color_pct, subset=['漲跌幅(%)']).map(color_strategy, subset=['波段策略']), use_container_width=True)
        st.markdown("---")
        if not df_f.empty:
            target = st.selectbox("查看 K 線與成交量", df_f['指標股'].tolist(), key="t2")
            if target in hist_all: st.plotly_chart(plot_k_volume(hist_all[target], target), use_container_width=True, key=f"chart_tab2_{target}")

with tab3:
    st.markdown("🚀 已載入 MACD、OBV背離 與 20日壓力全域過濾器")
    if not df_all.empty:
        df_potential = df_all[df_all['黑馬潛力'] != "-"]
        
        if my_holdings_dict:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("### 💼 我的持股健檢")
                df_my = df_all[df_all['代號'].isin(my_holdings_dict.keys())]
                if not df_my.empty:
                    st.dataframe(df_my[['資料日期', '指標股', '漲跌幅(%)', '現價', '波段策略', '籌碼動能']].style.map(color_strategy, subset=['波段策略']).map(color_pct, subset=['漲跌幅(%)']), use_container_width=True)
                else:
                    st.warning("找不到輸入的股票資料。")
            with col_t2:
                st.markdown("### 🐎 今日潛在爆發黑馬")
                if not df_potential.empty:
                    st.dataframe(df_potential[['所屬題材', '指標股', '漲跌幅(%)', '現價', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略', '黑馬潛力']).map(color_pct, subset=['漲跌幅(%)']), use_container_width=True)
                else:
                    st.info("今日無符合布林壓縮且主力吃貨的黑馬股。")
        else:
            st.markdown("### 🐎 今日潛在爆發黑馬")
            if not df_potential.empty:
                st.dataframe(df_potential[['所屬題材', '指標股', '漲跌幅(%)', '現價', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略', '黑馬潛力']).map(color_pct, subset=['漲跌幅(%)']), use_container_width=True)
            else:
                st.info("今日無符合布林壓縮且主力吃貨的黑馬股。")

        st.markdown("---")
        st.markdown("### 全市場波段選股總表")
        df_s = df_all.sort_values("策略權重").drop(columns=['策略權重'])
        st.dataframe(df_s[['資料日期', '所屬題材', '指標股', '漲跌幅(%)', '現價', '波段策略', '黑馬潛力', '籌碼動能']].style.map(color_strategy, subset=['波段策略', '黑馬潛力']).map(color_pct, subset=['漲跌幅(%)']), height=600, use_container_width=True)
        
        st.markdown("---")
        st.subheader("全域個股線型觀測")
        target_a = st.selectbox("選擇個股", df_s['指標股'].tolist(), key="t3")
        if target_a in hist_all: st.plotly_chart(plot_k_volume(hist_all[target_a], target_a), use_container_width=True, key=f"chart_tab3_{target_a}")
