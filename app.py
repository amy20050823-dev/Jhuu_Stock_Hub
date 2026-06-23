import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# ================= 1. 網頁與 CSS 配置 =================
st.set_page_config(page_title="台股動態觀測站 V2.0", layout="wide", page_icon="📈")

st.markdown("""
<style>
    .summary-card { background-color: #f8f9fa; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .metric-card { background-color: #ffffff; border-radius: 12px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; border: 1px solid #edf2f7; }
    .tag-pill { background-color: #e2e8f0; color: #4a5568; padding: 4px 10px; border-radius: 15px; font-size: 13px; margin-right: 6px; display: inline-block; }
    .tag-boss { background-color: #fef08a; color: #854d0e; font-weight: bold; }
    .tag-danger { background-color: #fee2e2; color: #991b1b; }
    .tag-safe { background-color: #dcfce3; color: #166534; }
</style>
""", unsafe_allow_html=True)

# ================= 2. 擴充版動態資料庫 =================
BASE_STOCK_DB = {
    "AI伺服器": ["2330", "2317", "2382", "3231", "2376", "6669", "3706", "2356", "2422"],
    "散熱管理/水冷": ["3017", "3324", "2421", "6230", "8996", "3483", "3338", "3653"],
    "電源與BBU": ["2308", "2301", "6409", "6121", "3211", "3323", "6781", "2324"],
    "CoWoS/先進封裝": ["3131", "6187", "5443", "6640", "6196", "3583", "2338", "6515"],
    "特用化學": ["4770", "1773", "4755", "1727", "4763", "1717", "5434", "3010"],
    "面板級封測": ["3711", "2449", "6257", "3481", "8064", "3580"],
    "CPO/矽光子": ["4979", "3450", "3081", "3363", "6442", "6451", "3163", "4908", "3234"],
    "功率元件": ["8255", "3645", "5425", "8261", "3317"]
}
LEADERS = ["2330", "2317", "2454", "3017", "2308", "3711", "3037", "3661"]

# ================= 3. 資料抓取與技術指標引擎 =================
@st.cache_data(ttl=600)
def get_global_indices():
    """抓取國際大盤與權值股指標"""
    symbols = {"加權指數": "^TWII", "櫃買指數": "^TWO", "費半指數": "^SOX", "美光(MU)": "MU", "台積電": "2330.TW", "聯發科": "2454.TW"}
    res = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if len(hist) >= 2:
                close, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                res[name] = {"現價": round(close, 2), "漲跌幅": round((close-prev)/prev*100, 2)}
            else: res[name] = {"現價": 0, "漲跌幅": 0}
        except: res[name] = {"現價": 0, "漲跌幅": 0}
    return res

@st.cache_data(ttl=1800)
def fetch_realtime_market_themes():
    """抓取即時新聞並萃取當日熱門題材關鍵字"""
    try:
        url = "https://news.google.com/rss/search?q=台股+OR+半導體+OR+法說會+OR+營收&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'xml')
        
        news_titles = [item.title.text for item in soup.find_all('item')[:15]]
        all_text = " ".join(news_titles)
        
        theme_keywords = {
            "功率元件": ["功率元件", "MOSFET", "二極體", "IGBT"],
            "CPO/矽光子": ["CPO", "矽光子", "光通訊", "聯亞", "聯鈞", "光聖"],
            "散熱與水冷": ["散熱", "水冷", "液冷", "奇鋐", "雙鴻"],
            "AI伺服器": ["AI伺服器", "GB200", "輝達", "代工", "鴻海", "廣達"],
            "電源與BBU": ["BBU", "備援電池", "電源供應", "台達電"],
            "面板級封裝": ["FOPLP", "面板級", "群創", "東捷"],
            "重電與綠能": ["重電", "電網", "華城", "中興電", "綠能"]
        }
        
        hot_themes = []
        for theme, keywords in theme_keywords.items():
            count = sum(all_text.count(kw) for kw in keywords)
            if count > 0:
                hot_themes.append({"題材": theme, "熱度": count})
                
        hot_themes = sorted(hot_themes, key=lambda x: x['熱度'], reverse=True)
        summary = f"📰 最新盤面偵測：今日新聞共掃描 15 篇。重點聚焦於「{hot_themes[0]['題材'] if hot_themes else '大盤震盪'}」相關概念。"
        
        return hot_themes[:3], summary, news_titles[:3]
    except Exception as e:
        return [], "無法取得即時新聞，請檢查網路連線或 API 狀態。", []

def calc_technical_indicators(df):
    """計算四大核心指標與標籤"""
    if len(df) < 60: return df
    
    # 1. 均線與布林通道
    df['20MA'] = df['Close'].rolling(20).mean()
    df['20STD'] = df['Close'].rolling(20).std()
    df['BB_Up'] = df['20MA'] + (df['20STD'] * 2)
    df['BB_Low'] = df['20MA'] - (df['20STD'] * 2)
    df['BB_Width'] = (df['BB_Up'] - df['BB_Low']) / df['20MA']
    
    # 2. OBV (量能)
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['OBV_10MA'] = df['OBV'].rolling(10).mean()
    df['OBV_20_High'] = df['OBV'].rolling(20).max()
    
    # 3. MACD / OSC (動能)
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    df['OSC'] = macd - signal
    
    # 4. KDJ (轉折)
    low_min = df['Low'].rolling(9).min()
    high_max = df['High'].rolling(9).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min + 1e-8) * 100
    df['K'] = rsv.ewm(com=2, adjust=False).mean()
    
    # 5. K線型態與獨立影線標籤
    df['Is_Red'] = df['Close'] > df['Open']
    total_range = (df['High'] - df['Low']).replace(0, 0.001)
    upper_shadow = df['High'] - df[['Close', 'Open']].max(axis=1)
    lower_shadow = df[['Close', 'Open']].min(axis=1) - df['Low']
    
    df['Upper_Shadow_Pct'] = upper_shadow / total_range
    df['Lower_Shadow_Pct'] = lower_shadow / total_range
    
    return df

@st.cache_data(ttl=1800)
def screen_stocks(stock_dict):
    """執行波段與潛在股篩選邏輯"""
    results = []
    
    flat_symbols = []
    for theme, symbols in stock_dict.items():
        flat_symbols.extend([f"{s}.TW" for s in symbols])
    
    # 使用 yf.download 批次下載以提升速度
    data = yf.download(list(set(flat_symbols)), period="3mo", group_by="ticker", progress=False)
    
    for theme, symbols in stock_dict.items():
        for sym in symbols:
            tkr = f"{sym}.TW"
            try:
                # 處理單一或多檔股票的 yfinance 結構差異
                df = data[tkr].copy() if len(set(flat_symbols)) > 1 else data.copy()
                df = df.dropna(subset=['Close'])
                if df.empty: continue
                
                df = calc_technical_indicators(df)
                today = df.iloc[-1]
                yesterday = df.iloc[-2]
                
                close = today['Close']
                change_pct = (close - yesterday['Close']) / yesterday['Close'] * 100
                
                # --- 獨立盤面標籤判定 ---
                tags = []
                if sym in LEADERS: tags.append('<span class="tag-pill tag-boss">👑 龍頭</span>')
                if today['Upper_Shadow_Pct'] > 0.4: tags.append('<span class="tag-pill tag-danger">🛑 上影壓力</span>')
                if today['Lower_Shadow_Pct'] > 0.4: tags.append('<span class="tag-pill tag-safe">⚓ 下方防守</span>')
                
                # --- 策略 1: 🚀 波段股 ---
                is_wave = False
                if (today['K'] > yesterday['K']) and \
                   (today['OSC'] > yesterday['OSC']) and \
                   (today['OBV'] > today['OBV_10MA']) and \
                   (today['OBV'] >= today['OBV_20_High'] * 0.95):
                    # 布林擴張或紅K突破
                    if (today['BB_Width'] > yesterday['BB_Width']) or (today['Is_Red'] and close > today['BB_Up']):
                        is_wave = True
                        
                # --- 策略 2: 🐎 潛在股 ---
                is_potential = False
                if not is_wave: # 互斥
                    if (today['BB_Width'] < 0.15) and (today['OBV'] > today['OBV_10MA']):
                        is_potential = True
                        
                strategy = ""
                if is_wave: strategy = "🚀 明日波段"
                elif is_potential: strategy = "🐎 潛在打底"
                
                if strategy:
                    results.append({
                        "代號": sym,
                        "所屬題材": theme,
                        "策略": strategy,
                        "現價": round(close, 2),
                        "漲跌幅(%)": round(change_pct, 2),
                        "盤面標籤": " ".join(tags) if tags else "-",
                    })
            except Exception as e:
                continue
                
    return pd.DataFrame(results)

# ================= 4. UI 介面設計 =================
st.title("台股動態觀測站 V2.0")

# --- 頂部大盤與龍頭看盤 ---
st.markdown("##### 🌐 全球大盤與台股龍頭")
indices = get_global_indices()
cols = st.columns(len(indices))
for i, (name, data) in enumerate(indices.items()):
    color = "#e11d48" if data['漲跌幅'] >= 0 else "#16a34a" # 台股習慣：紅漲綠跌
    arrow = "▲" if data['漲跌幅'] >= 0 else "▼"
    cols[i].markdown(f"""
    <div class="metric-card">
        <div style="color: #718096; font-size: 14px;">{name}</div>
        <div style="font-size: 22px; font-weight: bold; margin: 5px 0;">{data['現價']:,}</div>
        <div style="color: {color}; font-size: 14px; font-weight: bold;">{arrow} {abs(data['漲跌幅'])}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 核心功能 Tabs ---
tab_screener, tab_journal = st.tabs(["🎯 AI 智能選股 (波段/潛在)", "💼 資金日誌與盲點檢討"])

with tab_screener:
    st.markdown("##### 📰 今日熱門題材 (即時新聞爬蟲)")
    
    # 載入動態新聞模組
    hot_themes, summary_text, top_news = fetch_realtime_market_themes()
    
    tags_html = ""
    for i, theme in enumerate(hot_themes):
        tags_html += f'<span class="tag-pill">{i+1}. {theme["題材"]} (熱度:{theme["熱度"]})</span>'
        
    st.markdown(f"""
    <div class="summary-card">
        <span class="tag-pill tag-boss">🔥 資金與新聞熱區</span>
        {tags_html if tags_html else '<span class="tag-pill">目前無明顯集中題材</span>'}
        <p style="margin-top: 10px; font-size: 14px; color: #4a5568;">{summary_text}</p>
        <p style="margin-top: 5px; font-size: 12px; color: #718096;">頭條直擊：{top_news[0] if top_news else '今日無重大快訊'}</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("系統正在執行 KDJ/OSC/OBV 交叉比對演算中... (資料量較大請稍候)"):
        df_screener = screen_stocks(BASE_STOCK_DB)
        
    if not df_screener.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🚀 明日波段表態股")
            st.caption("動能轉強、OBV創高、布林通道開花突破")
            df_wave = df_screener[df_screener['策略'] == "🚀 明日波段"]
            if not df_wave.empty:
                st.write(df_wave[['代號', '所屬題材', '現價', '漲跌幅(%)', '盤面標籤']].to_html(escape=False, index=False), unsafe_allow_html=True)
            else:
                st.info("今日無符合標準之強勢波段股。")
                
        with col2:
            st.markdown("### 🐎 潛在黑馬觀察股")
            st.caption("基本面佳、布林極度壓縮、主力暗中吸籌")
            df_pot = df_screener[df_screener['策略'] == "🐎 潛在打底"]
            if not df_pot.empty:
                st.write(df_pot[['代號', '所屬題材', '現價', '漲跌幅(%)', '盤面標籤']].to_html(escape=False, index=False), unsafe_allow_html=True)
            else:
                st.info("今日無符合標準之壓縮潛在股。")
    else:
        st.warning("今日大盤動能不足，所有追蹤標的皆未達系統觸發標準。")

with tab_journal:
    col_asset, col_log = st.columns([1, 2])
    
    with col_asset:
        st.markdown("#### 💰 資金水位配置")
        # 模擬圓餅圖資料
        labels = ['現金 (子彈)', 'CPO/矽光子', '電源與BBU']
        values = [40, 35, 25]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker_colors=['#e2e8f0', '#3b82f6', '#f59e0b'])])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig, use_container_width=True)
        
    with col_log:
        st.markdown("#### 📝 新增交易日誌")
        with st.form("trade_log"):
            row1_1, row1_2, row1_3 = st.columns(3)
            ticker = row1_1.text_input("股票代號")
            action = row1_2.selectbox("動作", ["買進", "賣出"])
            price = row1_3.number_input("成交價", min_value=0.0)
            
            reason = st.multiselect("進/出場理由", ["🚀 波段訊號觸發", "🐎 黑馬低檔埋伏", "新聞強勢題材", "🛑 破線停損", "達到停利點"])
            notes = st.text_area("覆盤備註 (寫下當時的情緒或判斷)")
            
            if st.form_submit_button("記錄交易"):
                st.success(f"已記錄 {ticker} 的交易！(此為 UI 展示，資料暫未寫入資料庫)")

    st.markdown("---")
    st.markdown("#### 🤖 AI 交易盲點診斷 (Demo)")
    st.info("""
    **本月交易覆盤分析：**
    * **勝率分析：** 過去一個月波段股操作勝率 65%，表現優異。但「潛在黑馬股」勝率僅 30%。
    * **AI 診斷：** 系統比對進出點發現，妳在黑馬股的操作上，常在布林通道尚未出量突破時就提早進場，導致資金卡住缺乏效率。
    * **改進建議：** 下次面對「🐎 潛在股」，請嚴格等待觸發爆量且突破上軌的第一天再出手。
    """)
