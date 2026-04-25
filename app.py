import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ================= 1. 網頁配置 =================
st.set_page_config(page_title="台股題材動態觀測站", layout="wide")

# ================= 2. 你的專屬大盤解析區 =================
DAILY_ANALYSIS = """
【今日大盤分析】
今日加權指數受到美股科技股回檔影響，早盤開低走低，但盤中可見低接買盤進駐，顯示下檔支撐依然強韌。目前市場正在觀望即將公布的通膨數據與聯準會態度，整體大盤呈現量縮震盪的整理格局。

【資金流向與籌碼觀察】
從盤面資金流向來看，先前漲多的「CPO/光通訊」族群出現獲利了結賣壓。資金明顯轉入具備防禦屬性與低基期的「半導體耗材」與「網通/石英元件」族群。建議投資朋友近期操作不宜追高，可關注籌碼出現「爆量流入」且技術面站上月線的潛力標的。
"""

# ================= 3. 產業題材與龍頭資料庫 =================
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

# 建立代號對應題材的字典 (去除表情符號，保持表格乾淨)
SYMBOL_TO_THEME = {}
for theme_full, stocks in STOCK_DB.items():
    clean_theme = theme_full.split(" ", 1)[-1] if " " in theme_full else theme_full
    for sym in stocks:
        SYMBOL_TO_THEME[sym] = clean_theme

# 龍頭加冕名單
LEADERS = ["2330", "2317", "3450", "4979", "3037", "2383", "3017", "2308", "2327", "2454", "3661"]

# ================= 4. 核心抓取與策略函數 =================
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
            t = None
            hist = pd.DataFrame()
            for suffix in [".TW", ".TWO"]:
                temp_t = yf.Ticker(f"{symbol}{suffix}")
                temp_hist = temp_t.history(period="6mo")
                if len(temp_hist) >= 60:
                    t = temp_t
                    hist = temp_hist
                    break
            
            if hist.empty or len(hist) < 60:
                continue
                
            crown = "👑 " if symbol in LEADERS else ""
            display_name = f"{crown}{name} ({symbol})"

            close = hist['Close'].iloc[-1]
            open_price = hist['Open'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change_pct = ((close - prev_close) / prev_close) * 100
            
            ma5 = hist['Close'].rolling(5).mean().iloc[-1]
            ma20 = hist['Close'].rolling(20).mean().iloc[-1]
            ma60 = hist['Close'].rolling(60).mean().iloc[-1]
            
            vol_today = hist['Volume'].iloc[-1]
            vol_prev = hist['Volume'].iloc[-2]
            vol_ma5 = hist['Volume'].rolling(5).mean().iloc[-1]
            
            inst_buy = vol_today > vol_ma5 * 1.5
            inst_sell = vol_today < vol_ma5 * 0.7
            
            obv = (np.sign(hist['Close'] - hist['Close'].shift(1)) * hist['Volume']).fillna(0).cumsum()
            obv_10ma = obv.rolling(10).mean().iloc[-1]
            
            bb_std = hist['Close'].rolling(20).std().iloc[-1]
            bb_width = (4 * bb_std) / ma20
            
            low_9 = hist['Low'].rolling(9).min()
            high_9 = hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
            k_series = rsv.ewm(com=2).mean()
            d_series = k_series.ewm(com=2).mean()
            j_series = 3 * k_series - 2 * d_series
            
            kd_k = k_series.iloc[-1]
            kd_d = d_series.iloc[-1]
            kd_golden = (k_series.iloc[-1] > d_series.iloc[-1]) and (k_series.iloc[-2] <= d_series.iloc[-2])
            
            kdj_df = pd.DataFrame({'K': k_series, 'D': d_series, 'J': j_series}).tail(30)
            kdj_history_dict[display_name] = kdj_df

            action = "⚪ 盤整觀望"
            action_priority = 99
            is_red = close > open_price
            is_black = close < open_price
            vol_up = vol_today > vol_prev
            
            if kd_k > 80 and close < ma5:
                action, action_priority = "💸 獲利了結", 6
            elif close < ma20 and (close < ma60 or inst_sell):
                action, action_priority = "🛑 賣出停損", 5
            elif close < ma20 and inst_buy:
                action, action_priority = "💎 跌破月線護盤", 2
            elif close < ma20 and close >= ma60 and not inst_sell and not inst_buy:
                action, action_priority = "🛌 守季線觀察", 8
            elif close > ma5 and close > ma20 and vol_up:
                if is_red:
                    if inst_buy and kd_golden:
                        action, action_priority = "💰 強力加碼", 1
                    elif kd_golden and not inst_buy:
                        action, action_priority = "➕ 加碼金叉", 3
                    elif kd_k > 80:
                        action, action_priority = "🔥 續抱不追高", 7
                    else:
                        action, action_priority = "🔴 試水溫", 4
                elif is_black:
                    action, action_priority = "👀 收黑開高走低 (避雷)", 10
            elif close >= ma20:
                action, action_priority = "🟢 持股", 9

            is_potential = (close > ma20) and (bb_width < 0.15) and (obv.iloc[-1] > obv_10ma)
            
            # 基本面資料抓取
            try:
                eps_val = t.info.get('trailingEps', None)
                eps_str = round(eps_val, 2) if eps_val else "N/A"
            except:
                eps_str = "N/A"
                
            try:
                yoy_val = t.info.get('revenueGrowth', None)
                yoy_str = f"{round(yoy_val * 100, 2)}%" if yoy_val else "N/A"
            except:
                yoy_str = "N/A"

            data_list.append({
                "代號": symbol, 
                "所屬題材": SYMBOL_TO_THEME.get(symbol, ""),
                "指標股": display_name, 
                "漲跌幅(%)": round(change_pct, 2), 
                "現價": round(close, 2), 
                "K值": round(kd_k, 2),
                "D值": round(kd_d, 2),
                "J值": round(j_series.iloc[-1], 2),
                "N字戰法策略": action,
                "策略權重": action_priority,
                "黑馬潛力": "🐎 爆發準備" if is_potential else "-",
                "籌碼動能": "爆量流入" if inst_buy else ("量縮觀望" if inst_sell else "量能平穩"), 
                "近四季EPS": eps_str,
                "營收YoY": yoy_str,
                "營收MoM": "N/A"
            })
        except:
            pass
            
    return pd.DataFrame(data_list), kdj_history_dict

# 顏色標示函數
def color_strategy(val):
    if isinstance(val, (int, float)): return ''
    if any(x in str(val) for x in ["💰", "➕", "💎", "🔴"]): return 'color: #ff4b4b; font-weight: bold;'
    if any(x in str(val) for x in ["🛑", "💸"]): return 'color: #00cc96; font-weight: bold;'
    if "🐎" in str(val): return 'color: #ffaa00; font-weight: bold;'
    return ''

def color_pct(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #ff4b4b; font-weight: bold;'
        if val < 0: return 'color: #00cc96; font-weight: bold;'
    return ''

# ================= 5. UI 視覺化與介面 =================
st.title("台股題材動態觀測站")

st.sidebar.header("關於 Jhuu")
st.sidebar.markdown("---")

tab1, tab2, tab3 = st.tabs(["首頁：大盤與題材", "細部題材：技術面與籌碼", "N字戰法選股系統"])

with tab1:
    st.subheader("全球市場溫度計")
    indices_data = get_indices()
    cols = st.columns(5)
    for idx, (name, data) in enumerate(indices_data.items()):
        cols[idx].metric(label=name, value=data["現價"], delta=f"{data['漲跌幅']}%")
    
    st.markdown("---")
    st.subheader("大盤與題材盤後分析")
    st.info(DAILY_ANALYSIS)
                    
    st.markdown("---")
    st.subheader("今日題材熱度排行")
    with st.spinner("計算題材熱度中..."):
        theme_summary = []
        for theme, stocks in STOCK_DB.items():
            df_t, _ = get_stock_advanced_data(stocks)
            if not df_t.empty:
                theme_summary.append({"題材名稱": theme, "平均漲跌幅(%)": round(df_t["漲跌幅(%)"].mean(), 2)})
        if theme_summary:
            sdf = pd.DataFrame(theme_summary).sort_values("平均漲跌幅(%)", ascending=False)
            st.dataframe(sdf, column_config={"平均漲跌幅(%)": st.column_config.ProgressColumn("平均漲跌幅(%)", min_value=-10, max_value=10, format="%.2f %%")}, use_container_width=True, hide_index=True)

with tab2:
    selected_theme = st.sidebar.selectbox("請選擇要追蹤的盤面族群", list(STOCK_DB.keys()))
    st.subheader(f"{selected_theme.split(' ', 1)[-1]} - 技術與籌碼分析")
    
    with st.spinner("資料載入中..."):
        df_final, kdj_all = get_stock_advanced_data(STOCK_DB[selected_theme])
        
        if not df_final.empty:
            # 隱藏不需要的欄位
            display_df = df_final.drop(columns=['策略權重', 'N字戰法策略', '黑馬潛力', '所屬題材']).set_index("代號")
            st.dataframe(display_df.style.map(color_pct, subset=['漲跌幅(%)']), use_container_width=True)
            
            st.markdown("---")
            st.subheader("個股 KDJ 趨勢圖 (K:黃, D:藍, J:紅)")
            target_stock = st.selectbox("選取個股查看 KDJ：", df_final['指標股'].tolist())
            if target_stock in kdj_all:
                st.line_chart(kdj_all[target_stock], color=["#FFD700", "#1f77b4", "#FF4B4B"], height=350)
        else:
            st.warning("暫時無法取得該族群資料。")

with tab3:
    st.subheader("N字戰法與主力黑馬掃描")
    st.markdown("整合所有題材庫股票，透過均線、布林通道與量能回測，自動給出今日買賣動作建議。優先排序『強力加碼』與『賣出警示』。")
    
    with st.spinner("系統正在全域掃描所有股票，請稍候..."):
        all_stocks_flat = {}
        for theme, stocks in STOCK_DB.items():
            all_stocks_flat.update(stocks)
            
        df_all, _ = get_stock_advanced_data(all_stocks_flat)
        
        if not df_all.empty:
            df_sorted = df_all.sort_values(by="策略權重", ascending=True).drop(columns=['策略權重']).reset_index(drop=True)
            # 重新排列欄位順序，把所屬題材放到前面
            cols = ['代號', '所屬題材', '指標股', '漲跌幅(%)', '現價', 'K值', 'D值', 'J值', 'N字戰法策略', '黑馬潛力', '籌碼動能', '近四季EPS', '營收YoY', '營收MoM']
            df_sorted = df_sorted[cols]
            
            st.dataframe(df_sorted.style.map(color_strategy, subset=['N字戰法策略', '黑馬潛力'])
                                        .map(color_pct, subset=['漲跌幅(%)']), use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 今日潛在爆發黑馬 (死魚盤準備翻身)")
            df_potential = df_all[df_all['黑馬潛力'] != "-"]
            if not df_potential.empty:
                df_potential = df_potential[cols]
                st.dataframe(df_potential.reset_index(drop=True).style.map(color_strategy, subset=['N字戰法策略', '黑馬潛力'])
                                                                      .map(color_pct, subset=['漲跌幅(%)']), use_container_width=True)
            else:
                st.info("今日無符合布林極度壓縮且主力吃貨的黑馬股。")

st.sidebar.markdown("---")
if st.sidebar.button("強制刷新所有數據"):
    st.cache_data.clear()
    st.rerun()
