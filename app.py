import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(
    page_title="纳指科技量化终端",
    page_icon="💻",
    layout="wide"
)

# 自定义 CSS: 优化表格显示
st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    .stButton>button {width: 100%;}
</style>
""", unsafe_allow_html=True)

st.title("💻 纳指科技股猎手 (Nasdaq 100 Scanner)")
st.caption("核心逻辑：锁定纳斯达克市值前100大公司，剔除小盘股，专注科技与成长。")

# ==========================================
# 2. 侧边栏：股票池选择
# ==========================================
st.sidebar.header("⚙️ 扫描范围设置")

scan_mode = st.sidebar.radio(
    "请选择股票池:",
    ("💎 核心科技七巨头 (Mag 7)", "🚀 纳斯达克 100 (大盘科技全扫描)")
)

# --- 核心函数：获取纳指100名单 ---
@st.cache_data
def get_nasdaq100_tickers():
    try:
        # 从维基百科抓取 Nasdaq-100 成分股
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        tables = pd.read_html(url)
        # 维基百科表格结构经常变，通常在第4或第5个表
        for table in tables:
            if 'Ticker' in table.columns:
                return table['Ticker'].tolist()
            elif 'Symbol' in table.columns:
                return table['Symbol'].tolist()
        # 如果抓取失败，返回保底的科技龙头列表
        return ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "PEP", "AMD", "NFLX", "INTC", "QCOM"]
    except:
        return ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AMD"]

# 确定要扫描的列表
if scan_mode == "💎 核心科技七巨头 (Mag 7)":
    # 手动精选：七巨头 + 热门AI芯片
    target_tickers = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "TSM", "ORCL", "SMCI", "ARM"]
    st.sidebar.info("⚡️ 极速模式：只看最核心的 AI 和科技龙头。")
else:
    # 纳指 100 模式
    st.sidebar.warning("⚠️ 扫描 100 只大盘科技股约需 30-60 秒。")
    if st.sidebar.button("🚀 加载纳斯达克 100 并开始"):
        with st.spinner("正在拉取 Nasdaq-100 成分股名单..."):
            target_tickers = get_nasdaq100_tickers()
        st.sidebar.success(f"成功锁定 {len(target_tickers)} 只大盘科技股！")
    else:
        target_tickers = [] # 默认不加载

# ==========================================
# 3. 核心量化引擎 (Data Engine)
# ==========================================
@st.cache_data(ttl=600)
def analyze_tech_stocks(tickers):
    if not tickers: return pd.DataFrame()
    
    data_list = []
    # 进度条
    progress_text = "正在分析科技股资金流向..."
    my_bar = st.progress(0, text=progress_text)
    
    # 分批处理防止超时
    batch_size = 20
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    for i in range(total_batches):
        batch = tickers[i*batch_size : (i+1)*batch_size]
        batch = [t.replace('.', '-') for t in batch] # 修正代码格式
        
        try:
            # 下载数据
            df_data = yf.download(batch, period="6mo", group_by='ticker', progress=False, threads=True)
            
            for ticker in batch:
                try:
                    # 提取单只股票数据
                    if len(batch) == 1: df = df_data
                    else: df = df_data[ticker]
                    
                    df = df.dropna()
                    if len(df) < 50: continue
                    
                    # --- 1. 基础数据 ---
                    curr_price = df['Close'].iloc[-1]
                    pct_chg = ((curr_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                    
                    # --- 2. 技术指标 ---
                    # 布林带 (20, 2)
                    bb = df.ta.bbands(length=20, std=2.0)
                    lower_band = bb.iloc[-1, 0]
                    upper_band = bb.iloc[-1, 2]
                    
                    # RSI
                    rsi = df.ta.rsi(length=14).iloc[-1]
                    
                    # MFI (资金流)
                    mfi = df.ta.mfi(length=14).iloc[-1]
                    
                    # EMA (趋势)
                    ema50 = df.ta.ema(length=50).iloc[-1]
                    
                    # --- 3. 筛选逻辑 (Filter Logic) ---
                    signals = []
                    score = 0
                    
                    # 抄底信号 (Dip Buy)
                    if curr_price < lower_band:
                        signals.append("⚡跌破布林下轨")
                        score += 2
                    if rsi < 30:
                        signals.append("RSI超卖")
                        score += 1
                    if mfi < 20:
                        signals.append("资金极度吸筹")
                        score += 2
                        
                    # 趋势信号 (Trend)
                    if curr_price > ema50:
                        # 只有在上升趋势中的回调才值得买
                        if rsi < 50 and rsi > 40:
                            signals.append("上升趋势回调")
                            
                    # 评级
                    rating = "观察"
                    if score >= 3: rating = "🔥 Strong Buy"
                    elif score >= 1: rating = "✅ Buy Dip"
                    elif mfi > 80: rating = "⚠️ Sell/Risk"
                    
                    # 如果是纳指100全扫描，只保留有信号的，或者是科技七巨头模式则全保留
                    if len(tickers) > 20 and not signals:
                        continue
                        
                    data_list.append({
                        "代码": ticker,
                        "现价": round(curr_price, 2),
                        "涨跌幅%": round(pct_chg, 2),
                        "评级": rating,
                        "RSI": round(rsi, 1),
                        "MFI (资金)": round(mfi, 1),
                        "信号": ", ".join(signals) if signals else "趋势中性"
                    })
                    
                except: continue
        except: continue
        
        my_bar.progress((i + 1) / total_batches)
        
    my_bar.empty()
    return pd.DataFrame(data_list)

# ==========================================
# 4. 结果展示
# ==========================================

if target_tickers:
    df_result = analyze_tech_stocks(target_tickers)
    
    if not df_result.empty:
        # 按照“机会大小”排序：优先显示 MFI 低（资金吸筹）和 RSI 低（超卖）的
        df_result = df_result.sort_values(by=["MFI (资金)", "RSI"], ascending=True)
        
        # 样式高亮
        def highlight_cols(val):
            if "Strong" in str(val): return 'background-color: #28a745; color: white' # 深绿
            if "Buy" in str(val): return 'background-color: #d4edda; color: black'    # 浅绿
            if "Sell" in str(val): return 'background-color: #f8d7da; color: black'   # 浅红
            return ''
            
        st.subheader(f"📊 扫描结果 ({len(df_result)} 只)")
        st.dataframe(
            df_result.style.applymap(highlight_cols, subset=['评级'])
                     .format({"涨跌幅%": "{:.2f}%"}),
            use_container_width=True,
            height=800
        )
    else:
        st.info("当前数据加载中，或没有触发‘极端信号’的股票。")
else:
    st.info("👈 请在左侧选择模式并点击按钮。")
