import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from deep_translator import GoogleTranslator
from datetime import datetime

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(
    page_title="AI 量化决策终端",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container {padding-top: 1rem; padding-bottom: 3rem;}
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .trade-card {
        background-color: #e3f2fd;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2196f3;
        margin-bottom: 20px;
    }
    .news-card {
        padding: 10px;
        border-bottom: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心功能函数
# ==========================================

@st.cache_data(ttl=3600)
def translate_text(text):
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
        df_data = yf.download(tickers, period="1mo", group_by='ticker', progress=False, threads=True)
        for ticker in tickers:
            try:
                # 兼容 yfinance 不同版本的数据结构
                if len(tickers) == 1:
                    df = df_data
                else:
                    df = df_data[ticker]
                
                df = df.dropna()
                if len(df) < 20: continue
                
                curr = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                pct = ((curr - prev) / prev) * 100
                
                rsi = df.ta.rsi(length=14).iloc[-1]
                mfi = df.ta.mfi(length=14).iloc[-1]
                
                rating = "Hold"
                score = 0
                if rsi < 35: score += 1
                if mfi < 25: score += 1
                if score >= 2: rating = "🔥 Strong Buy"
                elif score == 1: rating = "✅ Watch"
                
                data_list.append({
                    "代码": ticker,
                    "最新价": round(curr, 2),
                    "涨跌幅%": round(pct, 2),
                    "评级": rating,
                    "RSI": round(rsi, 1),
                    "MFI": round(mfi, 1)
                })
            except: continue
    except: return pd.DataFrame()
    return pd.DataFrame(data_list)

def get_stock_detail(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="6mo")
    news = stock.news
    return info, hist, news

# ==========================================
# 3. 策略计算逻辑
# ==========================================
def calculate_trade_plan(df):
    current_price = df['Close'].iloc[-1]
    
    # 修复点：显式计算并合并布林带，不依赖 append=True
    bb = df.ta.bbands(length=20, std=2.0)
    if bb is not None:
        # 动态获取列名（避免 Key Error）
        lower_col = bb.columns[0] # 通常第一列是下轨
        upper_col = bb.columns[2] # 第三列是上轨
        lower_band = bb[lower_col].iloc[-1]
        upper_band = bb[upper_col].iloc[-1]
    else:
        lower_band = current_price * 0.95
        upper_band = current_price * 1.05
    
    atr_series = df.ta.atr(length=14)
    atr = atr_series.iloc[-1] if atr_series is not None else current_price * 0.02
    
    # 策略逻辑
    if current_price < lower_band:
        buy_price = current_price 
        strategy_text = "极度超卖 (Oversold)"
    else:
        buy_price = max(lower_band, current_price - (atr * 0.5))
        strategy_text = "回踩支撑 (Dip Buy)"

    stop_loss = buy_price - (atr * 2)
    take_profit = buy_price + (buy_price - stop_loss) * 2
    if take_profit > upper_band * 1.1:
        take_profit = upper_band
        
    return {
        "buy": round(buy_price, 2),
        "stop": round(stop_loss, 2),
        "target": round(take_profit, 2),
        "atr": round(atr, 2),
        "desc": strategy_text
    }

# ==========================================
# 4. 页面布局
# ==========================================

st.title("⚡ AI 量化决策终端")
col_list, col_detail = st.columns([1, 2.5])

# --- 左侧列表 ---
with col_list:
    st.subheader("📋 实时扫描")
    tickers = get_nasdaq100_list()
    df_scan = scan_market(tickers)
    
    if not df_scan.empty:
        df_scan = df_scan.sort_values(by=["评级", "MFI"], ascending=[False, True])
        selection = st.dataframe(
            df_scan, use_container_width=True, height=700,
            hide_index=True, selection_mode="single-row", on_select="rerun"
        )
        selected_rows = selection.selection.rows
        selected_ticker = df_scan.iloc[selected_rows[0]]["代码"] if selected_rows else None
    else:
        st.error("数据加载中...")
        selected_ticker = None

# --- 右侧详情 ---
with col_detail:
    if selected_ticker:
        info, hist, news_list = get_stock_detail(selected_ticker)
        
        # 1. 标题区
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"## {selected_ticker} - {info.get('shortName', '')}")
        with c2:
            price = info.get('currentPrice', hist['Close'].iloc[-1])
            prev = info.get('previousClose', hist['Close'].iloc[-2])
            st.metric("现价", f"${price}", f"{price-prev:.2f}")

        # 2. 🤖 AI 交易计划
        plan = calculate_trade_plan(hist)
        
        st.markdown(f"""
        <div class="trade-card">
            <h4>🤖 AI 交易建议 ({plan['desc']})</h4>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <div>🔵 <strong>建议买入:</strong> ${plan['buy']}</div>
                <div>🔴 <strong>止损点:</strong> ${plan['stop']}</div>
                <div>🟢 <strong>止盈点:</strong> ${plan['target']}</div>
            </div>
            <div style="font-size: 12px; color: #666; margin-top: 5px;">
                *基于 ATR 波动率模型计算，盈亏比 1:2
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. K线图 (修复 Key Error 的核心部分)
        # 手动计算布林带并合并，不再依赖自动 append
        bb_df = hist.ta.bbands(length=20, std=2.0)
        if bb_df is not None:
            # 获取动态列名
            bbl_col = bb_df.columns[0] # Lower
            bbu_col = bb_df.columns[2] # Upper
            # 合并数据
            hist = pd.concat([hist, bb_df], axis=1)
        else:
            bbl_col = bbu_col = None

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist['Open'], high=hist['High'],
            low=hist['Low'], close=hist['Close'], name='K线'
        ))
        
        # 只有当布林带计算成功时才画线
        if bbl_col:
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist[bbl_col], 
                line=dict(color='orange', width=1), name='布林下轨'
            ))
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist[bbu_col], 
                line=dict(color='blue', width=1), name='布林上轨'
            ))

        # 标记 AI 建议点位
        fig.add_hline(y=plan['buy'], line_dash="dash", line_color="blue", annotation_text="Buy")
        fig.add_hline(y=plan['stop'], line_dash="dash", line_color="red", annotation_text="Stop")
        fig.update_layout(height=450, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        # 4. 财务数据
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("市盈率 (PE)", round(info.get('trailingPE', 0), 1))
        m2.metric("市值", f"{info.get('marketCap', 0)/1e9:.1f}B")
        m3.metric("机构持仓", f"{round(info.get('heldPercentInstitutions', 0)*100, 1)}%")
        m4.metric("做空比率", f"{round(info.get('shortRatio', 0), 2)}")

        # 5. 📰 中文新闻解读
        st.subheader("📰 最新动态 (AI 翻译)")
        with st.spinner("正在翻译最新新闻..."):
            count = 0
            if news_list:
                for item in news_list:
                    if count >= 5: break 
                    
                    title_en = item.get('title', 'No Title')
                    link = item.get('link', '#')
                    publisher = item.get('publisher', 'Unknown')
                    pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M')
                    
                    # 调用翻译
                    title_zh = translate_text(title_en)
                    
                    st.markdown(f"""
                    <div class="news-card">
                        <a href="{link}" target="_blank" style="text-decoration: none; color: #333;">
                            <strong>{title_zh}</strong>
                        </a>
                        <div style="font-size: 12px; color: #888; margin-top: 4px;">
                            📅 {pub_time} | 来源: {publisher} <br>
                            <span style="color: #aaa;">(原文: {title_en})</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    count += 1
            else:
                st.info("暂无最新新闻。")

    else:
        st.info("👈 请点击左侧股票代码，生成 AI 交易报告。")
