import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(
    page_title="纳指科技量化终端 (完整版)",
    page_icon="🦅",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    .stButton>button {width: 100%;}
</style>
""", unsafe_allow_html=True)

st.title("🦅 纳指 100 全能量化终端")
st.caption("集成了：全市场扫描 + 暴跌雷达 + 深度图表")

# ==========================================
# 2. 侧边栏：股票池选择
# ==========================================
st.sidebar.header("⚙️ 扫描范围设置")

scan_mode = st.sidebar.radio(
    "请选择股票池:",
    ("💎 核心科技七巨头 (Mag 7)", "🚀 纳斯达克 100 (完整成分股)")
)

# --- 内置完整名单 (确保稳定) ---
@st.cache_data
def get_nasdaq100_tickers():
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

# 确定列表
if scan_mode == "💎 核心科技七巨头 (Mag 7)":
    target_tickers = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "TSM"]
    st.sidebar.info("⚡️ 极速模式：只扫描最核心的几只。")
else:
    st.sidebar.warning("⚠️ 纳指100全扫描约需 1-2 分钟，请点击下方按钮开始。")
    if st.sidebar.button("🚀 开始全量扫描"):
        target_tickers = get_nasdaq100_tickers()
        st.sidebar.success(f"已加载 {len(target_tickers)} 只股票，开始分析...")
    else:
        target_tickers = [] 

# ==========================================
# 3. 核心量化引擎
# ==========================================
@st.cache_data(ttl=600)
def analyze_tech_stocks(tickers):
    if not tickers: return pd.DataFrame()
    
    data_list = []
    progress_text = "正在逐个分析..."
    my_bar = st.progress(0, text=progress_text)
    
    batch_size = 25 
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    for i in range(total_batches):
        batch = tickers[i*batch_size : (i+1)*batch_size]
        
        try:
            df_data = yf.download(batch, period="3mo", group_by='ticker', progress=False, threads=True)
            
            for ticker in batch:
                try:
                    if len(batch) == 1: df = df_data
                    else: df = df_data[ticker]
                    
                    df = df.dropna()
                    if len(df) < 30: continue
                    
                    # 1. 基础数据
                    curr_price = df['Close'].iloc[-1]
                    pct_chg = ((curr_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                    
                    # 2. 关键指标
                    bb = df.ta.bbands(length=20, std=2.0)
                    lower_band = bb.iloc[-1, 0]
                    rsi = df.ta.rsi(length=14).iloc[-1]
                    mfi = df.ta.mfi(length=14).iloc[-1]
                    
                    # 3. 筛选逻辑
                    signals = []
                    score = 0
                    strategy = "观望"
                    
                    # 抄底信号
                    is_oversold = False
                    if curr_price < lower_band:
                        signals.append("⚡跌破布林下轨")
                        score += 2
                        is_oversold = True
                    if rsi < 35:
                        signals.append(f"RSI超卖({round(rsi,0)})")
                        score += 1
                        is_oversold = True
                    if mfi < 25:
                        signals.append(f"资金吸筹({round(mfi,0)})")
                        score += 2
                    
                    # 只有有信号的才显示 (保持页面干净)
                    # 七巨头模式下全部显示
                    if len(tickers) > 20 and score == 0:
                        continue
                        
                    # 评级
                    rating = "观察"
                    if score >= 3: rating = "🔥 Strong Buy"
                    elif score >= 1: rating = "✅ Watch"
                    
                    if is_oversold: strategy = "博弈反弹"
                    
                    data_list.append({
                        "代码": ticker,
                        "现价": round(curr_price, 2),
                        "涨跌幅%": round(pct_chg, 2),
                        "评级": rating,
                        "策略": strategy,
                        "RSI": round(rsi, 1),
                        "MFI (资金)": round(mfi, 1),
                        "布林下轨": round(lower_band, 2),
                        "信号": ", ".join(signals)
                    })
                    
                except: continue
        except: continue
        
        my_bar.progress((i + 1) / total_batches)
        
    my_bar.empty()
    return pd.DataFrame(data_list)

# ==========================================
# 4. 结果展示 (Tabs 界面)
# ==========================================

if target_tickers:
    df_result = analyze_tech_stocks(target_tickers)
    
    if not df_result.empty:
        # 定义高亮样式
        def highlight_cols(val):
            if "Strong" in str(val): return 'background-color: #28a745; color: white'
            if "Watch" in str(val): return 'background-color: #d4edda; color: black'
            return ''
            
        # --- 这里恢复了 Tab 功能 ---
        tab1, tab2, tab3 = st.tabs(["📊 综合大屏", "⚡ 暴跌抄底雷达", "📈 个股深度K线"])

        # --- Tab 1: 综合列表 ---
        with tab1:
            st.subheader(f"全市场扫描结果 ({len(df_result)} 只)")
            st.dataframe(
                df_result.style.applymap(highlight_cols, subset=['评级'])
                         .format({"涨跌幅%": "{:.2f}%"}),
                use_container_width=True,
                height=600
            )

        # --- Tab 2: 抄底雷达 ---
        with tab2:
            st.subheader("📉 黄金坑机会 (Oversold Scanner)")
            st.markdown("筛选条件：**跌破布林下轨** 或 **RSI < 35** 的股票")
            
            # 筛选
            dip_df = df_result[df_result['策略'] == "博弈反弹"]
            
            if not dip_df.empty:
                st.dataframe(
                    dip_df.style.applymap(highlight_cols, subset=['评级']),
                    use_container_width=True
                )
                for index, row in dip_df.iterrows():
                     st.info(f"👉 **{row['代码']}**: 现价 ${row['现价']} vs 布林支撑 ${row['布林下轨']} | 信号: {row['信号']}")
            else:
                st.success("当前纳指100成分股中，没有出现极度超卖的‘黄金坑’机会，市场情绪平稳。")

        # --- Tab 3: K线图 ---
        with tab3:
            st.subheader("个股走势确认")
            # 下拉框只显示扫描出来的股票
            select_list = df_result['代码'].tolist()
            if select_list:
                selected_ticker = st.selectbox("选择股票查看K线:", select_list)
                
                if selected_ticker:
                    stock_df = yf.download(selected_ticker, period="6mo", progress=False)
                    fig = go.Figure(data=[go.Candlestick(
                        x=stock_df.index,
                        open=stock_df['Open'],
                        high=stock_df['High'],
                        low=stock_df['Low'],
                        close=stock_df['Close'],
                        name=selected_ticker
                    )])
                    fig.update_layout(title=f"{selected_ticker} - 日线走势", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("暂无数据可绘图。")

    else:
        st.info("扫描完成！当前没有触发‘买入信号’的股票。")
else:
    st.info("👈 请在左侧选择‘纳斯达克 100’并点击按钮。")
