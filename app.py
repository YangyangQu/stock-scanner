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
    page_title="AI Pro 交易终端 (机构版)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 100%; }
    div[data-testid="stDataFrame"] { font-size: 12px; }
    h1 { margin-bottom: 0px; padding-bottom: 0px; }
    
    .trade-panel {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
    }
    
    .price-up { color: #008000; font-weight: 700; font-size: 18px; }
    .price-down { color: #d91e18; font-weight: 700; font-size: 18px; }
    .price-neutral { color: #333333; font-weight: 700; font-size: 16px; }
    
    .label-buy { background-color: #e8f5e9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }
    .label-sell { background-color: #ffebee; color: #c62828; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }
    
    /* 进度条样式 */
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据逻辑
# ==========================================

@st.cache_data(ttl=3600)
def translate_text(text):
    if not text: return ""
    try:
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except: return text 

@st.cache_data(ttl=3600)
def get_nasdaq100_list():
    return [
        "NVDA", "TSLA", "AAPL", "AMD", "MSFT", "AMZN", "META", "GOOGL", "AVGO", "COST",
        "NFLX", "PEP", "LIN", "CSCO", "TMUS", "ADBE", "QCOM", "TXN", "INTU", "AMGN",
        "MU", "PDD", "INTC", "PLTR", "COIN", "MARA", "MSTR", "SMCI", "ARM", "LCID",
        "ISRG", "CMCSA", "HON", "BKNG", "AMAT", "KKR", "VRTX", "SBUX", "PANW", "ADP",
        "GILD", "LRCX", "ADI", "MELI", "MDLZ", "CTAS", "REGN", "KLAC", "CRWD", "SNPS"
    ]

@st.cache_data(ttl=300)
def scan_market_realtime(tickers):
    data_list = []
    batch_size = 10
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    for i in range(total_batches):
        batch = tickers[i*batch_size : (i+1)*batch_size]
        try:
            df_batch = yf.download(batch, period="5d", interval="15m", group_by='ticker', progress=False, threads=False)
            
            for ticker in batch:
                try:
                    if len(batch) == 1: df = df_batch
                    else: df = df_batch[ticker]
                    
                    df = df.dropna()
                    if len(df) < 10: continue
                    
                    curr = df['Close'].iloc[-1]
                    today_date = df.index[-1].date()
                    prev_days_data = df[df.index.date != today_date]
                    
                    if not prev_days_data.empty:
                        prev_close = prev_days_data['Close'].iloc[-1]
                        pct = ((curr - prev_close) / prev_close)
                    else:
                        pct = ((curr - df['Close'].iloc[0]) / df['Close'].iloc[0])

                    trend = df['Close'].tail(20).tolist()
                    
                    rsi = ta.rsi(df['Close'], length=14)
                    rsi_val = rsi.iloc[-1] if rsi is not None else 50
                    
                    signal = "⚪"
                    if rsi_val < 30: signal = "🔥抄底"
                    elif rsi_val > 75: signal = "⚠️止盈"
                    elif pct > 0.03: signal = "🚀暴涨"
                    elif pct < -0.03: signal = "📉暴跌"
                    
                    data_list.append({
                        "Symbol": ticker,
                        "Trend": trend,
                        "Price": curr,
                        "Chg": pct,
                        "Signal": signal,
                        "SortKey": abs(pct)
                    })
                except: continue
        except: continue
        
    return pd.DataFrame(data_list)

def get_detailed_history(ticker, period, interval):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        info = stock.info
        return hist, info, stock
    except: return pd.DataFrame(), {}, None

def get_news_ddg(ticker):
    try:
        results = DDGS().news(keywords=f"{ticker} stock news", max_results=5)
        return list(results)
    except: return []

# --- 新增：计算期权PCR和获取内幕交易 ---
@st.cache_data(ttl=3600)
def get_advanced_data(ticker):
    stock = yf.Ticker(ticker)
    
    # 1. 计算 Put/Call Ratio (PCR)
    pcr = "N/A"
    try:
        opts = stock.options
        if opts:
            # 获取最近的期权链
            opt_chain = stock.option_chain(opts[0])
            calls_vol = opt_chain.calls['volume'].sum()
            puts_vol = opt_chain.puts['volume'].sum()
            if calls_vol > 0:
                pcr_val = puts_vol / calls_vol
                pcr = round(pcr_val, 2)
    except: pass
    
    # 2. 获取内幕交易
    insider = pd.DataFrame()
    try:
        insider = stock.insider_transactions
        if insider is not None and not insider.empty:
            insider = insider.head(5)[['Start Date', 'Insider', 'Text', 'Shares']]
    except: pass
    
    return pcr, insider

# ==========================================
# 3. 界面布局
# ==========================================

st.title("⚡ AI 量化全能终端 (机构版)")
col_nav, col_chart, col_info = st.columns([2.5, 5.5, 2.0])

# --- 左侧列表 ---
with col_nav:
    st.subheader("全市场扫描")
    tickers = get_nasdaq100_list()
    with st.spinner("正在同步实时行情..."):
        df_scan = scan_market_realtime(tickers)
    
    if not df_scan.empty:
        df_scan = df_scan.sort_values(by="SortKey", ascending=False)
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

# --- 中间图表 ---
with col_chart:
    if 'period' not in st.session_state: st.session_state.period = '1d'
    if 'interval' not in st.session_state: st.session_state.interval = '1m'
    
    hist_fast, info, stock_obj = get_detailed_history(selected_ticker, "1d", "1m")
    
    # 获取高级数据 (PCR & Insider)
    pcr_val, insider_df = get_advanced_data(selected_ticker)
    
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
    
    p_cols = st.columns(5)
    def set_p(p, i): 
        st.session_state.period = p
        st.session_state.interval = i
    
    with p_cols[0]: st.button("1天 (1m)", on_click=set_p, args=('1d','1m'), use_container_width=True)
    with p_cols[1]: st.button("5天 (5m)", on_click=set_p, args=('5d','5m'), use_container_width=True)
    with p_cols[2]: st.button("1月 (30m)", on_click=set_p, args=('1mo','30m'), use_container_width=True)
    with p_cols[3]: st.button("日线", on_click=set_p, args=('6mo','1d'), use_container_width=True)
    with p_cols[4]: st.button("周线", on_click=set_p, args=('2y','1wk'), use_container_width=True)

    hist, _ = get_detailed_history(selected_ticker, st.session_state.period, st.session_state.interval)
    
    if not hist.empty:
        macd = ta.macd(hist['Close'])
        y_min = hist['Close'].min() * 0.999
        y_max = hist['Close'].max() * 1.001
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2], subplot_titles=("价格", "成交量", "MACD"))
        
        fill_color = 'rgba(0, 128, 0, 0.1)' if diff >= 0 else 'rgba(217, 30, 24, 0.1)'
        line_color = '#008000' if diff >= 0 else '#d91e18'
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', fill='tozeroy', fillcolor=fill_color, line=dict(color=line_color, width=2), name='Price'), row=1, col=1)
        
        colors = ['#008000' if c >= o else '#d91e18' for c, o in zip(hist['Close'], hist['Open'])]
        fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], marker_color=colors, name='Vol'), row=2, col=1)
        
        if macd is not None:
            fig.add_trace(go.Scatter(x=hist.index, y=macd.iloc[:, 0], line=dict(color='#2962FF', width=1), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=macd.iloc[:, 2], line=dict(color='#FF6D00', width=1), name='Signal'), row=3, col=1)
            hist_colors = ['#26a69a' if h >= 0 else '#ef5350' for h in macd.iloc[:, 1]]
            fig.add_trace(go.Bar(x=hist.index, y=macd.iloc[:, 1], marker_color=hist_colors, name='Hist'), row=3, col=1)

        rangebreaks = []
        if st.session_state.interval in ['1m', '2m', '5m', '15m', '30m', '60m']:
            rangebreaks.append(dict(bounds=["sat", "sun"]))
            rangebreaks.append(dict(bounds=[16, 9.5], pattern="hour"))

        fig.update_layout(height=650, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor='white', paper_bgcolor='white', showlegend=False, xaxis_rangeslider_visible=False, yaxis=dict(range=[y_min, y_max], gridcolor='#f0f0f0', side='right'), yaxis2=dict(gridcolor='#f0f0f0', side='right'), yaxis3=dict(gridcolor='#f0f0f0', side='right'), hovermode="x unified", xaxis=dict(rangebreaks=rangebreaks))
        st.plotly_chart(fig, use_container_width=True)

    # --- 底部多维信息 (Tabs) ---
    tab1, tab2, tab3 = st.tabs(["📰 实时新闻", "💼 高管交易", "📅 财报信息"])
    
    with tab1:
        news = get_news_ddg(selected_ticker)
        for item in news:
            st.markdown(f"- [{translate_text(item.get('title',''))}]({item.get('url','#')}) <span style='color:gray;font-size:12px'>{item.get('date','')[:10]}</span>", unsafe_allow_html=True)

    with tab2:
        if not insider_df.empty:
            # 简单清洗数据
            st.dataframe(insider_df, use_container_width=True, hide_index=True)
        else:
            st.info("近期无高管交易记录")

    with tab3:
        # 获取下一次财报日期
        try:
            calendar = stock_obj.calendar
            if calendar and 'Earnings Date' in calendar:
                earnings_date = calendar['Earnings Date'][0]
                st.metric("下一次财报日", f"{earnings_date}")
            else:
                st.write("暂无财报日历数据")
        except: st.write("数据不可用")

# --- 右侧：分析区 ---
with col_info:
    st.subheader("📊 决策看板")
    
    if not hist.empty:
        curr = hist['Close'].iloc[-1]
        bb = ta.bbands(hist['Close'], length=20, std=2.0)
        
        if bb is not None:
            support = bb.iloc[-1, 0]
            resis = bb.iloc[-1, 2]
        else:
            support = curr * 0.95
            resis = curr * 1.05

        st.markdown(f"""
<div class="trade-panel">
<h4>🤖 AI 策略建议</h4>
<div style="font-size:13px; color:#666; margin-bottom:15px;">基于布林带波动率模型</div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
<span class="label-sell">阻力位 (Sell)</span>
<span class="price-down">${resis:.2f}</span>
</div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-top:1px dashed #eee; border-bottom:1px dashed #eee; padding:8px 0;">
<span style="font-weight:600;">当前价格</span>
<span class="price-neutral">${curr:.2f}</span>
</div>
<div style="display:flex; justify-content:space-between; align-items:center;">
<span class="label-buy">支撑位 (Buy)</span>
<span class="price-up">${support:.2f}</span>
</div>
</div>
""", unsafe_allow_html=True)
        
        # --- 新增：市场情绪看板 ---
        short_float = info.get('shortPercentOfFloat', 0)
        short_val = f"{short_float*100:.2f}%" if short_float else "N/A"
        
        # PCR 颜色判断
        pcr_color = "#333"
        pcr_text = str(pcr_val)
        if pcr_val != "N/A":
            if pcr_val > 1.0: pcr_color = "#d91e18" # 看跌
            elif pcr_val < 0.7: pcr_color = "#008000" # 看涨
        
        st.markdown(f"""
<div class="trade-panel">
<h4>🌪️ 市场情绪</h4>
<div style="display:flex; justify-content:space-between; margin-bottom:8px;">
<span>期权PCR比率:</span>
<strong style="color:{pcr_color}">{pcr_text}</strong>
</div>
<div style="font-size:11px; color:#666; margin-bottom:15px;">
(>1.0 偏空, <0.7 偏多)
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:8px;">
<span>做空比例:</span>
<strong>{short_val}</strong>
</div>
<div style="font-size:11px; color:#666;">
(>10% 有逼空风险)
</div>
</div>
""", unsafe_allow_html=True)
        
        # 机构评级
        target = info.get('targetMeanPrice', 0)
        rating = info.get('recommendationKey', 'none').upper().replace('_', ' ')
        
        st.markdown(f"""
<div class="trade-panel">
<h4>🏦 机构观点</h4>
<div style="text-align:center; font-size:20px; font-weight:800; color:#2962FF; margin:15px 0;">{rating}</div>
<div style="display:flex; justify-content:space-between; font-size:13px;">
<span>华尔街目标价:</span>
<strong>${target}</strong>
</div>
</div>
""", unsafe_allow_html=True)
        
        # 核心数据
        st.markdown(f"""
<div class="trade-panel">
<h4>📈 核心数据</h4>
<div style="font-size:13px; line-height:2.2;">
<div style="display:flex; justify-content:space-between;"><span>市盈率 (PE):</span> <strong>{info.get('trailingPE','N/A')}</strong></div>
<div style="display:flex; justify-content:space-between;"><span>市值:</span> <strong>{info.get('marketCap',0)/1e9:.1f}B</strong></div>
<div style="display:flex; justify-content:space-between;"><span>52周高:</span> <strong>{info.get('fiftyTwoWeekHigh','N/A')}</strong></div>
<div style="display:flex; justify-content:space-between;"><span>做空比:</span> <strong>{info.get('shortRatio','N/A')}</strong></div>
</div>
</div>
""", unsafe_allow_html=True)
