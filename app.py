import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 題材資料庫 (諠諠專屬版)
STOCK_DB = {
    "🤖 輝達GTC/伺服器": ["2330", "2317", "2382", "3231", "2376", "6669", "3661", "3706"],
    "✨ CPO/AAOI 光通訊": ["4979", "3450", "3081", "3363", "6442", "6451", "3163"],
    "🖨️ PCB/CCL銅箔基板": ["2383", "6213", "6274", "2368", "3037", "8046", "3189", "2313"],
    "⚡ 網通/石英元件": ["3042", "3221", "8182", "2484"],
    "📦 CoWoS/先進封裝": ["3131", "3583", "6187", "5443", "6640", "6196"],
    "🔋 BBU(備援電池)": ["6121", "3211", "3323", "6781"],
    "🦾 AI機器人/自動化": ["2359", "2365", "6414", "8374", "4510"],
    "🔌 重電/綠能電網": ["1519", "1503", "1513", "1514", "1609"]
}

# 2. 網頁標題
st.title("諠諠的台股題材觀測站 🚀")

# 3. 側邊欄：選擇要分析的題材
selected_theme = st.sidebar.selectbox("請選擇要追蹤的題材", list(STOCK_DB.keys()))
st.subheader(f"📊 {selected_theme} - 盤面動態")

# 4. 抓取數據的邏輯
@st.cache_data(ttl=600) # 快取10分鐘，避免一直重複抓資料
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

# 5. 顯示數據與操作建議
with st.spinner('正在從市場抓取最新盤面資料...'):
    df = get_data(STOCK_DB[selected_theme])
    
    if not df.empty:
        st.dataframe(df)
        
        avg_change = df["漲跌幅(%)"].mean()
        st.subheader("💡 盤面小結與操作建議")
        st.write(f"目前族群平均漲跌幅: **{round(avg_change, 2)}%**")
        
        if avg_change > 2:
            st.success("🔥 族群整體轉強！資金流入跡象明顯，可尋找技術面剛突破的個股。")
        elif avg_change < -2:
            st.warning("⚠️ 族群整體偏弱！建議先觀望，不宜隨意接刀。")
        else:
            st.info("🔄 族群處於震盪整理，觀察指標股是否表態。")
    else:
        st.error("目前無法抓取資料，請確認網路連線或稍後再試。")
