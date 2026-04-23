import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 1. 網頁設定與標題
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")
st.title("台股題材動態觀測站 🚀")

# 2. 題材資料庫 (加入低軌衛星與記憶體)
STOCK_DB = {
    "🤖 輝達GTC/伺服器": ["2330", "2317", "2382", "3231", "2376", "6669", "3661", "3706"],
    "✨ CPO/光通訊": ["4979", "3450", "3081", "3363", "6442", "6451", "3163"],
    "🖨️ PCB/銅箔基板": ["2383", "6213", "6274", "2368", "3037", "8046", "3189", "2313"],
    "⚡ 網通/石英元件": ["3042", "3221", "8182", "2484"],
    "📦 CoWoS/先進封裝": ["3131", "3583", "6187", "5443", "6640", "6196"],
    "🔋 BBU(備援電池)": ["6121", "3211", "3323", "6781"],
    "🦾 AI機器人/自動化": ["2359", "2365", "6414", "8374", "4510"],
    "🔌 重電/綠能電網": ["1519", "1503", "1513", "1514", "1609"],
    "🛰️ 低軌衛星": ["2313", "3491", "6271", "3380"],
    "🧠 記憶體": ["2408", "2344", "8299", "3260"]
}

# 3. 題材關鍵字字典 (包含中英文雙語觸發條件)
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

# 4. 自動抓取新聞功能 (國內鉅亨網 + 國際 CNBC 雙引擎)
@st.cache_data(ttl=1800)
def get_market_news():
    news_list = []
    
    # [國內] 鉅亨網台股新聞
    try:
        url_tw = "https://news.cnyes.com/news/cat/tw_stock"
        res_tw = requests.get(url_tw, timeout=5)
        soup_tw = BeautifulSoup(res_tw.text, 'html.parser')
        tw_titles = [f"[國內] {t.get_text()}" for t in soup_tw.select('h3')[:10]]
        news_list.extend(tw_titles)
    except:
        pass

    # [國際] CNBC Top News (使用 RSS)
    try:
        url_global = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
        res_global = requests.get(url_global, timeout=5)
        soup_global = BeautifulSoup(res_global.text, 'xml')
        global_titles = [f"[國際] {item.title.text}" for item in soup_global.find_all('item')[:10]]
        news_list.extend(global_titles)
    except:
        pass
        
    return news_list

# --- 網站視覺化排版開始 ---

st.header("📰 即時新聞與題材觸發雷達")
with st.expander("點擊查看系統如何進行分析", expanded=True):
    st.write("系統每 30 分鐘自動掃描國內外最新新聞，並與資料庫進行字串比對，若出現高度重疊的關鍵字，將發出題材警報。")
    
    news_titles = get_market_news()
    if news_titles:
        matched_themes = set()
        for title in news_titles:
            for theme, keywords in THEME_KEYWORDS.items():
                if any(kw in title for kw in keywords):
                    st.error(f"🚨 偵測到資金題材【{theme}】: {title}")
                    matched_themes.add(theme)
        
        if not matched_themes:
            st.info("目前最新新聞未觸發系統內建之熱門題材。")
    else:
        st.error("無法抓取新聞，請稍後再試。")

st.markdown("---")

# 5. 側邊欄：手動檢驗盤面
st.sidebar.header("盤面分析工具")
selected_theme_key = st.sidebar.selectbox("請選擇要追蹤的盤面族群", list(STOCK_DB.keys()))
st.subheader(f"📊 {selected_theme_key} - 盤面動態")

# 6. 抓取股價數據邏輯
@st.cache_data(ttl=600)
def get_data(stocks):
    data_list = []
    for s in stocks:
        try:
            t = yf.Ticker(f"{s}.TW")
            hist = t.history(period="2d")
            if len(hist) >= 2:
                close = hist['Close'].iloc[-1]
                change = ((close - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                data_list.append({"股票代號": s, "現價": round(close, 2), "漲跌幅(%)": round(change, 2)})
        except:
            pass
    return pd.DataFrame(data_list)

# 7. 顯示數據與程式化操作建議
with st.spinner('正在從市場抓取最新盤面資料...'):
    df = get_data(STOCK_DB[selected_theme_key])
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        avg_change = df["漲跌幅(%)"].mean()
        st.subheader("💡 盤面小結與系統策略")
        st.write(f"目前族群平均漲跌幅: **{round(avg_change, 2)}%**")
        
        if avg_change > 2:
            st.success("🔥 族群整體轉強！資金流入跡象明顯，可尋找技術面剛突破的跟隨股。")
        elif avg_change < -2:
            st.warning("⚠️ 族群整體偏弱！即使有利多新聞也不宜隨意接刀，建議等待量縮止跌。")
        else:
            st.info("🔄 族群處於震盪整理，觀察指標股是否帶量表態。")
    else:
        st.error("目前無法抓取股價資料，請確認網路連線或稍後再試。")
