import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

# 1. 題材資料庫 (升級為包含股票名稱的字典結構)
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
    "輝達GTC/伺服器": ["輝達", "NVIDIA", "伺服器", "GB200", "Nvidia", "AI chip"],
    "CPO/光通訊": ["CPO", "光通訊", "矽光子", "Photonics"],
    "PCB/銅箔基板": ["PCB", "銅箔基板", "CCL"],
    "網通/石英元件": ["網通", "石英", "WiFi 7"],
    "CoWoS/先進封裝": ["CoWoS", "先進封裝", "封測", "台積電設備"],
    "BBU(備援電池)": ["BBU", "備援電池", "電池模組"],
    "AI機器人/自動化": ["機器人", "自動化", "所羅門", "無人機"],
    "重電/綠能電網": ["重電", "電網", "綠能", "台電", "變壓器"],
    "低軌衛星": ["低軌衛星", "SpaceX", "Satellite"],
    "記憶體": ["記憶體", "DRAM", "HBM", "Micron", "Memory"]
}

# 2. 自動抓取新聞與翻譯模組
@st.cache_data(ttl=1800)
def get_market_news():
    news_list = []
    translator = GoogleTranslator(source='auto', target='zh-TW')
    
    try:
        url_tw = "https://news.cnyes.com/news/cat/tw_stock"
        res_tw = requests.get(url_tw, timeout=5)
        soup_tw = BeautifulSoup(res_tw.text, 'html.parser')
        tw_titles = [f"[國內] {t.get_text()}" for t in soup_tw.select('h3')[:10]]
        news_list.extend(tw_titles)
    except: pass

    try:
        url_cnbc = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
        res_cnbc = requests.get(url_cnbc, timeout=5)
        soup_cnbc = BeautifulSoup(res_cnbc.text, 'xml')
        for item in soup_cnbc.find_all('item')[:8]:
            eng_title = item.title.text
            try:
                zh_title = translator.translate(eng_title)
                news_list.append(f"[國際] {zh_title} (原文: {eng_title})")
            except:
                news_list.append(f"[國際] {eng_title}")
    except: pass
    return news_list

# 3. 抓取股價數據邏輯 (加入名稱映射)
@st.cache_data(ttl=600)
def get_stock_data(stock_dict):
    data_list = []
    for symbol, name in stock_dict.items():
        try:
            t = yf.Ticker(f"{symbol}.TW")
            hist = t.history(period="2d")
            if len(hist) >= 2:
                close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                change = ((close - prev_close) / prev_close) * 100
                data_list.append({"代號": symbol, "名稱": name, "現價": round(close, 2), "漲跌幅(%)": round(change, 2)})
        except: pass
    return pd.DataFrame(data_list)

@st.cache_data(ttl=600)
def get_taiex_data():
    try:
        t = yf.Ticker("^TWII")
        hist = t.history(period="2d")
        if len(hist) >= 2:
            close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = ((close - prev_close) / prev_close) * 100
            return round(close, 2), round(change, 2)
    except: return None, None

# --- 網站介面設計 ---
st.title("台股題材動態觀測站 🚀")

# 建立分頁
tab1, tab2 = st.tabs(["📈 首頁：大盤與熱門新聞", "🎯 細部題材：類股觀測"])

# ===== 分頁 1：首頁 =====
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("大盤加權指數 (^TWII)")
        taiex_close, taiex_change = get_taiex_data()
        if taiex_close:
            st.metric(label="目前點位", value=f"{taiex_close}", delta=f"{taiex_change}%")
        else:
            st.write("無法取得大盤資料")
            
    with col2:
        st.subheader("📰 題材觸發雷達")
        with st.spinner('掃描國內外最新新聞中...'):
            news_titles = get_market_news()
            if news_titles:
                matched_themes = set()
                for title in news_titles:
                    for theme, keywords in THEME_KEYWORDS.items():
                        if any(kw in title for kw in keywords):
                            st.error(f"🚨 觸發題材【{theme}】: {title}")
                            matched_themes.add(theme)
                if not matched_themes:
                    st.info("目前最新新聞未觸發系統內建之熱門題材。")

# ===== 分頁 2：細部題材觀測 =====
with tab2:
    st.sidebar.header("盤面分析工具")
    selected_theme_key = st.sidebar.selectbox("請選擇要追蹤的盤面族群", list(STOCK_DB.keys()))
    
    st.subheader(f"📊 {selected_theme_key} - 盤面動態")
    
    with st.spinner(f'正在抓取 {selected_theme_key} 個股資料...'):
        df = get_stock_data(STOCK_DB[selected_theme_key])
        
        if not df.empty:
            # 讓表格更美觀，設定 index
            df.set_index("代號", inplace=True)
            st.dataframe(df, use_container_width=True)
            
            avg_change = df["漲跌幅(%)"].mean()
            st.markdown("---")
            st.subheader("💡 盤面小結與系統策略")
            st.write(f"目前族群平均漲跌幅: **{round(avg_change, 2)}%**")
            
            if avg_change > 2:
                st.success("🔥 族群整體轉強！資金流入跡象明顯，可尋找技術面剛突破的跟隨股。")
            elif avg_change < -2:
                st.warning("⚠️ 族群整體偏弱！即使有利多新聞也不宜隨意接刀，建議等待量縮止跌。")
            else:
                st.info("🔄 族群處於震盪整理，觀察指標股是否帶量表態。")
        else:
            st.error("目前無法抓取股價資料。")
