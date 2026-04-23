import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 1. 網頁設定與標題 (改成公開專業版名稱)
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")
st.title("台股題材動態觀測站 🚀")

# 2. 題材資料庫
STOCK_DB = {
    "🤖 輝達GTC/伺服器": ["2330", "2317", "2382", "3231", "2376", "6669", "3661", "3706"],
    "✨ CPO/光通訊": ["4979", "3450", "3081", "3363", "6442", "6451", "3163"],
    "🖨️ PCB/銅箔基板": ["2383", "6213", "6274", "2368", "3037", "8046", "3189", "2313"],
    "⚡ 網通/石英元件": ["3042", "3221", "8182", "2484"],
    "📦 CoWoS/先進封裝": ["3131", "3583", "6187", "5443", "6640", "6196"],
    "🔋 BBU(備援電池)": ["6121", "3211", "3323", "6781"],
    "🦾 AI機器人/自動化": ["2359", "2365", "6414", "8374", "4510"],
    "🔌 重電/綠能電網": ["1519", "1503", "1513", "1514", "1609"]
}

# 這是這次優化的核心：新聞關鍵字字典
THEME_KEYWORDS = {
    "輝達GTC/伺服器": ["輝達", "NVIDIA", "伺服器", "AI伺服器", "GB200"],
    "CPO/光通訊": ["CPO", "光通訊", "矽光子"],
    "PCB/銅箔基板": ["PCB", "銅箔基板", "CCL"],
    "網通/石英元件": ["網通", "石英", "WiFi 7"],
    "CoWoS/先進封裝": ["CoWoS", "先進封裝", "封測", "台積電設備"],
    "BBU(備援電池)": ["BBU", "備援電池", "電池模組"],
    "AI機器人/自動化": ["機器人", "自動化", "所羅門", "無人機"],
    "重電/綠能電網": ["重電", "電網", "綠能", "台電", "變壓器"]
}

# 3. 自動抓取新聞功能 (爬蟲模組)
@st.cache_data(ttl=1800) # 每 30 分鐘才重新抓一次，避免資源消耗過度
def get_market_news():
    url = "https://news.cnyes.com/news/cat/tw_stock"
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 抓取鉅亨網的標題
        titles = [t.get_text() for t in soup.select('h3')[:20]]
        return titles
    except:
        return []

# --- 網站視覺化排版開始 ---

st.header("📰 即時新聞與題材觸發雷達")
with st.expander("點擊查看系統如何進行分析", expanded=True):
    st.write("系統每 30 分鐘自動掃描市場最新 20 則新聞，並與資料庫進行字串比對，若出現高度重疊的關鍵字，將發出題材警報。")
    
    news_titles = get_market_news()
    if news_titles:
        matched_themes = set()
        for title in news_titles:
            for theme, keywords in THEME_KEYWORDS.items():
                if any(kw in title for kw in keywords):
                    # 只要標題命中關鍵字，就跳出警示區塊
                    st.error(f"🚨 偵測到資金題材【{theme}】: {title}")
                    matched_themes.add(theme)
        
        if not matched_themes:
            st.info("目前最新新聞未觸發系統內建之熱門題材。")
    else:
        st.error("無法抓取新聞，請稍後再試。")

st.markdown("---")

# 4. 側邊欄：手動檢驗盤面
st.sidebar.header("盤面分析工具")
selected_theme_key = st.sidebar.selectbox("請選擇要追蹤的盤面族群", list(STOCK_DB.keys()))
st.subheader(f"📊 {selected_theme_key} - 盤面動態")

# 5. 抓取股價數據邏輯
@st.cache_data(ttl=600) # 股價每 10 分鐘更新一次
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

# 6. 顯示數據與程式化操作建議
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
