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
# 1. 页面配置 & CSS (解决顶部消失问题)
# ==========================================
st.set_page_config(
    page_title="AI Pro 交易终端 (终极版)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 强制内容置顶，去除顶部留白 */
    .block-container {
        padding-top: 1rem; 
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* 左侧列表样式优化 */
    div[data-testid="stDataFrame"] {
        font-size: 12px;
    }
    
    /* 标题样式 */
    h1 { margin-bottom: 0px; padding-bottom: 0px; }
    
    /* 右侧面板 */
    .trade-panel {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    
    /* 价格涨跌颜色 */
    .pos-val { color: #008000; font-weight: bold; }
    .neg-val { color: #d91e18; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据核心逻辑
# ==========================================

@st.cache_data(ttl=3600)
def translate_text(text):
    if not text: return ""
    try:
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except: return text 

@st.cache_data(ttl=600)
def get_nasdaq100_list():
    # 完整纳指100名单
    return [
        "NVDA", "TSLA", "AAPL", "AMD", "MSFT", "AMZN", "META", "GOOGL", "AVGO", "COST",
        "NFLX", "PEP", "LIN", "CSCO", "TMUS", "ADBE", "QCOM", "TXN", "INTU", "AMGN",
        "MU", "PDD", "INTC", "PLTR", "COIN", "MARA", "MSTR", "SMCI", "ARM", "LCID",
        "ISRG", "CMCSA", "HON", "BKNG", "AMAT", "KKR", "VRTX", "SBUX", "PANW",
        "ADP", "GILD", "LRCX", "ADI", "MELI", "MDLZ", "CTAS", "REGN", "KLAC",
        "CRWD", "SNPS", "SHW", "PYPL", "MAR", "CDNS", "CSX", "ORLY", "ASML", "NXPI",
        "CEG", "MNST", "DASH", "ROP", "FTNT", "PCAR", "CHTR", "ABNB", "AEP", "CPRT",
        "DXCM", "MCHP", "ROST", "PAYX", "FAST", "CTSH", "ODFL", "KDP", "IDXX", "EA",
        "EXC", "VRSK", "GEHC", "XEL", "AZN", "BKR", "GFS", "LULU", "TTD", "FANG",
        "WBD", "CSGP", "MRVL", "BIIB", "TEAM", "ILMN", "DDOG", "ZS", "ON", "MDB",
        "ANSS", "DLTR", "WBA", "SIRI", "ZM", "ENPH", "JD"
    ]

@st.cache_data(ttl=300)
def scan_market_full(tickers):
    data_list = []
    try:
        # 批量下载：只取最近5天数据，只为显示左侧列表和迷你图，速度最快
        df_data = yf.download(tickers, period="5d", group_by='ticker', progress=False, threads=True)
    except: return pd.DataFrame()

    for ticker in tickers:
        try:
            if len(tickers) == 1: df = df_data
            else: df = df_data[ticker]
            
            df = df.dropna()
            if len(df) < 2: continue # 只要有2天数据就显示，保证列表最全
            
            curr = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            pct = ((curr - prev) / prev)
            
            # 迷你趋势数据 (Sparkline)
            trend = df['Close'].tolist()
            
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
                "Signal": signal
            })
        except: continue
        
    return pd.DataFrame(data_list)

def get_detailed_history(ticker, period, interval):
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
# 3. 主界面布局
# ==========================================

st.title("⚡ AI 量化全能终端")

# 布局调整：左侧列表(25%) | 中间图表(55%) | 右侧分析(20%)
col_nav, col_chart, col_info = st.columns([2.5, 5.5, 2.0])

# --- 左侧：全量列表 ---
with col_nav:
    st.subheader("全市场扫描")
    tickers = get_nasdaq100_list()
    df_scan = scan_market_full(tickers)
    
    if not df_scan.empty:
        # 按代码字母排序，方便查找
        df_scan = df_scan.sort_values(by="Symbol")
        
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
            height=900, # 加高高度，显示更多
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        selected_rows = selection.selection.rows
        selected_ticker = df_scan.iloc[selected_rows[0]]["Symbol"] if selected_rows else "NVDA"
    else:
        st.error("数据加载中...")
        selected_ticker = "NVDA"

# --- 中间：专业级图表 (MACD + 动态坐标) ---
with col_chart:
    # 顶部信息栏
    hist_fast, info = get_detailed_history(selected_ticker, "1d", "5m")
    if not hist_fast.empty:
        curr = hist_fast['Close'].iloc[-1]
        prev = info.get('previousClose', curr)
        diff = curr - prev
        pct = (diff / prev) * 100
        color = "green" if diff >= 0 else "red"
        
        c1, c2 = st.columns([2, 4])
        with c1:
            st.markdown(f"## {selected_ticker}")
            st.caption(info.get('shortName', ''))
        with c2:
            st.markdown(f"<h2 style='color:{color}'>${curr:.2f} <span style='font-size:18px'>({diff:+.2f} / {pct:+.2f}%)</span></h2>", unsafe_allow_html=True)
    
    # 周期选择
    p_cols = st.columns(6)
    if 'period' not in st.session_state: st.session_state.period = '1mo'
    
    def set_p(p, i): 
        st.session_state.period = p
        st.session_state.interval = i
        
    with p_cols[0]: st.button("1天", on_click=set_p, args=('1d','5m'), use_container_width=True)
    with p_cols[1]: st.button("5天", on_click=set_p, args=('5d','15m'), use_container_width=True)
    with p_cols[2]: st.button("1月", on_click=set_p, args=('1mo','60m'), use_container_width=True)
    with p_cols[3]: st.button("日线", on_click=set_p, args=('6mo','1d'), use_container_width=True)
    with p_cols[4]: st.button("周线", on_click=set_p, args=('2y','1wk'), use_container_width=True)

    # 获取绘图数据
    period = st.session_state.get('period', '1mo')
    interval = st.session_state.get('interval', '60m')
    hist, _ = get_detailed_history(selected_ticker, period, interval)

    # --- 绘图核心逻辑 (修复：动态坐标 + MACD) ---
    if not hist.empty:
        # 计算 MACD
        macd = ta.macd(hist['Close'])
        
        # 确定 Y 轴范围 (解决“曲线太平”的问题)
        y_min = hist['Close'].min() * 0.98 # 留一点余量
        y_max = hist['Close'].max() * 1.02
        
        # 创建三行子图：价格(0.6), 成交量(0.2), MACD(0.2)
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.05, 
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=("价格趋势", "成交量", "MACD")
        )
        
        # 1. 价格主图 (山峰图 Area Chart)
        fill_color = 'rgba(0, 128, 0, 0.1)' if diff >= 0 else 'rgba(217, 30, 24, 0.1)'
        line_color = '#008000' if diff >= 0 else '#d91e18'
        
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist['Close'],
            mode='lines',
            fill='tozeroy', 
            fillcolor=fill_color,
            line=dict(color=line_color, width=2),
            name='价格'
        ), row=1, col=1)

        # 2. 成交量图
        colors = ['#008000' if c >= o else '#d91e18' for c, o in zip(hist['Close'], hist['Open'])]
        fig.add_trace(go.Bar(
            x=hist.index, y=hist['Volume'],
            marker_color=colors,
            name='成交量'
        ), row=2, col=1)

        # 3. MACD图
        if macd is not None:
            # MACD线 & 信号线
            fig.add_trace(go.Scatter(x=hist.index, y=macd.iloc[:, 0], line=dict(color='#2962FF', width=1.5), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=macd.iloc[:, 2], line=dict(color='#FF6D00', width=1.5), name='Signal'), row=3, col=1)
            # 柱状图
            hist_colors = ['#26a69a' if h >= 0 else '#ef5350' for h in macd.iloc[:, 1]]
            fig.add_trace(go.Bar(x=hist.index, y=macd.iloc[:, 1], marker_color=hist_colors, name='Hist'), row=3, col=1)

        # 布局设置 (关键：Range设定)
        fig.update_layout(
            height=700,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=False,
            xaxis_rangeslider_visible=False,
            # 强制主图 Y 轴范围，解决“太平”问题
            yaxis=dict(range=[y_min, y_max], gridcolor='#f0f0f0'),
            yaxis2=dict(gridcolor='#f0f0f0'), # Volume
            yaxis3=dict(gridcolor='#f0f0f0'), # MACD
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    # 新闻区
    st.markdown("### 📰 相关新闻 (AI 翻译)")
    news = get_news_ddg(selected_ticker)
    for item in news:
        st.markdown(f"- [{translate_text(item.get('title',''))}]({item.get('url','#')}) <span style='color:gray;font-size:12px'>{item.get('date','')[:10]}</span>", unsafe_allow_html=True)

# --- 右侧：分析面板 ---
with col_info:
    st.subheader("📊 深度分析")
    
    # 获取指标
    curr = hist['Close'].iloc[-1]
    bb = ta.bbands(hist['Close'], length=20, std=2.0)
    if bb is not None:
        support = bb.iloc[-1, 0]
        resis = bb.iloc[-1, 2]
    else:
        support = curr * 0.95
        resis = curr * 1.05

    # 1. 交易建议卡片
    st.markdown(f"""
    <div class="trade-panel">
        <h4>🤖 AI 策略</h4>
        <div style="display:flex; justify-content:space-between;">
            <span>阻力位 (Sell):</span>
            <span class="neg-val">${resis:.2f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:10px;">
            <span>现价:</span>
            <span style="font-weight:bold;">${curr:.2f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:10px;">
            <span>支撑位 (Buy):</span>
            <span class="pos-val">${support:.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. 机构评级
    target = info.get('targetMeanPrice', 0)
    rating = info.get('recommendationKey', 'none').upper().replace('_', ' ')
    
    st.markdown(f"""
    <div class="trade-panel">
        <h4>🏦 机构评级</h4>
        <div style="text-align:center; font-size:22px; font-weight:bold; color:#2962FF; margin:10px 0;">
            {rating}
        </div>
        <div style="display:flex; justify-content:space-between; font-size:13px;">
            <span>分析师目标价:</span>
            <strong>${target}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. 核心数据
    st.markdown(f"""
    <div class="trade-panel">
        <h4>📈 核心指标</h4>
        <div style="font-size:13px; line-height:2;">
            <div>市盈率 (PE): <strong>{info.get('trailingPE','N/A')}</strong></div>
            <div>市值: <strong>{info.get('marketCap',0)/1e9:.1f}B</strong></div>
            <div>52周高: <strong>{info.get('fiftyTwoWeekHigh','N/A')}</strong></div>
            <div>做空比率: <strong>{info.get('shortRatio','N/A')}</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
