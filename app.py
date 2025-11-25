import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from duckduckgo_search import DDGS
from deep_translator import GoogleTranslator
from datetime import datetime

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(
    page_title="AI 量化终端 Pro Max",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：极致美化
st.markdown("""
<style>
    .block-container {padding-top: 0.5rem; padding-bottom: 2rem;}
    
    /* 侧边栏列表优化 */
    div[data-testid="stDataFrame"] {
        font-size: 13px;
    }
    
    /* 指标卡片 */
    div[data-testid="stMetric"] {
        background-color: #fff;
        border: 1px solid #eee;
        border-radius: 8px;
        padding: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* 加载条颜色 */
    .stProgress > div > div > div > div {
        background-color: #ffbd45;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据处理与缓存
# ==========================================

@st.cache_data(ttl=3600)
def translate_text(text):
    if not text: return ""
    try:
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except:
        return text 

@st.cache_data(ttl=300)
def get_nasdaq100_list():
    # 完整 100 只列表
    return [
        "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AMD", "AVGO", "COST",
        "NFLX", "PEP", "LIN", "CSCO", "TMUS", "ADBE", "QCOM", "TXN", "INTU", "AMGN",
        "ISRG", "CMCSA", "HON", "BKNG", "AMAT", "KKR", "VRTX", "SBUX", "PANW", "MU",
        "ADP", "PDD", "GILD", "INTC", "LRCX", "ADI", "MELI", "MDLZ", "CTAS", "REGN",
        "KLAC", "CRWD", "SNPS", "SHW", "PYPL", "MAR", "CDNS", "CSX", "ORLY", "ASML",
        "NXPI", "CEG", "MNST", "DASH", "ROP", "FTNT", "PCAR", "CHTR", "ABNB", "AEP",
        "CPRT", "DXCM", "MCHP", "ROST", "PAYX", "FAST", "CTSH", "ODFL", "KDP", "IDXX",
        "EA", "EXC", "VRSK", "GEHC", "XEL", "AZN", "BKR", "GFS", "LULU", "TTD", "FANG",
        "WBD", "CSGP", "MRVL", "BIIB", "TEAM", "ILMN", "DDOG", "ZS", "ON", "MDB",
        "ANSS", "DLTR", "WBA", "SIRI", "ZM", "ENPH", "JD", "LCID"
    ]

@st.cache_data(ttl=300)
def scan_market_detailed(tickers):
    data_list = []
    
    # 批量下载数据 (1个月数据，用于计算指标和画迷你图)
    # 使用 threads=True 加速
    try:
        df_data = yf.download(tickers, period="1mo", group_by='ticker', progress=False, threads=True)
    except:
        return pd.DataFrame()

    for ticker in tickers:
        try:
            # 提取单只股票
            if len(tickers) == 1: df = df_data
            else: df = df_data[ticker]
            
            df = df.dropna()
            if len(df) < 20: continue
            
            # 1. 基础价格
            curr = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            pct = ((curr - prev) / prev)
            
            # 2. 技术指标
            rsi = df.ta.rsi(length=14).iloc[-1]
            mfi = df.ta.mfi(length=14).iloc[-1]
            
            # MACD
            macd = df.ta.macd(fast=12, slow=26, signal=9)
            macd_diff = macd.iloc[-1, 1] # Histogram
            macd_signal = "🟢金叉" if macd_diff > 0 else "🔴死叉"
            
            # 3. 迷你走势图数据 (Sparkline)
            # 取最近 20 天的收盘价，转为列表
            trend_data = df['Close'].tail(20).tolist()
            
            # 4. 评级信号
            signal = "⚪"
            if rsi < 35 or mfi < 25: signal = "🔥买入"
            elif rsi > 75: signal = "⚠️超买"
            elif pct > 0.03: signal = "🚀暴涨"
            
            # 5. 成交量
            vol = df['Volume'].iloc[-1]
            vol_str = f"{vol/1e6:.1f}M"

            data_list.append({
                "Symbol": ticker,
                "Trend": trend_data, # 这里的列表会被渲染成曲线图
                "Price": curr,
                "Chg": pct,
                "Signal": signal,
                "MACD": macd_signal,
                "Vol": vol_str,
                "RSI_Num": rsi # 用于排序的隐藏列
            })
        except: continue
        
    return pd.DataFrame(data_list)

def get_stock_data_by_timeframe(ticker, interval, period):
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period=period, interval=interval)
    return info, hist

def get_news_ddg(ticker):
    try:
        results = DDGS().news(keywords=f"{ticker} stock news", max_results=3)
        return list(results)
    except: return []

# ==========================================
# 3. 布局与逻辑
# ==========================================

st.title("⚡ AI 量化交易终端")

# 布局：左侧列表 (35%)，右侧详情 (65%)
col_nav, col_main = st.columns([3.5, 6.5])

# --- 左侧：超级列表 (The Super List) ---
with col_nav:
    st.subheader("🔍 市场全景 (Nasdaq 100)")
    
    with st.spinner("正在加载 100 只股票实时数据..."):
        tickers = get_nasdaq100_list()
        df_scan = scan_market_detailed(tickers)
    
    if not df_scan.empty:
        # 默认按是否有信号排序，然后按代码排
        df_scan = df_scan.sort_values(by=["Signal", "Symbol"], ascending=[False, True])
        
        # ⚡ 核心组件：配置超级表格
        selection = st.dataframe(
            df_scan,
            column_order=("Symbol", "Trend", "Price", "Chg", "Signal", "MACD", "Vol"),
            column_config={
                "Symbol": st.column_config.TextColumn("代码", width="small"),
                
                # 🔥 迷你走势图配置 (Sparkline)
                "Trend": st.column_config.LineChartColumn(
                    "近20日走势",
                    width="medium",
                    y_min=None, y_max=None, # 自动缩放
                ),
                
                "Price": st.column_config.NumberColumn("现价", format="$%.2f", width="small"),
                "Chg": st.column_config.NumberColumn(
                    "涨跌", 
                    format="%.2f%%", 
                    width="small",
                ),
                "Signal": st.column_config.TextColumn("评级", width="small"),
                "MACD": st.column_config.TextColumn("MACD", width="small"),
                "Vol": st.column_config.TextColumn("量", width="small"),
            },
            use_container_width=True,
            height=850, # 足够高以显示更多股票
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        selected_rows = selection.selection.rows
        if selected_rows:
            selected_ticker = df_scan.iloc[selected_rows[0]]["Symbol"]
        else:
            selected_ticker = "NVDA"
    else:
        st.error("数据加载失败")
        selected_ticker = "NVDA"

# --- 右侧：深度详情 ---
with col_main:
    # 顶部工具栏
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(f"## {selected_ticker}")
    with c2:
        timeframe = st.radio("周期", ["15分钟", "1小时", "日线", "周线"], horizontal=True)
        tf_map = {
            "15分钟": {"interval": "15m", "period": "5d"},
            "1小时": {"interval": "60m", "period": "1mo"},
            "日线": {"interval": "1d", "period": "6mo"},
            "周线": {"interval": "1wk", "period": "2y"}
        }

    # 获取数据
    params = tf_map[timeframe]
    info, hist = get_stock_data_by_timeframe(selected_ticker, params['interval'], params['period'])

    # 顶部指标栏
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("最新价", f"${hist['Close'].iloc[-1]:.2f}", f"{(hist['Close'].iloc[-1]-hist['Close'].iloc[-2]):.2f}")
    m2.metric("RSI (强弱)", f"{ta.rsi(hist['Close']).iloc[-1]:.1f}")
    m3.metric("MACD趋势", "Bullish" if ta.macd(hist['Close']).iloc[-1, 2] > 0 else "Bearish")
    m4.metric("成交量", f"{hist['Volume'].iloc[-1]/1e6:.1f}M")

    # 📈 主图表 (带 MACD 子图)
    # 计算指标
    bb = ta.bbands(hist['Close'], length=20, std=2.0)
    macd = ta.macd(hist['Close'])
    
    if bb is not None:
        hist = pd.concat([hist, bb], axis=1)
        bbl, bbu = bb.columns[0], bb.columns[2]
    else: bbl = bbu = None

    # 创建子图 (上图K线，下图MACD)
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=('价格走势', 'MACD'),
                        row_heights=[0.7, 0.3])

    # 1. K线图
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist['Open'], high=hist['High'],
        low=hist['Low'], close=hist['Close'], name='Price'
    ), row=1, col=1)

    # 布林带
    if bbl:
        fig.add_trace(go.Scatter(x=hist.index, y=hist[bbu], line=dict(width=0), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist[bbl], fill='tonexty', 
                                 fillcolor='rgba(0,100,255,0.1)', line=dict(width=0), 
                                 name='Bollinger'), row=1, col=1)

    # 2. MACD图
    if macd is not None:
        # MACD Line
        fig.add_trace(go.Scatter(x=hist.index, y=macd.iloc[:, 0], line=dict(color='blue', width=1), name='MACD'), row=2, col=1)
        # Signal Line
        fig.add_trace(go.Scatter(x=hist.index, y=macd.iloc[:, 2], line=dict(color='orange', width=1), name='Signal'), row=2, col=1)
        # Histogram
        colors = ['green' if val >= 0 else 'red' for val in macd.iloc[:, 1]]
        fig.add_trace(go.Bar(x=hist.index, y=macd.iloc[:, 1], marker_color=colors, name='Hist'), row=2, col=1)

    fig.update_layout(height=600, xaxis_rangeslider_visible=False, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # 新闻
    st.subheader("📰 AI 资讯速递")
    news = get_news_ddg(selected_ticker)
    if news:
        for item in news:
            st.markdown(f"**[{translate_text(item.get('title',''))}]({item.get('url','#')})**")
            st.caption(f"来源: {item.get('source','Web')} | {item.get('date','')[:10]}")
    else:
        st.write("暂无新闻")
