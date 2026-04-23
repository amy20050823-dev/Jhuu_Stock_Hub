import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import json

# ================= 1. 網頁配置與初始化 =================
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

if "ai_analysis_text" not in st.session_state:
    st.session_state.ai_analysis_text = ""

# ================= 2. 產業題材資料庫 =================
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

# ================= 3. 核心抓取函數 =================
@st.cache_data(ttl=1800)
def get_market_news():
    news = []
    translator = GoogleTranslator(source='auto', target='zh-TW')
    try:
        soup = BeautifulSoup(requests.get("https://news.cnyes.com/news/cat/tw_stock", timeout=5).text, 'html.parser')
        news.extend([f"[國內] {t.get_text()}" for t in soup.select('h3')[:20]])
    except: pass
    try:
        soup = BeautifulSoup(requests.get("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", timeout=5).text, 'xml')
        for item in soup.find_all('item')[:15]:
            try: news.append(f"[國際] {translator.translate(item.title.text)}")
            except: pass
    except: pass
    return news

@st.cache_data(ttl=600)
def get_indices():
    # 這裡加上了 WTI原油 (CL=F)
    indices_dict = {"加權指數": "^TWII", "那斯達克": "^IXIC", "費半指數": "^SOX", "VIX恐慌": "^VIX", "WTI原油": "CL=F"}
    res = {}
    for name, symbol in indices_dict.items():
        try:
            hist = yf.Ticker(symbol).history(period="2d")
            if len(hist) >= 2:
                close, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
            else: res[name] = {"現價": 0, "漲跌幅": 0}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

@st.cache_data(ttl=600)
def get_stock_advanced_data(stock_dict):
    data_list = []
    kdj_history_dict = {}
    for symbol, name in stock_dict.items():
        try:
            t = yf.Ticker(f"{symbol}.TW")
            hist = t.history(period="3mo")
            if len(hist) < 20: continue
            
            close, prev_close = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            change_pct = ((close - prev_close) / prev_close) * 100
            
            ma5 = hist['Close'].rolling(5).mean().iloc[-1]
            ma20 = hist['Close'].rolling(20).mean().iloc[-1]
            if close > ma5 and close > ma20: trend = "📈 多頭"
            elif close < ma5 and close < ma20: trend = "📉 空頭"
            else: trend = "整理"

            low_9 = hist['Low'].rolling(9).min()
            high_9 = hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
            k = rsv.ewm(com=2).mean()
            d = k.ewm(com=2).mean()
            j = 3 * k - 2 * d
            
            kdj_df = pd.DataFrame({'K': k, 'D': d, 'J': j}).tail(30)
            sign = "+" if change_pct > 0 else ""
            display_name = f"{name} ({sign}{round(change_pct, 2)}%)"
            kdj_history_dict[display_name] = kdj_df
            
            try:
                eps_val = t.info.get('trailingEps', None)
                eps_str = round(eps_val, 2) if eps_val else "N/A"
            except:
                eps_str = "N/A"

            data_list.append({
                "代號": symbol, 
                "指標股": display_name, 
                "漲跌數值": change_pct, 
                "現價": round(close, 2), 
                "多空趨勢": trend, 
                "近四季EPS": eps_str
            })
        except:
            pass
            
    return pd.DataFrame(data_list), kdj_history_dict

# ================= 4. UI 視覺化與介面 =================
def color_taiwan_stock(val):
    if isinstance(val, (int, float)): return ''
    if "(+" in val or "📈" in val: return 'color: #ff4b4b; font-weight: bold;'
    if "(-" in val or "📉" in val: return 'color: #00cc96; font-weight: bold;'
    return ''

st.title("台股題材動態觀測站 🚀")

st.sidebar.header("系統控制")
if st.sidebar.button("🔄 強制刷新所有數據"):
    st.cache_data.clear()
    st.session_state.ai_analysis_text = ""
    st.rerun()

tab1, tab2 = st.tabs(["首頁：大盤與題材熱度", "技術面分析"])

with tab1:
    st.subheader("全球市場指數")
    indices_data = get_indices()
    # 這裡改成 5 欄來容納原油
    cols = st.columns(5)
    for idx, (name, data) in enumerate(indices_data.items()):
        cols[idx].metric(label=name, value=data["現價"], delta=f"{data['漲跌幅']}%")
    
    st.markdown("---")
    st.subheader("大盤與題材盤後分析")
    
    manual_input = st.text_area("手動輸入盤後日誌：", value=st.session_state.ai_analysis_text)
    if manual_input != st.session_state.ai_analysis_text:
        st.session_state.ai_analysis_text = manual_input
    
    if st.button("呼叫 AI 產生最新盤後解析", use_container_width=True):
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ 請先在 Secrets 設定 GEMINI_API_KEY")
        else:
            with st.spinner("AI 正在撰寫分析中 (直接連線模式)..."):
                try:
                    news_titles = get_market_news()
                    theme_summary = []
                    for theme, stocks in STOCK_DB.items():
                        df_t, _ = get_stock_advanced_data(stocks)
                        if not df_t.empty:
                            theme_summary.append({"題材": theme, "平均漲跌": round(df_t["漲跌數值"].mean(), 2)})
                    df_theme_ai = pd.DataFrame(theme_summary).sort_values("平均漲跌", ascending=False) if theme_summary else pd.DataFrame()
                    
                    prompt = f"你是專業台股分析師。根據數據寫150字盤後分析。絕對禁止問候語與語助詞。大盤：{indices_data.get('加權指數',{}).get('漲跌幅',0)}%。強弱題材：{df_theme_ai.head(1)['題材'].values if not df_theme_ai.empty else '無'} / {df_theme_ai.tail(1)['題材'].values if not df_theme_ai.empty else '無'}。新聞：{news_titles[:10]}。分兩段：【大盤分析】、【資金流向】。"
                    
                    # 使用原始的 HTTP 請求繞過套件報錯
                    api_key = st.secrets["GEMINI_API_KEY"]
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    headers = {'Content-Type': 'application/json'}
                    
                    response = requests.post(url, json=payload, headers=headers)
                    result_data = response.json()
                    
                    if "candidates" in result_data:
                        st.session_state.ai_analysis_text = result_data["candidates"][0]["content"]["parts"][0]["text"]
                        st.rerun() 
                    else:
                        st.error(f"Google 伺服器回傳異常：{result_data}")
                        
                except Exception as e:
                    st.error(f"連線徹底失敗，請確認 API 金鑰：{str(e)}")
                    
    st.markdown("---")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("🔥 今日題材熱度排行")
        with st.spinner("計算題材熱度中..."):
            theme_summary = []
            for theme, stocks in STOCK_DB.items():
                df_t, _ = get_stock_advanced_data(stocks)
                if not df_t.empty:
                    theme_summary.append({"題材名稱": theme, "平均漲跌幅(%)": round(df_t["漲跌數值"].mean(), 2)})
            if theme_summary:
                sdf = pd.DataFrame(theme_summary).sort_values("平均漲跌幅(%)", ascending=False)
                st.dataframe(sdf, column_config={"平均漲跌幅(%)": st.column_config.ProgressColumn("平均漲跌幅(%)", min_value=-10, max_value=10, format="%.2f %%")}, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ 暫時無法抓取盤面資料，請點擊左側『強制刷新』。")
                
    with col_r:
        st.subheader("📰 題材觸發雷達")
        news_list = get_market_news()
        found = False
        for n in news_list:
            for theme_name, keywords in THEME_KEYWORDS.items():
                if any(kw in n for kw in keywords):
                    st.error(f"🚨 觸發【{theme_name}】: {n}")
                    found = True
        if not found: st.info("目前無明顯題材觸發。")

with tab2:
    selected_theme = st.sidebar.selectbox("請選擇要追蹤的盤面族群", list(STOCK_DB.keys()))
    st.subheader(f"📊 {selected_theme} - 技術與基本面分析")
    
    with st.spinner("資料載入中..."):
        df_final, kdj_all = get_stock_advanced_data(STOCK_DB[selected_theme])
        
        if not df_final.empty:
            display_df = df_final.drop(columns=['漲跌數值']).set_index("代號")
            st.dataframe(display_df.style.map(color_taiwan_stock, subset=['指標股', '多空趨勢']), use_container_width=True)
            
            st.markdown("---")
            st.subheader("📈 個股 KDJ 趨勢圖 (K:黃, D:藍, J:紅)")
            target_stock = st.selectbox("選取個股查看 KDJ：", df_final['指標股'].tolist())
            if target_stock in kdj_all:
                st.line_chart(kdj_all[target_stock], color=["#FFD700", "#1f77b4", "#FF4B4B"], height=350)
        else:
            st.warning("⚠️ 暫時無法取得該族群資料。原因可能是 Yahoo Finance 阻擋連線。")
            st.info("💡 提示：請點擊左側「🔄 強制刷新所有數據」按鈕重試。")
