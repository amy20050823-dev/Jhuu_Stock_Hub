import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

# 1. 題材資料庫 (V8 終極產業鏈完整版)
STOCK_DB = {
    # --- 核心運算與網通 ---
    "🤖 輝達GTC/伺服器": {"2330": "台積電", "2317": "鴻海", "2382": "廣達", "3231": "緯創", "2376": "技嘉", "6669": "緯穎", "3706": "神達"}, # 世芯已移至矽智財
    "✨ CPO/光通訊": {"4979": "華星光", "3450": "聯鈞", "3081": "聯亞", "3363": "上詮", "6442": "光聖", "6451": "訊芯-KY", "3163": "波若威"},
    "🖨️ PCB/銅箔基板": {"2383": "台光電", "6213": "聯茂", "6274": "台燿", "2368": "金像電", "3037": "欣興", "8046": "南電", "3189": "景碩", "2313": "華通"},
    "⚡ 網通/石英元件": {"3042": "晶技", "3221": "台嘉碩", "8182": "加高", "2484": "希華"},
    "🧠 記憶體": {"2408": "南亞科", "2344": "華邦電", "8299": "群聯", "3260": "威剛"},
    
    # --- 新增：AI 硬體升級與關鍵零組件 ---
    "❄️ 散熱管理": {"3017": "奇鋐", "3324": "雙鴻", "2421": "建準", "6230": "超眾", "8996": "高力"},
    "🔌 電源供應器": {"2308": "台達電", "2301": "光寶科", "6409": "旭隼"},
    "🔋 BBU(備援電池)": {"6121": "新普", "3211": "順達", "3323": "加百裕", "6781": "AES-KY"},
    "📟 被動元件": {"2327": "國巨", "2492": "華新科", "3026": "禾伸堂"},
    
    # --- 新增：半導體上游與先進製程 ---
    "🧩 ASIC/IP矽智財": {"3443": "智原", "3661": "世芯-KY", "6643": "M31", "6533": "晶心科"},
    "⚡ 高速傳輸與介面": {"4966": "譜瑞-KY", "5269": "祥碩", "6756": "威鋒電子", "6661": "威健"},
    "📦 CoWoS/先進封裝": {"3131": "弘塑", "6187": "萬潤", "5443": "均豪", "6640": "均華", "6196": "帆宣"}, # 辛耘已移至耗材檢測
    "🛠️ 半導體耗材與檢測": {"6223": "旺矽", "6217": "中探針", "1560": "研伸", "1773": "勝一", "3583": "辛耘"},
    
    # --- 應用延伸 ---
    "🎮 邊緣運算與MCU": {"2454": "聯發科", "4919": "盛群", "2337": "旺宏"},
    "🦾 AI機器人/自動化": {"2359": "所羅門", "2365": "昆盈", "6414": "樺漢", "8374": "羅昇", "4510": "高鋒"},
    "🛰️ 低軌衛星": {"2313": "華通", "3491": "昇達科", "6271": "同欣電", "3380": "明泰"}
}

# 2. 新聞觸發關鍵字字典 (全面升級捕捉能力)
THEME_KEYWORDS = {
    "輝達GTC/伺服器": ["輝達", "NVIDIA", "伺服器", "GB200"],
    "CPO/光通訊": ["CPO", "光通訊", "矽光子"],
    "PCB/銅箔基板": ["PCB", "銅箔基板", "CCL"],
    "網通/石英元件": ["網通", "石英", "WiFi 7"],
    "記憶體": ["記憶體", "DRAM", "HBM", "Micron"],
    "散熱管理": ["散熱", "液冷", "水冷", "CDU", "Cold Plate"],
    "電源供應器": ["電源供應器", "UPS", "逆變器", "電源"],
    "BBU(備援電池)": ["BBU", "備援電池", "電池模組"],
    "被動元件": ["被動元件", "MLCC", "電容", "電感"],
    "ASIC/IP矽智財": ["ASIC", "矽智財", "IP", "客製化晶片", "RISC-V"],
    "高速傳輸與介面": ["高速傳輸", "USB 4", "PCIe", "傳輸介面"],
    "CoWoS/先進封裝": ["CoWoS", "先進封裝", "封測", "台積電設備"],
    "半導體耗材與檢測": ["探針卡", "測試探針", "再生晶圓", "濕製程", "半導體檢測"],
    "邊緣運算與MCU": ["邊緣運算", "Edge AI", "MCU", "微控制器"],
    "AI機器人/自動化": ["機器人", "自動化", "所羅門", "無人機"],
    "低軌衛星": ["低軌衛星", "SpaceX", "Satellite"]
}
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

# 2. 自動抓新聞
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

# 3. 獲取大盤指數
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

# 4. 抓取個股與計算技術指標 (回傳表格與 KDJ 歷史資料)
@st.cache_data(ttl=600)
def get_stock_advanced_data(stock_dict):
    data_list = []
    kdj_history_dict = {} # 用來儲存每檔股票完整的 KDJ 線圖資料
    
    for symbol, name in stock_dict.items():
        try:
            t = yf.Ticker(f"{symbol}.TW")
            hist = t.history(period="3mo") # 拉長到3個月確保指標平滑
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

            # 完整 K, D, J 計算
            low_9 = hist['Low'].rolling(9).min()
            high_9 = hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
            k = rsv.ewm(com=2).mean()
            d = k.ewm(com=2).mean()
            j = 3 * k - 2 * d # 計算 J 值
            
            # 儲存近 30 天的 KDJ 資料準備畫圖
            kdj_df = pd.DataFrame({'K值': k, 'D值': d, 'J值': j}).tail(30)
            
            sign = "+" if change_pct > 0 else ""
            display_name = f"{name} ({sign}{round(change_pct, 2)}%)"
            
            # 存入字典供下方圖表使用
            kdj_history_dict[display_name] = kdj_df

            data_list.append({
                "代號": symbol,
                "指標股": display_name,
                "漲跌數值": change_pct,
                "現價": round(close, 2),
                "多空趨勢": trend,
                "近四季EPS": round(t.info.get('trailingEps', 0) or 0, 2),
            })
        except: pass
    return pd.DataFrame(data_list), kdj_history_dict

# 5. 計算首頁的所有題材熱度
@st.cache_data(ttl=600)
def get_all_themes_summary():
    summary = []
    for theme, stocks in STOCK_DB.items():
        df, _ = get_stock_advanced_data(stocks)
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
    if "(+" in val or "📈" in val: return 'color: #ff4b4b; font-weight: bold;'
    if "(-" in val or "📉" in val: return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 介面設計 =================
st.title("台股題材動態觀測站 🚀")
tab1, tab2 = st.tabs(["📈 首頁：大盤與題材熱度", "🎯 細部題材：技術面與籌碼"])

with tab1:
    st.subheader("🌐 全球市場溫度計")
    indices_data = get_indices()
    cols = st.columns(4)
    for idx, (name, data) in enumerate(indices_data.items()):
        cols[idx].metric(label=name, value=data["現價"], delta=f"{data['漲跌幅']}%")
    
    st.markdown("---")
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("🔥 今日題材熱度排行")
        with st.spinner("計算各題材資金動向中..."):
            theme_df = get_all_themes_summary()
            if not theme_df.empty:
                st.dataframe(
                    theme_df,
                    column_config={
                        "平均漲跌幅(%)": st.column_config.ProgressColumn(
                            "平均漲跌幅(%)", help="族群平均漲跌幅",
                            min_value=-10, max_value=10, format="%.2f %%"
                        )
                    },
                    use_container_width=True, hide_index=True
                )
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
        df, kdj_dict = get_stock_advanced_data(STOCK_DB[selected_theme])
        if not df.empty:
            # 顯示上方表格 (拿掉原本的單線圖與KD狀態字眼)
            df_display = df.drop(columns=['漲跌數值']).set_index("代號")
            styled_df = df_display.style.map(color_taiwan_stock, subset=['指標股', '多空趨勢'])
            st.dataframe(styled_df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📉 個股 KDJ 互動走勢圖")
            
            # 下拉選單讓使用者選擇要看哪一檔股票的 KDJ
            selected_stock = st.selectbox("請選擇要查看詳細指標的個股：", df['指標股'].tolist())
            
            if selected_stock in kdj_dict:
                chart_data = kdj_dict[selected_stock]
                # 繪製多線圖，並設定自訂顏色 (K: 黃, D: 藍, J: 紅)
                st.line_chart(chart_data, color=["#FFD700", "#1f77b4", "#FF4B4B"], height=300)
                
        else:
            st.warning("目前無法抓取資料。")
