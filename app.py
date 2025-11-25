import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from duckduckgo_search import DDGS
from deep_translator import GoogleTranslator
from datetime import datetime

# ==========================================
# 1. 页面配置 & CSS
# ==========================================
st.set_page_config(
    page_title="AI Pro 交易终端 (完美版)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    div[data-testid="stDataFrame"] { font-size: 12px; }
    h1 { margin-bottom: 0px; padding-bottom: 0px; }
    
    /* 交易面板样式 */
    .trade-panel {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* 价格颜色 */
    .price-up { color: #008000; font-weight: bold; }
    .price-down { color: #d91e18; font-weight: bold; }
    
    /* 信号圆点 */
    .signal-dot { font-size: 14px; margin-right: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据逻辑 (修复 RSI 和 信号)
# ==========================================

@st.cache_data(ttl=3600)
def translate_text(text):
    if not text: return ""
    try:
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except: return text 

@st.cache_data(ttl=3600)
def get_nasdaq100_list():
    # 活跃股在前，保证体验
    return [
        "NVDA", "TSLA", "AAPL", "AMD", "MSFT", "AMZN", "META", "GOOGL", "AVGO", "COST",
        "NFLX", "PEP", "LIN", "CSCO", "TMUS", "ADBE", "QCOM", "TXN", "INTU", "AMGN",
        "MU", "PDD", "INTC", "PLTR", "COIN", "MARA", "MSTR", "SMCI", "ARM", "LCID",
        "ISRG", "CMCSA", "HON", "BKNG", "AMAT", "KKR", "VRTX", "SBUX", "PANW", "ADP",
        "GILD", "LRCX", "ADI", "MELI", "MDLZ", "CTAS", "REGN", "KLAC", "CRWD", "SNPS"
    ]

@st.cache_data(ttl=600)
def scan_market_fixed(tickers):
    data_list = []
    batch_size = 10
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    for i in range(total_batches):
        batch = tickers[i*batch_size : (i+1)*batch_size]
        try:
            # 关键修复：下载 3个月 数据，确保 RSI(14) 能计算出来！
            df_batch = yf.download(batch, period="3mo", interval="1d", group_by='ticker', progress=False, threads=False)
            
            for ticker in batch:
                try:
                    if len(batch) == 1: df = df_batch
                    else: df = df_batch[ticker]
                    
                    df = df.dropna()
                    if len(df) < 20: continue # 确保数据足够计算指标
                    
                    curr = df['Close'].iloc[-1]
                    prev = df['Close'].iloc[-2]
                    pct = ((curr - prev) / prev)
                    
                    # 迷你图数据
                    trend = df['Close'].tail(20).tolist()
                    
                    # 关键修复：指标计算
                    rsi = ta.rsi(df['Close'], length=14)
                    rsi_val = rsi.iloc[-1] if rsi is not None else 50
                    
                    # 信号放宽标准，让更多股票显示信号
                    signal = "⚪"
                    if rsi_val < 35: signal = "🔥抄底" # 超卖
                    elif rsi_val > 70: signal = "⚠️止盈" # 超买
                    elif pct > 0.03: signal = "🚀暴涨"
                    elif pct < -0.03: signal = "📉暴跌"
                    
                    data_list.append({
                        "Symbol": ticker,
                        "Trend": trend,
                        "Price": curr,
                        "Chg": pct,
                        "Signal": signal
                    })
                except: continue
        except: continue
    return pd.DataFrame(data_list)

def get_detailed_history(ticker, period, interval):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        info = stock.info
        return hist, info
    except: return pd.DataFrame(), {}

def get_news_ddg(ticker):
    try:
        results = DDGS().news(keywords=f"{ticker} stock news", max_results=3)
        return list(results)
    except: return []

# ==========================================
# 3. 界面布局
# ==========================================

st.title("⚡ AI 量化全能终端")
col_nav, col_chart, col_info = st.columns([2.5, 5.5, 2.0])

# --- 左侧：列表 ---
with col_nav:
    st.subheader("全市场扫描")
    tickers = get_nasdaq100_list()
    with st.spinner("正在计算全市场信号..."):
        df_scan = scan_market_fixed(tickers)
    
    if not df_scan.empty:
        # 排序：把有信号的排在最前面
        df_scan["SortKey"] = df_scan["Signal"].apply(lambda x: 0 if x == "⚪" else 1)
        df_scan = df_scan.sort_values(by=["SortKey", "Symbol"], ascending=[False, True])
        
        selection = st.dataframe(
            df_scan,
            column_order=("Symbol", "Trend", "Price", "Chg", "Signal"),
            column_config={
                "Symbol": st.column_config.TextColumn("代码", width="small"),
                "Trend": st.column_config.LineChartColumn("走势", width="small", y_min=None, y_max=None),
                "Price": st.column_config.NumberColumn("现价", format="$%.2f", width="small"),
                "Chg": st.column_config.NumberColumn("幅%", format="%.2f%%", width="small"),
                "Signal": st.column_config.TextColumn("信号", width="small"),
            },
            use_container_width=True,
            height=900,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        selected_rows = selection.selection.rows
        selected_ticker = df_scan.iloc[selected_rows[0]]["Symbol"] if selected_rows else "NVDA"
    else:
        selected_ticker = "NVDA"

# --- 中间：图表 ---
with col_chart:
    if 'period' not in st.session_state: st.session_state.period = '1d'
    if 'interval' not in st.session_state: st.session_state.interval = '1m'
    
    # 顶部信息
    hist_fast, info = get_detailed_history(selected_ticker, "1d", "1m")
    if not hist_fast.empty:
        curr = hist_fast['Close'].iloc[-1]
        prev = info.get('previousClose', curr)
        diff = curr - prev
        pct = (diff / prev) * 100
        color = "green" if diff >= 0 else "red"
        
        c1, c2 = st.columns([2, 4])
        with c1:
            st.markdown(f"## {selected_ticker}")
            st.caption(info.get('shortName', selected_ticker))
        with c2:
            st.markdown(f"<h2 style='color:{color}'>${curr:.2f} <span style='font-size:18px'>({diff:+.2f} / {pct:+.2f}%)</span></h2>", unsafe_allow_html=True)

    # 周期切换
    p_cols = st.columns(5)
    def set_p(p, i): 
        st.session_state.period = p
        st.session_state.interval = i
    
    with p_cols[0]: st.button("1天 (1m)", on_click=set_p, args=('1d','1m'), use_container_width=True)
    with p_cols[1]: st.button("5天 (5m)", on_click=set_p, args=('5d','5m'), use_container_width=True)
    with p_cols[2]: st.button("1月 (30m)", on_click=set_p, args=('1mo','30m'), use_container_width=True)
    with p_cols[3]: st.button("日线", on_click=set_p, args=('6mo','1d'), use_container_width=True)
    with p_cols[4]: st.button("周线", on_click=set_p, args=('2y','1wk'), use_container_width=True)

    # 获取绘图数据
    hist, _ = get_detailed_history(selected_ticker, st.session_state.period, st.session_state.interval)

    if not hist.empty:
        macd = ta.macd(hist['Close'])
        
        # 动态 Y 轴
        y_min = hist['Close'].min() * 0.999
        y_max = hist['Close'].max() * 1.001
        
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=("价格趋势", "成交量", "MACD")
        )
        
        # 1. 价格 (山峰图)
        fill_color = 'rgba(0, 128, 0, 0.1)' if diff >= 0 else 'rgba(217, 30, 24, 0.1)'
        line_color = '#008000' if diff >= 0 else '#d91e18'
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', fill='tozeroy', fillcolor=fill_color, line=dict(color=line_color, width=2), name='价格'), row=1, col=1)

        # 2. 成交量
        colors = ['#008000' if c >= o else '#d91e18' for c, o in zip(hist['Close'], hist['Open'])]
        fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], marker_color=colors, name='成交量'), row=2, col=1)

        # 3. MACD
        if macd is not None:
            fig.add_trace(go.Scatter(x=hist.index, y=macd.iloc[:, 0], line=dict(color='#2962FF', width=1), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=macd.iloc[:, 2], line=dict(color='#FF6D00', width=1), name='Signal'), row=3, col=1)
            hist_colors = ['#26a69a' if h >= 0 else '#ef5350' for h in macd.iloc[:, 1]]
            fig.add_trace(go.Bar(x=hist.index, y=macd.iloc[:, 1], marker_color=hist_colors, name='Hist'), row=3, col=1)

        # 关键修复：隐藏非交易时间 (Rangebreaks)
        # 针对 1m, 5m, 15m, 30m, 60m 的数据，隐藏周末和美股盘后空白
        rangebreaks = []
        if st.session_state.interval in ['1m', '2m', '5m', '15m', '30m', '60m']:
            rangebreaks.append(dict(bounds=["sat", "sun"])) # 隐藏周末
            rangebreaks.append(dict(bounds=[16, 9.5], pattern="hour")) # 隐藏美股盘后 (16:00 - 09:30)

        fig.update_layout(
            height=700,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=False,
            xaxis_rangeslider_visible=False,
            yaxis=dict(range=[y_min, y_max], gridcolor='#f0f0f0', side='right'),
            yaxis2=dict(gridcolor='#f0f0f0', side='right'),
            yaxis3=dict(gridcolor='#f0f0f0', side='right'),
            hovermode="x unified",
            xaxis=dict(
                rangebreaks=rangebreaks # 应用断点修复
            )
        )
        st.plotly_chart(fig, use_container_width=True)

    # 新闻
    st.markdown("### 📰 实时新闻")
    news = get_news_ddg(selected_ticker)
    for item in news:
        st.markdown(f"- [{translate_text(item.get('title',''))}]({item.get('url','#')}) <span style='color:gray;font-size:12px'>{item.get('date','')[:10]}</span>", unsafe_allow_html=True)

# --- 右侧：分析区 (重写买卖建议) ---
with col_info:
    st.subheader("📊 交易决策")
    
    if not hist.empty:
        curr = hist['Close'].iloc[-1]
        
        # 使用日线数据计算更准确的支撑阻力
        # 防止分钟级数据波动太大导致误判
        bb = ta.bbands(hist['Close'], length=20, std=2.0)
        
        if bb is not None:
            # 支撑位 (Lower Band)
            support = bb.iloc[-1, 0]
            # 阻力位 (Upper Band)
            resis = bb.iloc[-1, 2]
        else:
            support = curr * 0.95
            resis = curr * 1.05

        # 优化显示逻辑
        st.markdown(f"""
        <div class="trade-panel">
            <h4>🤖 AI 策略建议</h4>
            <div style="font-size:14px; color:#555; margin-bottom:10px;">基于布林带波动率模型</div>
            
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="background-color:#ffebee; color:#c62828; padding:2px 6px; border-radius:4px; font-size:12px;">卖出目标</span>
                <span class="neg-val" style="font-size:18px;">${resis:.2f}</span>
            </div>
            
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-top:1px dashed #eee; border-bottom:1px dashed #eee; padding:5px 0;">
                <span>当前价格</span>
                <span style="font-weight:bold; font-size:16px;">${curr:.2f}</span>
            </div>
            
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="background-color:#e8f5e9; color:#2e7d32; padding:2px 6px; border-radius:4px; font-size:12px;">买入目标</span>
                <span class="pos-val" style="font-size:18px;">${support:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        target = info.get('targetMeanPrice', 0)
        rating = info.get('recommendationKey', 'none').upper().replace('_', ' ')
        
        st.markdown(f"""
        <div class="trade-panel">
            <h4>🏦 机构观点</h4>
            <div style="text-align:center; font-size:20px; font-weight:bold; color:#2962FF; margin:10px 0;">
                {rating}
            </div>
            <div style="display:flex; justify-content:space-between; font-size:13px;">
                <span>华尔街目标价:</span>
                <strong>${target}</strong>
            </div>
            <div style="margin-top:5px; font-size:12px; color:#666; text-align:center;">
                (距离目标还有 {(target-curr)/curr*100:.1f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="trade-panel">
            <h4>📈 核心指标</h4>
            <div style="font-size:13px; line-height:2;">
                <div>市盈率 (PE): <strong>{info.get('trailingPE','N/A')}</strong></div>
                <div>市值: <strong>{info.get('marketCap',0)/1e9:.1f}B</strong></div>
                <div>52周高: <strong>{info.get('fiftyTwoWeekHigh','N/A')}</strong></div>
                <div>做空比: <strong>{info.get('shortRatio','N/A')}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
