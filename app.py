import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from duckduckgo_search import DDGS
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta

# ==========================================
# 1. 页面配置 & CSS (复刻 Investing.com 风格)
# ==========================================
st.set_page_config(
    page_title="AI Pro 交易终端",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 全局背景与字体 */
    .stApp {background-color: #ffffff;}
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    
    /* 侧边栏列表优化 */
    div[data-testid="stDataFrame"] {font-size: 13px;}
    
    /* 顶部价格大字 */
    .big-price {
        font-size: 32px;
        font-weight: 700;
        color: #000;
        margin-bottom: 0px;
    }
    .price-change-pos { color: #008000; font-size: 18px; font-weight: 600; }
    .price-change-neg { color: #d91e18; font-size: 18px; font-weight: 600; }
    
    /* 按钮样式仿造 */
    .time-btn {
        display: inline-block;
        padding: 5px 15px;
        border: 1px solid #ddd;
        border-radius: 4px;
        color: #333;
        font-size: 14px;
        margin-right: 5px;
        cursor: pointer;
    }
    
    /* 右侧交易面板卡片 */
    .trade-panel {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        background-color: #f9f9f9;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .buy-btn {
        background-color: #d91e18; 
        color: white; 
        padding: 10px; 
        text-align: center; 
        border-radius: 5px; 
        font-weight: bold;
        display: block;
    }
    .sell-btn {
        background-color: #008000; 
        color: white; 
        padding: 10px; 
        text-align: center; 
        border-radius: 5px; 
        font-weight: bold;
        display: block;
    }
    
    /* 机构评级条 */
    .rating-bar {
        height: 8px;
        background: linear-gradient(90deg, #d91e18 0%, #ffeb3b 50%, #008000 100%);
        border-radius: 4px;
        margin-top: 5px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据处理与工具函数
# ==========================================

@st.cache_data(ttl=3600)
def translate_text(text):
    if not text: return ""
    try:
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except: return text 

@st.cache_data(ttl=300)
def get_nasdaq100_list():
    return [
        "NVDA", "TSLA", "AAPL", "AMD", "MSFT", "AMZN", "META", "GOOGL", "AVGO", "COST",
        "NFLX", "PEP", "LIN", "CSCO", "TMUS", "ADBE", "QCOM", "TXN", "INTU", "AMGN",
        "MU", "PDD", "INTC", "PLTR", "COIN", "MARA", "MSTR", "SMCI", "ARM", "LCID"
    ]

@st.cache_data(ttl=60)
def scan_market_quick(tickers):
    data_list = []
    try:
        # 下载数据用于列表展示
        df_data = yf.download(tickers, period="1mo", group_by='ticker', progress=False, threads=True)
    except: return pd.DataFrame()

    for ticker in tickers:
        try:
            if len(tickers) == 1: df = df_data
            else: df = df_data[ticker]
            
            df = df.dropna()
            if len(df) < 10: continue
            
            curr = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            pct = ((curr - prev) / prev)
            
            # 迷你趋势数据
            trend = df['Close'].tail(15).tolist()
            
            # 简单信号
            rsi = df.ta.rsi(length=14).iloc[-1]
            signal = "⚪"
            if rsi < 35: signal = "🔥抄底"
            elif rsi > 75: signal = "⚠️高危"
            
            data_list.append({
                "Symbol": ticker,
                "Trend": trend,
                "Price": curr,
                "Chg": pct,
                "Signal": signal,
                "RSI": rsi 
            })
        except: continue
    return pd.DataFrame(data_list)

def get_detailed_data(ticker, period, interval):
    """获取详情页数据 + 机构信息"""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval)
    info = stock.info
    return hist, info

def get_news_ddg(ticker):
    try:
        results = DDGS().news(keywords=f"{ticker} stock news", max_results=3)
        return list(results)
    except: return []

# ==========================================
# 3. 核心界面逻辑
# ==========================================

# 布局：左侧列表(25%) | 中间图表(50%) | 右侧分析(25%)
col_list, col_chart, col_analysis = st.columns([2.5, 5.5, 2.5])

# --- 1. 左侧：股票列表 ---
with col_list:
    st.subheader("自选列表")
    tickers = get_nasdaq100_list()
    df_scan = scan_market_quick(tickers)
    
    if not df_scan.empty:
        df_scan = df_scan.sort_values(by=["Signal", "Symbol"], ascending=[False, True])
        
        selection = st.dataframe(
            df_scan,
            column_order=("Symbol", "Trend", "Price", "Chg", "Signal"),
            column_config={
                "Symbol": st.column_config.TextColumn("代码", width="small"),
                "Trend": st.column_config.LineChartColumn("走势", width="small", y_min=None, y_max=None),
                "Price": st.column_config.NumberColumn("现价", format="$%.2f", width="small"),
                "Chg": st.column_config.NumberColumn("涨跌", format="%.2f%%", width="small"),
                "Signal": st.column_config.TextColumn("信号", width="small"),
            },
            use_container_width=True,
            height=800,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        selected_rows = selection.selection.rows
        selected_ticker = df_scan.iloc[selected_rows[0]]["Symbol"] if selected_rows else "NVDA"
    else:
        selected_ticker = "NVDA"

# --- 2. 中间：专业走势图 (Area Chart) ---
with col_chart:
    # 顶部：代码与价格
    hist_fast, info = get_detailed_data(selected_ticker, "1d", "1m") # 获取最新即时数据
    if not hist_fast.empty:
        curr_price = hist_fast['Close'].iloc[-1]
        prev_close = info.get('previousClose', curr_price)
        chg_val = curr_price - prev_close
        chg_pct = (chg_val / prev_close) * 100
        
        color_class = "price-change-pos" if chg_val >= 0 else "price-change-neg"
        sign = "+" if chg_val >= 0 else ""
        
        st.markdown(f"""
        <div style="display: flex; align-items: baseline;">
            <div class="big-price">{info.get('shortName', selected_ticker)} ({selected_ticker})</div>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <div class="big-price" style="margin-right: 15px;">{curr_price:.2f}</div>
            <div class="{color_class}">{sign}{chg_val:.2f} ({sign}{chg_pct:.2f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 时间周期选择
    time_cols = st.columns([1,1,1,1,1,1,6])
    period_map = {
        "1D": ("1d", "5m"), "5D": ("5d", "15m"), "1M": ("1mo", "60m"),
        "6M": ("6mo", "1d"), "1Y": ("1y", "1wk")
    }
    
    # 默认为 1M (月线)
    if 'chart_period' not in st.session_state: st.session_state.chart_period = '1M'

    def set_period(p): st.session_state.chart_period = p
    
    with time_cols[0]: st.button("1D", on_click=set_period, args=("1D",), use_container_width=True)
    with time_cols[1]: st.button("5D", on_click=set_period, args=("5D",), use_container_width=True)
    with time_cols[2]: st.button("1M", on_click=set_period, args=("1M",), use_container_width=True)
    with time_cols[3]: st.button("6M", on_click=set_period, args=("6M",), use_container_width=True)
    with time_cols[4]: st.button("1Y", on_click=set_period, args=("1Y",), use_container_width=True)

    # 获取绘图数据
    p_param, i_param = period_map[st.session_state.chart_period]
    hist, _ = get_detailed_data(selected_ticker, p_param, i_param)
    
    # --- 绘制图表 (Plotly) ---
    # 创建双子图：主图价格，副图成交量
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.8, 0.2]
    )
    
    # 1. 主图：山峰图 (Area Chart) - 模仿Investing风格
    # 涨跌颜色判断
    fill_color = 'rgba(0, 128, 0, 0.1)' if chg_val >= 0 else 'rgba(217, 30, 24, 0.1)'
    line_color = '#008000' if chg_val >= 0 else '#d91e18'
    
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist['Close'],
        mode='lines',
        fill='tozeroy', # 填充到底部
        fillcolor=fill_color,
        line=dict(color=line_color, width=2),
        name='价格'
    ), row=1, col=1)

    # 2. 副图：成交量 (Volume)
    colors = ['#008000' if o >= c else '#d91e18' for o, c in zip(hist['Open'], hist['Close'])]
    fig.add_trace(go.Bar(
        x=hist.index, y=hist['Volume'],
        marker_color=colors,
        showlegend=False,
        name='成交量'
    ), row=2, col=1)

    # 布局美化
    fig.update_layout(
        height=550,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=False, rangeslider_visible=False),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', side='right'), # 价格轴在右侧
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 新闻模块放在图表下方
    st.markdown("### 📰 相关新闻")
    news = get_news_ddg(selected_ticker)
    if news:
        for item in news:
            st.markdown(f"**[{translate_text(item.get('title',''))}]({item.get('url','#')})**")
            st.caption(f"{item.get('date','')[:10]} | {item.get('source','Web')}")

# --- 3. 右侧：交易决策面板 ---
with col_analysis:
    st.subheader("📊 交易决策")
    
    # 计算 AI 建议价格
    curr = hist['Close'].iloc[-1]
    bb = ta.bbands(hist['Close'], length=20, std=2.0)
    if bb is not None:
        support = bb.iloc[-1, 0] # Lower
        resistance = bb.iloc[-1, 2] # Upper
    else:
        support = curr * 0.95
        resistance = curr * 1.05
    
    # 分析师数据
    target_mean = info.get('targetMeanPrice', 0)
    num_analysts = info.get('numberOfAnalystOpinions', 0)
    rec_key = info.get('recommendationKey', 'none').replace('_', ' ').upper()
    
    # === 1. AI 建议卡片 ===
    with st.container():
        st.markdown(f"""
        <div class="trade-panel">
            <h4 style="margin-top:0;">🤖 AI 策略建议</h4>
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#666;">支撑位 (Buy):</span>
                <strong>${support:.2f}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#666;">阻力位 (Sell):</span>
                <strong>${resistance:.2f}</strong>
            </div>
            <hr>
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#666;">现价:</span>
                <strong>${curr:.2f}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 简单判定
        if curr < support * 1.02:
            st.success("🔥 价格接近支撑，建议买入")
        elif curr > resistance * 0.98:
            st.error("⚠️ 价格接近阻力，建议卖出")
        else:
            st.info("⚪ 价格处于震荡区间，观望")

    # === 2. 机构评级卡片 ===
    st.write("") # Spacer
    with st.container():
        st.markdown(f"""
        <div class="trade-panel">
            <h4 style="margin-top:0;">🏦 华尔街机构评级</h4>
            <div style="text-align:center; font-size:24px; font-weight:bold; margin:10px 0;">
                {rec_key}
            </div>
            <div class="rating-bar"></div>
            <div style="display:flex; justify-content:space-between; font-size:12px; color:#666;">
                <span>卖出</span>
                <span>持有</span>
                <span>买入</span>
            </div>
            <hr>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <span>分析师目标均价:</span>
                <span style="font-weight:bold; color:#2962FF;">${target_mean if target_mean else 'N/A'}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span>评级机构数量:</span>
                <span>{num_analysts} 家</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # === 3. 基本面速览 ===
    st.write("")
    with st.container():
        pe = info.get('trailingPE', 'N/A')
        eps = info.get('trailingEps', 'N/A')
        beta = info.get('beta', 'N/A')
        
        st.markdown(f"""
        <div class="trade-panel">
            <h4 style="margin-top:0;">📈 核心数据</h4>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <div>
                    <div style="color:#888; font-size:12px;">市盈率 (PE)</div>
                    <div style="font-weight:bold;">{pe}</div>
                </div>
                <div>
                    <div style="color:#888; font-size:12px;">每股收益 (EPS)</div>
                    <div style="font-weight:bold;">{eps}</div>
                </div>
                <div>
                    <div style="color:#888; font-size:12px;">波动率 (Beta)</div>
                    <div style="font-weight:bold;">{beta}</div>
                </div>
                <div>
                    <div style="color:#888; font-size:12px;">52周最高</div>
                    <div style="font-weight:bold;">${info.get('fiftyTwoWeekHigh','N/A')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
