import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# ================= 1. 網頁配置 =================
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

# ================= 2. 大盤解析區 =================
DAILY_ANALYSIS = """
【今日大盤與資金流向分析】
目前盤面主軸仍圍繞在 AI 供應鏈與半導體先進製程。當加權指數在高檔震盪時，資金會轉向具備防禦屬性與低基期的題材股。
建議觀察：1. 是否有新題材在新聞中頻繁出現？ 2. 個股突破布林上緣且爆量時的「超級進場點」。
"""

# ================= 3. 產業題材與龍頭資料庫 =================
STOCK_DB = {
    "輝達GTC/伺服器": {"2330": "台積電", "2317": "鴻海", "2382": "廣達", "3231": "緯創", "2376": "技嘉", "6669": "緯穎", "3706": "神達"},
    "CPO/光通訊": {"4979": "華星光", "3450": "聯鈞", "3081": "聯亞", "3363": "上詮", "6442": "光聖", "6451": "訊芯-KY", "3163": "波若威"},
    "PCB/銅箔基板": {"2383": "台光電", "6213": "聯茂", "6274": "台燿", "2368": "金像電", "3037": "欣興", "8046": "南電", "3189": "景碩", "2313": "華通"},
    "網通/石英元件": {"3042": "晶技", "3221": "台嘉碩", "8182": "加高", "2484": "希華"},
    "記憶體": {"2408": "南亞科", "2344": "華邦電", "8299": "群聯", "3260": "威剛"},
    "散熱管理": {"3017": "奇鋐", "3324": "雙鴻", "2421": "建準", "6230": "超眾", "8996": "高力"},
    "電源供應器": {"2308": "台達電", "2301": "光寶科", "6409": "旭隼"},
    "BBU(備援電池)": {"6121": "新普", "3211": "順達", "3323": "加百裕", "6781": "AES-KY"},
    "被動元件": {"2327": "國巨", "2492": "華新科", "3026": "禾伸堂"},
    "ASIC/IP矽智財": {"3443": "智原", "3661": "世芯-KY", "6643": "M31", "6533": "晶心科"},
    "高速傳輸與介面": {"4966": "譜瑞-KY", "5269": "祥碩", "6756": "威鋒電子", "6661": "威健"},
    "CoWoS/先進封裝": {"3131": "弘塑", "6187": "萬潤", "5443": "均豪", "6640": "均华", "6196": "帆宣"},
    "半導體耗材與檢測": {"6223": "旺矽", "6217": "中探針", "1560": "研伸", "1773": "勝一", "3583": "辛耘"},
    "邊緣運算與MCU": {"2454": "聯發科", "4919": "盛群", "2337": "旺宏"},
    "AI機器人/自動化": {"2359": "所羅門", "2365": "昆盈", "6414": "樺漢", "8374": "羅昇", "4510": "高鋒"},
    "低軌衛星": {"2313": "華通", "3491": "昇達科", "6271": "同欣電", "3380": "明泰"}
}

SYMBOL_TO_THEME = {}
for theme_full, stocks in STOCK_DB.items():
    for sym in stocks:
        SYMBOL_TO_THEME[sym] = theme_full

LEADERS = ["2330", "2317", "3450", "4979", "3037", "2383", "3017", "2308", "2327", "2454", "3661"]

# ================= 4. 核心抓取與策略函數 =================
@st.cache_data(ttl=1800)
def get_market_news():
    news = []
    try:
        url_tw = "https://news.google.com/rss/search?q=台股+OR+股市&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        res = requests.get(url_tw, timeout=5)
        soup = BeautifulSoup(res.text, 'xml')
        for item in soup.find_all('item')[:20]:
            title = item.title.text.split(' - ')[0]
            news.append({"title": title, "link": item.link.text})
    except: pass
    return news

@st.cache_data(ttl=600)
def get_indices():
    indices_dict = {"加權指數": "^TWII", "那斯達克": "^IXIC", "費半指數": "^SOX", "VIX恐慌": "^VIX", "WTI原油": "CL=F"}
    res = {}
    for name, symbol in indices_dict.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if len(hist) >= 2:
                close, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
            else: res[name] = {"現價": 0, "漲跌幅": 0}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

@st.cache_data(ttl=600)
def get_stock_advanced_data(stock_dict):
    data_list = []
    price_history_dict = {} 
    
    for symbol, name in stock_dict.items():
        try:
            t = None
            hist = pd.DataFrame()
            # 改為 4 個月，減輕載入負擔，同時確保 60MA 算得出來
            for suffix in [".TW", ".TWO"]:
                temp_t = yf.Ticker(f"{symbol}{suffix}")
                temp_hist = temp_t.history(period="4mo")
                if len(temp_hist) >= 60:
                    t = temp_t
                    hist = temp_hist
                    break
            
            if hist.empty or len(hist) < 60: continue
                
            crown = "👑 " if symbol in LEADERS else ""
            display_name = f"{crown}{name} ({symbol})"

            close = hist['Close'].iloc[-1]
            open_p = hist['Open'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change_pct = ((close - prev_close) / prev_close) * 100
            
            hist['MA5'] = hist['Close'].rolling(5).mean()
            hist['MA20'] = hist['Close'].rolling(20).mean()
            hist['MA60'] = hist['Close'].rolling(60).mean()
            
            bb_std = hist['Close'].rolling(20).std().iloc[-1]
            upper_bb = hist['MA20'].iloc[-1] + 2 * bb_std
            bb_width = (4 * bb_std) / hist['MA20'].iloc[-1]
            
            price_history_dict[display_name] = hist.tail(60)

            vol_today = hist['Volume'].iloc[-1]
            vol_ma5 = hist['Volume'].rolling(5).mean().iloc[-1]
            
            low_9 = hist['Low'].rolling(9).min()
            high_9 = hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
            k_s = rsv.ewm(com=2).mean()
            d_s = k_s.ewm(com=2).mean()
            kd_golden = (k_s.iloc[-1] > d_s.iloc[-1]) and (k_s.iloc[-2] <= d_s.iloc[-2])

            action = "⚪ 盤整觀望"
            action_prio = 99
            
            # 策略核心
            if k_s.iloc[-1] > 80 and close < hist['MA5'].iloc[-1]: action, action_prio = "💸 獲利了結", 6
            elif close < hist['MA20'].iloc[-1]: 
                if close < hist['MA60'].iloc[-1] or vol_today < vol_ma5 * 0.7: action, action_prio = "🛑 賣出停損", 5
                elif vol_today > vol_ma5 * 1.5: action, action_prio = "💎 跌破月線護盤", 2
                else: action, action_prio = "🛌 守季線觀察", 8
            elif close > hist['MA5'].iloc[-1] and close > hist['MA20'].iloc[-1]:
                if close > open_p and vol_today > hist['Volume'].iloc[-2]:
                    if vol_today > vol_ma5 * 1.5 and kd_golden and close > upper_bb: action, action_prio = "🚀 超級進場點", 0
                    elif vol_today > vol_ma5 * 1.5 and kd_golden: action, action_prio = "💰 強力加碼", 1
                    elif kd_golden and vol_today <= vol_ma5 * 1.5: action, action_prio = "➕ 加碼金叉", 3
                    elif k_s.iloc[-1] > 80: action, action_prio = "🔥 續抱不追高", 7
                    else: action, action_prio = "🔴 試水溫", 4
                elif close < open_p: action, action_prio = "👀 收黑開高走低", 10
            elif close >= hist['MA20'].iloc[-1]: action, action_prio = "🟢 持股", 9

            obv = (np.sign(hist['Close'] - hist['Close'].shift(1)) * hist['Volume']).fillna(0).cumsum()
            is_potential = (close > hist['MA20'].iloc[-1]) and (bb_width < 0.15) and (obv.iloc[-1] > obv.rolling(10).mean().iloc[-1])

            data_list.append({
                "代號": symbol, 
                "所屬題材": SYMBOL_TO_THEME.get(symbol, "自選"),
                "指標股": display_name, 
                "漲跌幅(%)": round(change_pct, 2), 
                "現價": round(close, 2), 
                "波段策略": action,
                "策略權重": action_prio,
                "黑馬潛力": "🐎 爆發準備" if is_potential else "-",
                "籌碼動能": "爆量流入" if vol_today > vol_ma5 * 1.5 else ("量縮觀望" if vol_today < vol_ma5 * 0.7 else "量能平穩")
            })
        except: pass
            
    return pd.DataFrame(data_list), price_history_dict

def plot_k_volume(hist_df, name):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=hist_df.index, open=hist_df['Open'], high=hist_df['High'], low=hist_df['Low'], close=hist_df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA5'], name='5MA', line=dict(color='#FFA500')), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA20'], name='20MA', line=dict(color='#1E90FF')), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA60'], name='60MA', line=dict(color='#8A2BE2')), row=1, col=1)
    
    colors = ['#ff4b4b' if r['Close'] >= r['Open'] else '#00cc96' for i, r in hist_df.iterrows()]
    fig.add_trace(go.Bar(x=hist_df.index, y=hist_df['Volume'], name='成交量', marker_color=colors), row=2, col=1)
    fig.update_layout(height=550, xaxis_rangeslider_visible=False, showlegend=False, margin=dict(t=30, b=10))
    return fig

def color_strategy(val):
    if isinstance(val, (int, float)): return ''
    if any(x in str(val) for x in ["🚀", "💰", "➕", "💎", "🔴"]): return 'color: #ff4b4b; font-weight: bold;'
    if any(x in str(val) for x in ["🛑", "💸"]): return 'color: #00cc96; font-weight: bold;'
    if "🐎" in str(val): return 'color: #ffaa00; font-weight: bold;'
    return ''

def color_pct(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #ff4b4b; font-weight: bold;'
        if val < 0: return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 5. UI 介面 =================
st.title("台股題材動態觀測站")

# 側邊欄精簡化
st.sidebar.header("盤面族群追蹤")
sel_theme = st.sidebar.selectbox("請選擇族群", list(STOCK_DB.keys()))
st.sidebar.markdown("---")
if st.sidebar.button("強制刷新"):
    st.cache_data.clear()
    st.rerun()

tab1, tab2, tab3 = st.tabs(["首頁：大盤與熱度", "細部題材：技術面", "波段選股"])

with tab1:
    st.subheader("全球市場溫度計")
    idx_data = get_indices()
    cols = st.columns(5)
    for i, (n, d) in enumerate(idx_data.items()):
        cols[i].metric(n, d["現價"], f"{d['漲跌幅']}%")
    
    st.markdown("---")
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        st.subheader("今日熱門排行")
        with st.spinner("抓取最新資料中... (若長時間空白代表 Yahoo 伺服器忙碌中)"):
            theme_res = []
            for th, stks in STOCK_DB.items():
                df_t, _ = get_stock_advanced_data(stks)
                if not df_t.empty: theme_res.append({"題材": th, "漲跌(%)": round(df_t["漲跌幅(%)"].mean(), 2)})
            if theme_res:
                st.dataframe(pd.DataFrame(theme_res).sort_values("漲跌(%)", ascending=False), height=300, use_container_width=True, hide_index=True)
            else:
                st.error("⚠️ Yahoo Finance 暫時阻擋了連線，請過幾分鐘後再點擊左側『強制刷新』。")
            
    with col_r:
        st.subheader("題材偵察機 (盤面新聞)")
        news_list = get_market_news()
        with st.container(height=300):
            for n in news_list:
                st.markdown(f"🔗 [{n['title']}]({n['link']})")

with tab2:
    st.subheader(f"{sel_theme} - 技術與籌碼分析")
    df_f, hist_all = get_stock_advanced_data(STOCK_DB[sel_theme])
    if not df_f.empty:
        st.dataframe(df_f[['指標股', '漲跌幅(%)', '現價', '籌碼動能']].style.map(color_pct, subset=['漲跌幅(%)']), use_container_width=True)
        st.markdown("---")
        target = st.selectbox("查看 K 線與成交量", df_f['指標股'].tolist(), key="t2")
        if target in hist_all: st.plotly_chart(plot_k_volume(hist_all[target], target), use_container_width=True)
    else:
         st.error("⚠️ Yahoo Finance 暫時阻擋了連線，無法載入個股資料。")

with tab3:
    st.subheader("波段選股與主力黑馬掃描")
    
    all_flat = {}
    for th, stks in STOCK_DB.items(): all_flat.update(stks)
    
    with st.spinner("全域掃描中..."):
        df_a, hist_a = get_stock_advanced_data(all_flat)
        
        if not df_a.empty:
            st.markdown("### 今日潛在爆發黑馬")
            df_potential = df_a[df_a['黑馬潛力'] != "-"]
            if not df_potential.empty:
                st.dataframe(df_potential[['所屬題材', '指標股', '漲跌幅(%)', '現價', '波段策略', '黑馬潛力', '籌碼動能']].reset_index(drop=True).style.map(color_strategy, subset=['波段策略', '黑馬潛力']).map(color_pct, subset=['漲跌幅(%)']), use_container_width=True)
            else:
                st.info("今日無符合布林極度壓縮且主力吃貨的黑馬股。")

            st.markdown("---")
            st.markdown("### 全市場波段選股總表")
            df_s = df_a.sort_values("策略權重").drop(columns=['策略權重'])
            st.dataframe(df_s.style.map(color_strategy, subset=['波段策略', '黑馬潛力']).map(color_pct, subset=['漲跌幅(%)']), height=500, use_container_width=True)
            
            st.markdown("---")
            st.subheader("全域個股線型觀測")
            target_a = st.selectbox("選擇個股", df_s['指標股'].tolist(), key="t3")
            if target_a in hist_a: st.plotly_chart(plot_k_volume(hist_a[target_a], target_a), use_container_width=True)
        else:
            st.error("⚠️ Yahoo Finance 暫時阻擋了連線，選股系統暫時無法運作。")
