import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# ================= 1. 網頁配置 =================
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

# ================= 2. 📝 你的專屬大盤解析區 =================
DAILY_ANALYSIS = """
從今日整體的盤面熱度來看，市場呈現極強的「AI 產業擴散效應」。資金不再只集中在單一龍頭股，而是由上游的 IP 矽智財、高速傳輸介面，延伸到中游的 PCB 載板與散熱管理。尤其 PCB/銅箔基板板塊漲幅超過 6%，顯示 AI 伺服器規格升級帶動的零組件需求是目前最具共識的進攻方向。相比之下，記憶體族群今日表現疲軟，顯示資金流向具有明確的選擇性，投資者應優先關注高頻高速與運算核心相關題材。

在籌碼動態方面，今日盤勢呈現「內外資一致看多」的罕見格局。三大法人合計買超金額突破 500 億元，其中外資單日大幅回補超過 430 億元，這通常被視為波段攻擊的起點。伴隨大盤成交量突破兆元天量，這顯示出強烈的換手動能與追價意願，盤勢結構由原先的震盪整理正式轉向多頭掌控，不過在量能極大化後，仍需留意短線正乖離過大的修正風險。
"""

# ================= 3. 產業題材資料庫 =================
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
    "輝達GTC/伺服器": ["輝達", "NVIDIA", "伺服器", "GB200", "AI"],
    "CPO/光通訊": ["CPO", "光通訊", "矽光子"],
    "PCB/銅箔基板": ["PCB", "銅箔基板", "CCL"],
    "網通/石英元件": ["網通", "石英", "WiFi 7"],
    "記憶體": ["記憶體", "DRAM", "HBM", "Micron", "美光"],
    "散熱管理": ["散熱", "液冷", "水冷", "CDU", "Cold Plate"],
    "電源供應器": ["電源供應器", "UPS", "逆變器", "電源"],
    "BBU(備援電池)": ["BBU", "備援電池", "電池模組"],
    "被動元件": ["被動元件", "MLCC", "電容", "電感"],
    "ASIC/IP矽智財": ["ASIC", "矽智財", "IP", "客製化晶片", "RISC-V"],
    "高速傳輸與介面": ["高速傳輸", "USB 4", "PCIe", "傳輸介面"],
    "CoWoS/先進封裝": ["CoWoS", "先進封裝", "封測", "台積電設備"],
    "半導體耗材與檢測": ["探針卡", "測試探針", "再生晶圓", "濕製程", "半導體檢測"],
    "邊緣運算與MCU": ["邊緣運算", "Edge AI", "MCU", "微控制器"],
    "AI機器人/自動化": ["機器人", "自動化", "所羅門", "無人機", "自動"],
    "低軌衛星": ["低軌衛星", "SpaceX", "Satellite", "星鏈"]
}

# ================= 4. 核心抓取函數 (Google News RSS 不死版) =================
@st.cache_data(ttl=1800)
def get_market_news():
    news = []
    translator = GoogleTranslator(source='auto', target='zh-TW')
    
    # 1. 抓取國內台股新聞 (Google News RSS - 搜尋"台股 OR 股市")
    try:
        url_tw = "https://news.google.com/rss/search?q=台股+OR+股市&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        res_tw = requests.get(url_tw, timeout=5)
        soup_tw = BeautifulSoup(res_tw.text, 'xml')
        items_tw = soup_tw.find_all('item')[:20]
        # 把新聞標題後面的 "- 媒體名稱" 去掉，畫面比較乾淨
        news.extend([f"[國內] {item.title.text.split(' - ')[0]}" for item in items_tw])
    except: pass
    
    # 2. 抓取國際美股新聞 (Google News RSS - 搜尋"US stock market")
    try:
        url_us = "https://news.google.com/rss/search?q=US+stock+market&hl=en-US&gl=US&ceid=US:en"
        res_us = requests.get(url_us, timeout=5)
        soup_us = BeautifulSoup(res_us.text, 'xml')
        items_us = soup_us.find_all('item')[:10]
        for item in items_us:
            try: 
                clean_title = item.title.text.split(' - ')[0]
                translated_title = translator.translate(clean_title)
                news.append(f"[國際] {translated_title}")
            except: pass
    except: pass
    
    return news

@st.cache_data(ttl=600)
def get_indices():
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
            else: trend = "🔄 整理"
            
            vol_today = hist['Volume'].iloc[-1]
            vol_ma5 = hist['Volume'].rolling(5).mean().iloc[-1]
            if vol_today > vol_ma5 * 1.5:
                chip_status = "🔥 爆量流入"
            elif vol_today < vol_ma5 * 0.7:
                chip_status = "💧 量縮觀望"
            else:
                chip_status = "➡️ 量能平穩"

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
                "籌碼動能": chip_status, 
                "近四季EPS": eps_str
            })
        except:
            pass
            
    return pd.DataFrame(data_list), kdj_history_dict

# ================= 5. UI 視覺化與介面 =================
def color_taiwan_stock(val):
    if isinstance(val, (int, float)): return ''
    if "(+" in val or "📈" in val or "🔥" in val: return 'color: #ff4b4b; font-weight: bold;'
    if "(-" in val or "📉" in val or "💧" in val: return 'color: #00cc96; font-weight: bold;'
    return ''

st.title("台股題材動態觀測站 🚀")

st.sidebar.header("系統控制")
if st.sidebar.button("🔄 強制刷新所有數據"):
    st.cache_data.clear()
    st.rerun()

tab1, tab2 = st.tabs(["📈 首頁：大盤與題材熱度", "🎯 細部題材：技術面與籌碼"])

with tab1:
    st.subheader("🌐 全球市場溫度計")
    indices_data = get_indices()
    cols = st.columns(5)
    for idx, (name, data) in enumerate(indices_data.items()):
        cols[idx].metric(label=name, value=data["現價"], delta=f"{data['漲跌幅']}%")
    
    st.markdown("---")
    st.subheader("👨‍💻 大盤與題材盤後分析")
    st.info(DAILY_ANALYSIS)
                    
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
        
        # 顯示最新新聞清單（折疊起來讓畫面乾淨）
        with st.expander("📝 點擊查看今日最新國內外股市新聞"):
            for n in news_list:
                st.write(n)
                
        found = False
        st.markdown("### 🚨 盤面關鍵字警報")
        for n in news_list:
            for theme_name, keywords in THEME_KEYWORDS.items():
                if any(kw.lower() in n.lower() for kw in keywords):
                    st.error(f"觸發【{theme_name}】: {n}")
                    found = True
        if not found: st.info("💡 目前盤面新聞較為雜亂，未偵測到系統設定之核心題材發酵。")

with tab2:
    selected_theme = st.sidebar.selectbox("請選擇要追蹤的盤面族群", list(STOCK_DB.keys()))
    st.subheader(f"📊 {selected_theme} - 技術與籌碼分析")
    
    with st.spinner("資料載入中..."):
        df_final, kdj_all = get_stock_advanced_data(STOCK_DB[selected_theme])
        
        if not df_final.empty:
            display_df = df_final.drop(columns=['漲跌數值']).set_index("代號")
            st.dataframe(display_df.style.map(color_taiwan_stock, subset=['指標股', '多空趨勢', '籌碼動能']), use_container_width=True)
            
            st.markdown("---")
            st.subheader("📈 個股 KDJ 趨勢圖 (K:黃, D:藍, J:紅)")
            target_stock = st.selectbox("選取個股查看 KDJ：", df_final['指標股'].tolist())
            if target_stock in kdj_all:
                st.line_chart(kdj_all[target_stock], color=["#FFD700", "#1f77b4", "#FF4B4B"], height=350)
        else:
            st.warning("⚠️ 暫時無法取得該族群資料。原因可能是 Yahoo Finance 阻擋連線。")
            st.info("💡 提示：請點擊左側「🔄 強制刷新所有數據」按鈕重試。")
