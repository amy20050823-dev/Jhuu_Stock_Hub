import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

# 1. 題材資料庫
STOCK_DB = {
    "🤖 輝達GTC/伺服器": {"2330": "台積電", "2317": "鴻海", "2382": "廣達", "3231": "緯創", "2376": "技嘉", "6669": "緯穎", "3661": "世芯-KY", "3706": "神達"},
    "✨ CPO/光通訊": {"4979": "華星光", "3450": "聯鈞", "3081": "聯亞", "3363": "上詮", "6442": "光聖", "6451": "訊芯-KY", "3163": "波若威"},
    "🖨️ PCB/銅箔基板": {"2383": "台光電", "6213": "聯茂", "6274": "台燿", "2368": "金像電", "3037": "欣興", "8046": "南電", "3189": "景碩", "2313": "華通"},
    "⚡ 網通/石英元件": {"3042": "晶技", "3221": "台嘉碩", "8182": "加高", "2484": "希華"},
    "📦 CoWoS/先進封裝": {"3131": "弘塑", "3583": "辛耘", "6187": "萬潤", "5443": "均豪", "6640": "均華", "6196": "帆宣"},
    "🔋 BBU(備援電池)": {"6121": "新普", "3211": "順達", "3323": "加百裕", "6781": "AES-KY"},
    "🦾 AI機器人/自動化": {"2359": "所羅門", "2365": "昆盈", "6414": "樺漢", "8374": "羅昇", "4510": "高鋒"},
    "🔌 重電/綠能電網": {"1519": "華城", "1503": "士電", "1513": "中興電", "1514": "亞力", "1609": "大亞"},
    "🛰️ 低軌衛星": {"2313": "華通", "3491": "昇達科", "6271": "同欣電", "3380": "明泰"},
    "🧠 記憶體": {"2408": "南亞科", "2344": "華邦電", "8299": "群聯", "3260": "威剛"}
}

THEME_KEYWORDS = {
    "輝達GTC/伺服器": ["輝達", "NVIDIA", "伺服器", "GB200"],
    "CPO/光通訊": ["CPO", "光通訊", "矽光子"],
    "PCB/銅箔基板": ["PCB", "銅箔基板", "CCL"],
    "網通/石英元件": ["網通", "石英", "WiFi 7"],
    "CoWoS/先進封裝": ["CoWoS", "先進封裝", "封測", "台積電設備"],
    "BBU(備援電池)": ["BBU", "備援電池", "電池模組"],
    "AI機器人/自動化": ["機器人", "自動化", "所羅門", "無人機"],
    "重電/綠能電網": ["重電", "電網", "綠能", "台電", "變壓器"],
    "低軌衛星": ["低軌衛星", "SpaceX", "Satellite"],
    "記憶體": ["記憶體", "DRAM", "HBM", "Micron"]
}

# 2. 自動抓新聞 (擴大掃描範圍至 20 則)
@st.cache_data(ttl=1800)
def get_market_news():
    news = []
    translator = GoogleTranslator(source='auto', target='zh-TW')
    try:
        url_tw = "https://news.cnyes.com/news/cat/tw_stock"
        soup = BeautifulSoup(requests.get(url_tw, timeout=5).text, 'html.parser')
        news.extend([f"[國內] {t.get_text()}" for t in soup.select('h3')[:20]])
    except: pass
    try:
        url_cnbc = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
        soup = BeautifulSoup(requests.get(url_cnbc, timeout=5).text, 'xml')
        for item in soup.find_all('item')[:15]:
            try: news.append(f"[國際] {translator.translate(item.title.text)}")
            except: pass
    except: pass
    return news

# 3. 獲取大盤指數 (移除有問題的櫃買)
@st.cache_data(ttl=600)
def get_indices():
    indices_dict = {
        "加權指數": "^TWII", 
        "那斯達克": "^IXIC", "費半指數": "^SOX", "VIX恐慌": "^VIX"
    }
    res = {}
    for name, symbol in indices_dict.items():
        try:
            hist = yf.Ticker(symbol).history(period="2d")
            close, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
        except:
            res[name] = {"現價": 0, "漲跌幅": 0}
    return res

# 4. 抓取個股與計算技術指標 (加入 KD 歷史陣列以繪製線圖)
@st.cache_data(ttl=600)
def get_stock_advanced_data(stock_dict):
    data_list = []
    for symbol, name in stock_dict.items():
        try:
            t = yf.Ticker(f"{symbol}.TW")
            hist = t.history(period="2mo") # 拉長抓取期間以確保 KD 計算準確
            if len(hist) < 20: continue
            
            close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change_pct = ((close - prev_close) / prev_close) * 100
            
            # 多空判斷
            ma5 = hist['Close'].rolling(5).mean().iloc[-1]
            ma20 = hist['Close'].rolling(20).mean().iloc[-1]
            if close > ma5 and close > ma20: trend = "📈 多頭"
            elif close < ma5 and close < ma20: trend = "📉 空頭"
            else: trend = "🔄 整理"

            # KD 計算
            low_9 = hist['Low'].rolling(9).min()
            high_9 = hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
            k = rsv.ewm(com=2).mean()
            d = k.ewm(com=2).mean()
            
            # 抓取近 10 天的 K 值來畫圖
            k_history = k.tail(10).fillna(0).tolist()
            
            k_curr, d_curr = k.iloc[-1], d.iloc[-1]
            k_prev, d_prev = k.iloc[-2], d.iloc[-2]
            
            if k_prev < d_prev and k_curr > d_curr: kd_signal = "🔥 黃金交叉"
            elif k_prev > d_prev and k_curr < d_curr: kd_signal = "💀 死亡交叉"
            else: kd_signal = f"K:{round(k_curr,1)}"

            sign = "+" if change_pct > 0 else ""
            display_name = f"{name} ({sign}{round(change_pct, 2)}%)"

            data_list.append({
                "代號": symbol,
                "指標股": display_name,
                "漲跌數值": change_pct,
                "現價": round(close, 2),
                "多空趨勢": trend,
                "KD狀態": kd_signal,
                "KD走勢圖": k_history, # 新增的線圖資料
                "近四季EPS": round(t.info.get('trailingEps', 0) or 0, 2),
            })
        except: pass
    return pd.DataFrame(data_list)

# 5. 計算首頁的所有題材熱度
@st.cache_data(ttl=600)
def get_all_themes_summary():
    summary = []
    for theme, stocks in STOCK_DB.items():
        df = get_stock_advanced_data(stocks)
        if not df.empty:
            avg_change = df["漲跌數值"].mean()
            summary.append({"題材名稱": theme, "平均漲跌幅(%)": round(avg_change, 2)})
    summary_df = pd.DataFrame(summary)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(by="平均漲跌幅(%)", ascending=False).reset_index(drop=True)
    return summary_df

# --- 顏色設定 ---
def color_taiwan_stock(val):
    if isinstance(val, (int, float)): return ''
    if "(+" in val or "📈" in val or "🔥" in val: return 'color: #ff4b4b; font-weight: bold;'
    if "(-" in val or "📉" in val or "💀" in val: return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 介面設計 =================
st.title("台股題材動態觀測站 🚀")
tab1, tab2 = st.tabs(["📈 首頁：大盤與題材熱度", "🎯 細部題材：技術面與籌碼"])

with tab1:
    st.subheader("🌐 全球市場溫度計")
    indices_data = get_indices()
    cols = st.columns(4) # 改成 4 欄
    for idx, (name, data) in enumerate(indices_data.items()):
        cols[idx].metric(label=name, value=data["現價"], delta=f"{data['漲跌幅']}%")
    
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("🔥 今日題材熱度排行")
        with st.spinner("計算各題材資金動向中..."):
            theme_df = get_all_themes_summary()
            if not theme_df.empty:
                # 使用 Streamlit 的 Progress 視覺化
                st.dataframe(
                    theme_df,
                    column_config={
                        "平均漲跌幅(%)": st.column_config.ProgressColumn(
                            "平均漲跌幅(%)", help="族群平均漲跌幅",
                            min_value=-5, max_value=5, format="%.2f %%"
                        )
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.write("載入中...")

    with col_right:
        st.subheader("📰 題材觸發雷達")
        news_titles = get_market_news()
        matched = False
        for title in news_titles:
            for theme, keywords in THEME_KEYWORDS.items():
                if any(kw in title for kw in keywords):
                    st.error(f"🚨 觸發【{theme}】: {title}")
                    matched = True
        if not matched:
            st.info("💡 目前盤面新聞較為雜亂，未偵測到系統設定之核心題材發酵。")

with tab2:
    selected_theme = st.sidebar.selectbox("請選擇要追蹤的盤面族群", list(STOCK_DB.keys()))
    st.subheader(f"📊 {selected_theme} - 技術與基本面分析")
    
    with st.spinner(f'正在計算 {selected_theme} 的資料...'):
        df = get_stock_advanced_data(STOCK_DB[selected_theme])
        if not df.empty:
            df_display = df.drop(columns=['漲跌數值']).set_index("代號")
            styled_df = df_display.style.map(color_taiwan_stock, subset=['指標股', '多空趨勢', 'KD狀態'])
            
            # 這裡設定 KD 走勢的迷你折線圖
            st.dataframe(
                styled_df,
                column_config={
                    "KD走勢圖": st.column_config.LineChartColumn(
                        "近10日 K值走勢", y_min=0, y_max=100
                    )
                },
                use_container_width=True
            )
        else:
            st.warning("目前無法抓取資料。")
