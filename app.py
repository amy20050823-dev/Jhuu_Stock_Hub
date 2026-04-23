import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import google.generativeai as genai

st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

# 設定 Gemini API
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    pass

# 1. 題材資料庫
STOCK_DB = {
    "🤖 輝達GTC/伺服器": {"2330": "台積電", "2317": "鴻海", "2382": "廣達", "3231": "緯創", "2376": "技嘉", "6669": "緯穎", "3706": "神達"},
    "✨ CPO/光通訊": {"4979": "華星光", "3450": "聯鈞", "3081": "聯亞", "3363": "上詮", "6442": "光聖", "6451": "訊芯-KY", "3163": "波若威"},
    "🖨️ PCB/銅箔基板": {"2383": "台光電", "6213": "聯茂", "6274": "台燿", "2368": "金像電", "3037": "欣興", "8046": "南電", "3189": "景碩", "2313": "華通"},
    "⚡ 網通/石英元件": {"3042": "晶技", "3221": "台嘉碩", "8182": "加高", "2484": "希華"},
    "🧠 記憶體": {"2408": "南亞科", "2344": "華邦電", "8299": "群聯", "3260": "威剛"},
    "❄️ 散熱管理": {"3017": "奇鋐", "3324": "雙鴻", "2421": "建準", "6230": "超眾", "8996": "高力"},
    "🔌 電源供應器": {"2308": "台達電", "2301": "光寶科", "6409": "旭隼"},
    "🔋 BBU(備援電池)": {"6121": "新普", "3211": "順達", "3323": "加百裕", "6781": "AES-KY"},
    "📟 被動元件": {"2327": "國巨", "2492": "華新科", "3026": "禾伸堂"},
    "🧩 ASIC/IP矽智財": {"3443": "智原", "3661": "世芯-KY", "6643": "M31", "6533": "晶心科"},
    "⚡ 高速傳輸與介面": {"4966": "譜瑞-KY", "5269": "祥碩", "6756": "威鋒電子", "6661": "威健"},
    "📦 CoWoS/先進封裝": {"3131": "弘塑", "6187": "萬潤", "5443": "均豪", "6640": "均華", "6196": "帆宣"},
    "🛠️ 半導體耗材與檢測": {"6223": "旺矽", "6217": "中探針", "1560": "研伸", "1773": "勝一", "3583": "辛耘"},
    "🎮 邊緣運算與MCU": {"2454": "聯發科", "4919": "盛群", "2337": "旺宏"},
    "🦾 AI機器人/自動化": {"2359": "所羅門", "2365": "昆盈", "6414": "樺漢", "8374": "羅昇", "4510": "高鋒"},
    "🛰️ 低軌衛星": {"2313": "華通", "3491": "昇達科", "6271": "同欣電", "3380": "明泰"}
}

# 2. 新聞觸發關鍵字字典
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

# 初始化 Session State 來記憶 AI 分析結果 (避免切換分頁重新消耗額度)
if "ai_analysis_text" not in st.session_state:
    st.session_state.ai_analysis_text = ""

# 3. 自動抓新聞
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

# 4. 獲取大盤指數
@st.cache_data(ttl=600)
def get_indices():
    indices_dict = {"加權指數": "^TWII", "那斯達克": "^IXIC", "費半指數": "^SOX", "VIX恐慌": "^VIX"}
    res = {}
    for name, symbol in indices_dict.items():
        try:
            hist = yf.Ticker(symbol).history(period="2d")
            close, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

# --- AI 大腦分析核心函數 ---
@st.cache_data(ttl=3600)
def get_ai_market_analysis(indices_data, news_titles, theme_df):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ 請先在 Streamlit Secrets 設定 GEMINI_API_KEY，AI 才能開始運作喔！"
    try:
        available_model = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_model = m.name
                break
                
        if not available_model:
            return "⚠️ 你的 API 金鑰目前沒有綁定任何可用的文字生成模型。"

        model = genai.GenerativeModel(available_model)
        
        market_str = f"加權指數漲跌幅: {indices_data.get('加權指數', {}).get('漲跌幅', 0)}%\n"
        market_str += f"那斯達克漲跌幅: {indices_data.get('那斯達克', {}).get('漲跌幅', 0)}%\n"
        market_str += f"費半指數漲跌幅: {indices_data.get('費半指數', {}).get('漲跌幅', 0)}%\n"
        
        strong_theme = theme_df.iloc[0]['題材名稱'] if not theme_df.empty else "無"
        weak_theme = theme_df.iloc[-1]['題材名稱'] if not theme_df.empty else "無"
        market_str += f"今日最強題材: {strong_theme}\n今日最弱題材: {weak_theme}\n"
        
        news_str = "\n".join(news_titles[:15])
        
        prompt = f"""
        你現在是一位實戰經驗豐富、說話接地氣的台股操盤手。請根據我提供的【市場數據】與【國內外頭條新聞】，寫一段大約 150 字的「大盤與題材盤後分析」。
        
        請用「白話文」讓一般投資人也能輕鬆聽懂，絕對不要用太文言文或死板的學術語氣。
        你的分析必須包含兩點：
        1. 【大盤今日走勢】：解釋今天加權指數為什麼這樣走？（判斷有沒有被美股拖累/帶動，或是被什麼國內外大新聞影響）。
        2. 【題材股資金流向】：點出今天台灣盤面的資金跑去哪了？（結合我提供的最強/最弱題材，白話說明資金是在避險、觀望還是積極點火攻擊哪個族群）。

        【市場數據】
        {market_str}
        
        【國內外頭條新聞】
        {news_str}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI 大腦發生未知的連線狀況：{str(e)}"

# 5. 抓取個股與計算技術指標
@st.cache_data(ttl=600)
def get_stock_advanced_data(stock_dict):
    data_list, kdj_history_dict = [], {}
    for symbol, name in stock_dict.items():
        try:
            t = yf.Ticker(f"{symbol}.TW")
            hist = t.history(period="3mo")
            if len(hist) < 20: continue
            
            close, prev_close = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            change_pct = ((close - prev_close) / prev_close) * 100
            
            ma5, ma20 = hist['Close'].rolling(5).mean().iloc[-1], hist['Close'].rolling(20).mean().iloc[-1]
            if close > ma5 and close > ma20: trend = "📈 多頭"
            elif close < ma5 and close < ma20: trend = "📉 空頭"
            else: trend = "🔄 整理"

            low_9, high_9 = hist['Low'].rolling(9).min(), hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
            k, d = rsv.ewm(com=2).mean(), rsv.ewm(com=2).mean().ewm(com=2).mean()
            j = 3 * k - 2 * d
            
            kdj_df = pd.DataFrame({'K值': k, 'D值': d, 'J值': j}).tail(30)
            sign = "+" if change_pct > 0 else ""
            display_name = f"{name} ({sign}{round(change_pct, 2)}%)"
            
            kdj_history_dict[display_name] = kdj_df
            data_list.append({"代號": symbol, "指標股": display_name, "漲跌數值": change_pct, "現價": round(close, 2), "多空趨勢": trend, "近四季EPS": round(t.info.get('trailingEps', 0) or 0, 2)})
        except: pass
    return pd.DataFrame(data_list), kdj_history_dict

# 6. 計算首頁的所有題材熱度
@st.cache_data(ttl=600)
def get_all_themes_summary():
    summary = []
    for theme, stocks in STOCK_DB.items():
        df, _ = get_stock_advanced_data(stocks)
        if not df.empty: summary.append({"題材名稱": theme, "平均漲跌幅(%)": round(df["漲跌數值"].mean(), 2)})
    summary_df = pd.DataFrame(summary)
    if not summary_df.empty: summary_df = summary_df.sort_values(by="平均漲跌幅(%)", ascending=False).reset_index(drop=True)
    return summary_df

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
    
    st.subheader("🤖 大盤與題材盤後分析")
    
    # 建立一個按鈕，按下去才會去呼叫 AI
    if st.button("✨ 產生最新盤後解析", use_container_width=True):
        with st.spinner("AI 老手正在閱讀新聞與盤面數據，撰寫白話文解析中..."):
            news_titles = get_market_news()
            theme_df = get_all_themes_summary()
            st.session_state.ai_analysis_text = get_ai_market_analysis(indices_data, news_titles, theme_df)
    
    # 如果已經有分析結果，就顯示出來
    if st.session_state.ai_analysis_text:
        st.info(st.session_state.ai_analysis_text)
        
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("🔥 今日題材熱度排行")
        theme_df = get_all_themes_summary() # 確保不在按鈕內也能獨立顯示
        if not theme_df.empty:
            st.dataframe(theme_df, column_config={"平均漲跌幅(%)": st.column_config.ProgressColumn("平均漲跌幅(%)", min_value=-10, max_value=10, format="%.2f %%")}, use_container_width=True, hide_index=True)
    with col_right:
        st.subheader("📰 題材觸發雷達")
        news_titles = get_market_news() # 確保不在按鈕內也能獨立顯示
        matched = False
        for title in news_titles:
            for theme, keywords in THEME_KEYWORDS.items():
                if any(kw in title for kw in keywords):
                    st.error(f"🚨 觸發【{theme}】: {title}")
                    matched = True
        if not matched: st.info("💡 目前盤面新聞較為雜亂，未偵測到系統設定之核心題材發酵。")

with tab2:
    selected_theme = st.sidebar.selectbox("請選擇要追蹤的盤面族群", list(STOCK_DB.keys()))
    st.subheader(f"📊 {selected_theme} - 技術與基本面分析")
    with st.spinner(f'正在計算 {selected_theme} 的資料...'):
        df, kdj_dict = get_stock_advanced_data(STOCK_DB[selected_theme])
        if not df.empty:
            styled_df = df.drop(columns=['漲跌數值']).set_index("代號").style.map(color_taiwan_stock, subset=['指標股', '多空趨勢'])
            st.dataframe(styled_df, use_container_width=True)
            st.markdown("---")
            st.subheader("📉 個股 KDJ 互動走勢圖")
            selected_stock = st.selectbox("請選擇要查看詳細指標的個股：", df['指標股'].tolist())
            if selected_stock in kdj_dict: st.line_chart(kdj_dict[selected_stock], color=["#FFD700", "#1f77b4", "#FF4B4B"], height=300)
