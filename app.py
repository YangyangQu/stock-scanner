import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(
    page_title="AI 智能选股终端 (Pro)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 美化表格
st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div[data-testid="stMetricValue"] {font-size: 18px;}
</style>
""", unsafe_allow_html=True)

st.title("🚀 美股智能量化终端 (AI Trader Pro)")
st.markdown("### 核心策略：资金流向 (Money Flow) + 趋势共振 + 暴跌反转")

# ==========================================
# 2. 侧边栏：股票池设置
# ==========================================
st.sidebar.header("⚙️ 监控池设置")

# 默认包含咱们讨论过的热门股
default_tickers = "AMD, NVDA, TSLA, AMZN, GOOGL, MSFT, META, AAPL, COIN, PLTR, MU, TGT, SMCI, MARA"
ticker_input = st.sidebar.text_area("输入股票代码 (逗号分隔)", default_tickers, height=100)
ticker_list = [x.strip().upper() for x in ticker_input.split(',')]

# 刷新按钮
if st.sidebar.button("🔄 立即刷新数据"):
    st.cache_data.clear()

st.sidebar.markdown("---")
st.sidebar.info("""
**指标说明：**
* **MFI (资金流):** <20 吸筹(买), >80 过热(卖)
* **CMF (主力):** >0 资金流入, <0 资金流出
* **布林带:** 跌破下轨 = 极端超卖
""")


# ==========================================
# 3. 核心量化逻辑 (Data Engine)
# ==========================================
@st.cache_data(ttl=300)  # 缓存5分钟，防止请求过于频繁
def get_quant_data(tickers):
    data_list = []

    # 批量下载数据，提升速度
    data = yf.download(tickers, period="6mo", group_by='ticker', progress=True)

    for ticker in tickers:
        try:
            # 处理单只股票数据
            if len(tickers) == 1:
                df = data
            else:
                df = data[ticker]

            # 清洗数据
            df = df.dropna()
            if len(df) < 50: continue

            # --- A. 基础数据 ---
            current_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            pct_change = ((current_price - prev_close) / prev_close) * 100
            volume = df['Volume'].iloc[-1]

            # --- B. 技术指标 (Technical) ---
            # 1. EMA (趋势)
            ema_20 = df.ta.ema(length=20).iloc[-1]
            ema_50 = df.ta.ema(length=50).iloc[-1]

            # 2. RSI (动能)
            rsi = df.ta.rsi(length=14).iloc[-1]

            # 3. MACD (趋势确认)
            macd = df.ta.macd(fast=12, slow=26, signal=9)
            macd_line = macd.iloc[-1, 0]
            macd_signal = macd.iloc[-1, 2]

            # 4. 布林带 (用于抄底)
            bbands = df.ta.bbands(length=20, std=2.0)
            bb_lower = bbands.iloc[-1, 0]  # Lower band
            bb_upper = bbands.iloc[-1, 2]  # Upper band

            # --- C. 资金指标 (Money Flow - 核心) ---
            # 1. MFI (资金流量指标)
            mfi = df.ta.mfi(length=14).iloc[-1]

            # 2. CMF (柴金资金流)
            cmf = df.ta.cmf(length=20).iloc[-1]

            # --- D. 信号判定模型 (Scoring Model) ---
            score = 0
            signals = []
            strategy_type = "观望"

            # 1. 趋势得分
            if current_price > ema_20: score += 1
            if current_price > ema_50: score += 1
            if macd_line > macd_signal:
                score += 1
                signals.append("MACD金叉")

            # 2. 资金得分
            if mfi < 20:
                score += 2
                signals.append("MFI极度吸筹")
            elif mfi > 80:
                score -= 2
                signals.append("⚠️资金过热")

            if cmf > 0.05:
                score += 1
                signals.append("主力净流入")
            elif cmf < -0.05:
                signals.append("主力出逃")

            # 3. 暴跌抄底特判 (Knife Catching)
            is_oversold = False
            if current_price < bb_lower:
                signals.append("⚡跌破布林下轨")
                is_oversold = True
                strategy_type = "超卖反弹 (Reversal)"
                score += 2  # 给予额外加分

            # RSI 特判
            if rsi < 30:
                signals.append("RSI超卖")
                if is_oversold: strategy_type = "🔥 黄金坑 (Strong Buy)"

            # 最终评级
            rating = "Hold"
            if score >= 5:
                rating = "Strong Buy 🔥"
            elif score >= 3:
                rating = "Buy ✅"
            elif score <= 1:
                rating = "Sell ⚠️"

            # 针对暴跌股的特殊评级
            if is_oversold and rsi < 35:
                rating = "⚠️ 抄底博弈"

            data_list.append({
                "代码": ticker,
                "现价": round(current_price, 2),
                "涨跌幅%": round(pct_change, 2),
                "评级": rating,
                "策略类型": strategy_type,
                "MFI (资金)": round(mfi, 1),
                "CMF (主力)": round(cmf, 3),
                "RSI": round(rsi, 1),
                "关键信号": ", ".join(signals),
                "布林下轨": round(bb_lower, 2)
            })

        except Exception as e:
            continue

    return pd.DataFrame(data_list)


# 获取数据
with st.spinner('正在连接华尔街数据源...'):
    df_result = get_quant_data(ticker_list)

# ==========================================
# 4. 页面展示逻辑 (Tabs)
# ==========================================

if df_result is not None and not df_result.empty:

    # 定义样式函数
    def highlight_rating(val):
        color = ''
        if 'Strong Buy' in val:
            color = 'background-color: #28a745; color: white'
        elif 'Buy' in val:
            color = 'background-color: #d4edda; color: black'
        elif 'Sell' in val:
            color = 'background-color: #f8d7da; color: black'
        elif '抄底' in val:
            color = 'background-color: #ffc107; color: black'  # 黄色警示
        return color


    def highlight_mfi(val):
        if val < 20: return 'color: #28a745; font-weight: bold'  # 绿色吸筹
        if val > 80: return 'color: #dc3545; font-weight: bold'  # 红色过热
        return ''


    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["📊 综合量化大屏", "⚡ 暴跌抄底雷达", "📈 个股深度K线"])

    # --- Tab 1: 综合大屏 ---
    with tab1:
        st.subheader("全市场扫描结果")
        st.dataframe(
            df_result.style.applymap(highlight_rating, subset=['评级'])
            .applymap(highlight_mfi, subset=['MFI (资金)'])
            .format({"涨跌幅%": "{:.2f}%"}),
            use_container_width=True,
            height=600
        )

    # --- Tab 2: 暴跌抄底雷达 (筛选器) ---
    with tab2:
        st.subheader("📉 黄金坑扫描 (Oversold Scanner)")
        st.markdown("**筛选逻辑：** 股价跌破布林带下轨 OR RSI < 30。适合左侧交易者。")

        # 筛选符合条件的股票
        dip_stocks = df_result[
            (df_result['现价'] < df_result['布林下轨']) |
            (df_result['RSI'] < 30)
            ]

        if not dip_stocks.empty:
            st.success(f"发现 {len(dip_stocks)} 只潜在抄底标的！")
            st.dataframe(
                dip_stocks.style.applymap(highlight_rating, subset=['评级']),
                use_container_width=True
            )
            for index, row in dip_stocks.iterrows():
                st.info(f"👉 **{row['代码']}**: {row['关键信号']} | 建议关注布林下轨支撑位 ${row['布林下轨']}")
        else:
            st.warning("当前没有股票符合'极端超卖'条件，市场情绪平稳。")

    # --- Tab 3: 个股K线图 ---
    with tab3:
        st.subheader("个股详细走势")
        selected_ticker = st.selectbox("选择要查看的股票", ticker_list)

        if selected_ticker:
            # 获取单只股票历史数据
            stock_df = yf.download(selected_ticker, period="6mo")

            # 使用 Plotly 画交互式K线图
            fig = go.Figure(data=[go.Candlestick(
                x=stock_df.index,
                open=stock_df['Open'],
                high=stock_df['High'],
                low=stock_df['Low'],
                close=stock_df['Close'],
                name=selected_ticker
            )])

            fig.update_layout(title=f"{selected_ticker} - 日线图", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

else:
    st.error("无法获取数据，请检查网络或股票代码。")