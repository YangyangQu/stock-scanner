import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from duckduckgo_search import DDGS
from deep_translator import GoogleTranslator
from datetime import datetime

# ==========================================
# 1. 页面极简配置
# ==========================================
st.set_page_config(
    page_title="AI 量化终端 Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：去除表格原本的“Excel感”，让它像一个 App 列表
st.markdown("""
<style>
    /* 隐藏默认的顶部内边距 */
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    
    /* 左侧列表美化 */
    div[data-testid="stDataFrame"] {
        border: none !important;
    }
    
    /* 指标卡片美化 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* 选中行的高亮样式优化 */
    .stDataFrame {
        font-family: 'Inter', sans-serif;
    }
    
    /* K线图容器背景 */
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
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
    return [
        "AAPL", "MSFT", "NVDA", "AVGO", "AMZN", "META", "TSLA", "GOOGL", "GOOG", "COST",
        "NFLX", "AMD", "PEP", "LIN", "CSCO", "TMUS", "ADBE", "QCOM", "TXN", "INTU",
        "AMGN", "ISRG", "CMCSA", "HON", "BKNG", "AMAT", "KKR", "VRTX", "SBUX", "PANW",
        "MU", "ADP", "PDD", "GILD", "INTC", "LRCX", "ADI", "MELI", "MDLZ", "CTAS",
        "REGN", "KLAC", "CRWD", "SNPS", "SHW", "PYPL", "MAR", "CDNS", "CSX", "ORLY",
        "ASML", "NXPI", "CEG", "MNST", "DASH", "ROP", "FTNT", "PCAR", "CHTR", "ABNB",
        "AEP", "CPRT", "DXCM", "MCHP", "ROST", "PAYX", "FAST", "CTSH", "ODFL", "KDP",
        "IDXX", "EA", "EXC", "VRSK", "GEHC", "XEL", "AZN", "BKR", "GFS", "LULU",
        "TTD", "FANG", "WBD", "CSGP", "MRVL", "BIIB", "TEAM", "ILMN", "DDOG", "ZS",
        "ON", "MDB", "ANSS", "DLTR", "WBA", "SIRI", "ZM", "ENPH", "JD", "LCID"
    ]

@st.cache_data(ttl=60)
def scan_market(tickers):
    data_list = []
    try:
        # 只拉取最后两天数据做快速扫描
        df_data = yf.download(tickers, period="5d", group_by='ticker', progress=False, threads=True)
        for ticker in tickers:
            try:
                if len(tickers) == 1: df = df_data
                else: df = df_data[ticker]
                
                df = df.dropna()
                if len(df) < 5: continue
                
                curr = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                pct = ((curr - prev) / prev)
                
                rsi = df.ta.rsi(length=14).iloc[-1]
                mfi = df.ta.mfi(length=14).iloc[-1]
                
                # 信号判断
                status = "⚪ 观望"
                if rsi < 35 or mfi < 25: status = "🔥 极佳"
                elif rsi > 70: status = "⚠️ 风险"
                elif pct > 0.03: status = "🚀 异动"
                
                data_list.append({
                    "Symbol": ticker,
                    "Price": curr,
                    "Chg%": pct,
                    "Signal": status,
                    "RSI": rsi # 用于排序，不一定显示
                })
            except: continue
    except: return pd.DataFrame()
    return pd.DataFrame(data_list)

def get_stock_data_by_timeframe(ticker, interval, period):
    """
    根据选择的时间周期获取数据
    """
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

# 布局：左侧 1/4 为列表，右侧 3/4 为详情
col_nav, col_main = st.columns([1, 3])

# --- 左侧：美化后的关注列表 ---
with col_nav:
    st.subheader("🔍 市场扫描")
    
    # 搜索框
    search_term = st.text_input("搜索代码", placeholder="如 NVDA...", label_visibility="collapsed")
    
    # 获取数据
    tickers = get_nasdaq100_list()
    df_scan = scan_market(tickers)
    
    if not df_scan.empty:
        # 排序：信号好的排前面
        df_scan = df_scan.sort_values(by=["Signal", "RSI"], ascending=[True, True])
        
        # 搜索过滤
        if search_term:
            df_scan = df_scan[df_scan['Symbol'].str.contains(search_term.upper())]

        # 🎨 使用 column_config 美化表格，让它看起来不像 Excel
        selection = st.dataframe(
            df_scan,
            column_order=("Symbol", "Price", "Chg%", "Signal"), # 只显示这几列
            column_config={
                "Symbol": st.column_config.TextColumn("代码", width="small"),
                "Price": st.column_config.NumberColumn("现价", format="$%.2f", width="small"),
                "Chg%": st.column_config.NumberColumn(
                    "涨跌", 
                    format="%.2f%%", 
                    width="small",
                ),
                "Signal": st.column_config.TextColumn("信号", width="medium"),
            },
            use_container_width=True,
            height=700,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        selected_rows = selection.selection.rows
        if selected_rows:
            selected_ticker = df_scan.iloc[selected_rows[0]]["Symbol"]
        else:
            selected_ticker = "NVDA" # 默认显示
    else:
        st.write("数据加载中...")
        selected_ticker = "NVDA"

# --- 右侧：深度分析与走势 ---
with col_main:
    # 1. 顶部：时间周期选择器 (关键更新!)
    c_header, c_timeframe = st.columns([2, 2])
    
    with c_header:
        st.markdown(f"## {selected_ticker}")
    
    with c_timeframe:
        # 🔘 时间周期切换按钮
        timeframe = st.radio(
            "选择周期:",
            ["15分钟", "1小时", "日线", "周线"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # 映射逻辑
        tf_map = {
            "15分钟": {"interval": "15m", "period": "5d"},
            "1小时": {"interval": "60m", "period": "1mo"},
            "日线": {"interval": "1d", "period": "6mo"},
            "周线": {"interval": "1wk", "period": "2y"}
        }
        params = tf_map[timeframe]

    # 获取详细数据
    info, hist = get_stock_data_by_timeframe(selected_ticker, params['interval'], params['period'])

    # 2. 核心指标栏
    m1, m2, m3, m4, m5 = st.columns(5)
    
    curr_price = hist['Close'].iloc[-1]
    prev_price = hist['Close'].iloc[-2]
    chg = curr_price - prev_price
    chg_pct = (chg / prev_price) * 100
    
    m1.metric("最新价", f"${curr_price:.2f}", f"{chg:.2f} ({chg_pct:.2f}%)")
    m2.metric("成交量", f"{hist['Volume'].iloc[-1]/1e6:.1f}M")
    m3.metric("RSI (强弱)", f"{ta.rsi(hist['Close']).iloc[-1]:.1f}")
    m4.metric("市盈率", f"{info.get('trailingPE', 0):.1f}")
    m5.metric("机构持仓", f"{info.get('heldPercentInstitutions', 0)*100:.0f}%")

    # 3. 📈 专业走势图 (带布林带)
    # 计算技术指标
    bb = ta.bbands(hist['Close'], length=20, std=2.0)
    if bb is not None:
        hist = pd.concat([hist, bb], axis=1)
        bbl = bb.columns[0]
        bbu = bb.columns[2]
    else: bbl = bbu = None

    fig = go.Figure()
    
    # K线
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist['Open'], high=hist['High'],
        low=hist['Low'], close=hist['Close'],
        name='Price'
    ))
    
    # 布林带区域 (美化: 使用填充色)
    if bbl:
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist[bbu],
            line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist[bbl],
            fill='tonexty', # 填充两条线中间的区域
            fillcolor='rgba(0, 100, 255, 0.1)',
            line=dict(width=0), showlegend=False, hoverinfo='skip',
            name='Bollinger'
        ))

    fig.update_layout(
        height=500,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_rangeslider_visible=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 4. 交易建议与新闻
    c_plan, c_news = st.columns([1, 1])
    
    with c_plan:
        st.subheader("💡 交易策略")
        # 简单策略逻辑
        atr = ta.atr(hist['High'], hist['Low'], hist['Close'], length=14).iloc[-1]
        support = hist[bbl].iloc[-1] if bbl else curr_price * 0.95
        
        buy_zone = max(support, curr_price - atr)
        stop_loss = buy_zone - atr * 1.5
        target = buy_zone + atr * 3
        
        st.info(f"""
        **建议交易计划 ({timeframe}级别):**
        
        🔵 **买入区间:** ${buy_zone:.2f} 附近
        🔴 **止损位:** ${stop_loss:.2f}
        🟢 **目标位:** ${target:.2f}
        
        *逻辑: 基于布林带支撑与 ATR 波动率*
        """)

    with c_news:
        st.subheader("📰 AI 速递")
        with st.spinner("获取中..."):
            news = get_news_ddg(selected_ticker)
            if news:
                for item in news:
                    title_zh = translate_text(item.get('title', ''))
                    link = item.get('url', '#')
                    date = item.get('date', '')[:10]
                    st.markdown(f"**[{title_zh}]({link})**")
                    st.caption(f"📅 {date} | 来源: {item.get('source', 'Web')}")
            else:
                st.write("暂无最新消息")
