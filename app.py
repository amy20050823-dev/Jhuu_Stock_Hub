import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
import io
import pdfplumber  # 💡 V86 新增：PDF 拆解神器

# ================= 1. 網頁配置 =================
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

if 'custom_themes' not in st.session_state:
    st.session_state['custom_themes'] = {}

# ================= 1.6 自動抓取中文股名 =================
def get_tw_stock_name(symbol):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find('title').text
        return title.split('(')[0].strip() if title else f"自選_{symbol}"
    except: return f"自選_{symbol}"

# ================= 3. 產業題材與 ETF 資料庫 =================
BASE_STOCK_DB = {
    "輝達GTC/AI伺服器": {"2330": "台積電", "2317": "鴻海", "2382": "廣達", "3231": "緯創", "2376": "技嘉", "6669": "緯穎", "3706": "神達", "2356": "英業達", "2422": "佳能"},
    "散熱管理/水冷": {"3017": "奇鋐", "3324": "雙鴻", "2421": "建準", "6230": "超眾", "8996": "高力", "3483": "力致", "3338": "泰碩", "3653": "健策"},
    "電源與BBU": {"2308": "台達電", "2301": "光寶科", "6409": "旭隼", "6121": "新普", "3211": "順達", "3323": "加百裕", "6781": "AES-KY", "2324": "仁寶"},
    "CoWoS/先進封裝": {"3131": "弘塑", "6187": "萬潤", "5443": "均豪", "6640": "均華", "6196": "帆宣", "3583": "辛耘", "2338": "光罩", "6515": "穎崴"}
}
STOCK_DB = {**BASE_STOCK_DB, **st.session_state['custom_themes']}
SYMBOL_TO_THEME = {sym: theme for theme, stocks in STOCK_DB.items() for sym in stocks}

ETF_DB = {
    "0050 (元大台灣50)": {"2330": {"name": "台積電", "weight": 52.5, "theme": "半導體"}, "2317": {"name": "鴻海", "weight": 8.2, "theme": "AI伺服器"}},
    "0056 (元大高股息)": {"3034": {"name": "聯詠", "weight": 4.2, "theme": "IC設計"}, "2603": {"name": "長榮", "weight": 4.1, "theme": "航運"}},
    "00981A (統一台股增長主動式)": {"2330": {"name": "台積電", "weight": 8.9, "theme": "半導體"}, "2383": {"name": "台光電", "weight": 5.2, "theme": "PCB"}},
    "00980A (野村臺灣智慧優選主動式)": {"2330": {"name": "台積電", "weight": 9.5, "theme": "半導體"}, "2317": {"name": "鴻海", "weight": 5.8, "theme": "AI伺服器"}}
}

# ================= 4. 核心抓取 =================
@st.cache_data(ttl=1800)
def get_indices():
    indices_dict = {"加權指數": "^TWII", "那斯達克": "^IXIC", "費半指數": "^SOX"}
    res = {}
    for name, symbol in indices_dict.items():
        try:
            hist = yf.Ticker(symbol).history(period="1mo")
            if not hist.empty:
                close, prev = float(hist['Close'].iloc[-1]), float(hist['Close'].iloc[-2])
                res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
            else: res[name] = {"現價": 0, "漲跌幅": 0}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

# 💡 V86 終極武器：空中攔截並解析 PDF 引擎
@st.cache_data(ttl=3600)
def parse_etf_pdf_in_memory(pdf_url):
    try:
        # 1. 偽裝瀏覽器抓取 PDF
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(pdf_url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            return pd.DataFrame([{"解析結果": f"下載失敗，網站阻擋或網址無效 (狀態碼: {res.status_code})"}])
            
        # 2. 在記憶體中解開 PDF
        with pdfplumber.open(io.BytesIO(res.content)) as pdf:
            # 掃描前兩頁尋找表格
            for page in pdf.pages[:2]:
                tables = page.extract_tables()
                for table in tables:
                    # 基礎清洗：移除全空行
                    clean_table = [row for row in table if any(cell for cell in row)]
                    if len(clean_table) > 3: # 假設超過3行的才是持股表格
                        # 將第一行設為標題
                        df = pd.DataFrame(clean_table[1:], columns=clean_table[0])
                        return df
                        
        return pd.DataFrame([{"解析結果": "成功下載 PDF，但在前兩頁找不到可辨識的持股表格。"}])
        
    except Exception as e:
        return pd.DataFrame([{"解析結果": f"系統發生錯誤：{str(e)}"}])

# ================= 5. UI 介面 =================
st.title("台股題材動態觀測站 V86 內建 PDF 爬蟲版")

tab1, tab2, tab3, tab4 = st.tabs(["📊 首頁：大盤熱度", "🔍 細部題材", "🎯 波段選股", "🛡️ ETF 戰情室 & PDF 爬蟲"])

with tab1:
    idx_data = get_indices()
    cols = st.columns(len(idx_data))
    for i, (n, d) in enumerate(idx_data.items()): cols[i].metric(n, d["現價"], f"{d['漲跌幅']}%")

with tab4:
    st.markdown("### ⚔️ ETF 籌碼對決戰情室")
    st.write("精選台股最具代表性的 ETF，觀察內建資料庫的籌碼重疊度。")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1: etf1 = st.selectbox("選擇第一檔", list(ETF_DB.keys()), index=0)
    with col_e2: etf2 = st.selectbox("選擇第二檔", list(ETF_DB.keys()), index=1)
    
    if etf1 and etf2:
        df1 = pd.DataFrame.from_dict(ETF_DB[etf1], orient='index').reset_index().rename(columns={'index':'代號'})
        df2 = pd.DataFrame.from_dict(ETF_DB[etf2], orient='index').reset_index().rename(columns={'index':'代號'})
        c1, c2 = st.columns(2)
        c1.dataframe(df1, use_container_width=True, hide_index=True)
        c2.dataframe(df2, use_container_width=True, hide_index=True)

    st.markdown("---")
    
    # 💡 V86 新增：專屬的 PDF 即時解析操作區
    st.markdown("### 🕵️‍♀️ 主動式 ETF 月報 PDF 即時解析器 (進階功能)")
    st.info("主動式 ETF 每月會於投信官網釋出 PDF 月報。將 PDF 的真實網址貼在下方，系統將在雲端拆解並嘗試抓出持股明細表！")
    
    # 給一個預設的測試網址（使用者可以自己換成投信官網找到的 PDF 網址）
    default_url = "https://www.wibibi.com/info/share/ETF_Sample_Report.pdf" # 示意網址
    pdf_url_input = st.text_input("🔗 貼上投信官網月報 PDF 網址：", "")
    
    if st.button("🚀 啟動空中攔截解析"):
        if pdf_url_input:
            with st.spinner("正在潛入投信官網、下載並拆解 PDF...（這可能需要幾秒鐘）"):
                # 呼叫我們的空中解析引擎
                df_parsed = parse_etf_pdf_in_memory(pdf_url_input)
                
                if "解析結果" in df_parsed.columns:
                    st.warning(df_parsed.iloc[0]["解析結果"])
                else:
                    st.success("🎉 解析成功！以下是從 PDF 抽出的表格數據：")
                    st.dataframe(df_parsed, use_container_width=True)
        else:
            st.error("請先貼上 PDF 網址喔！")
