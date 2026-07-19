"""
固定不变的渲染代码。
新增标的分析后，只需在 data/ 目录下新增一个 <TICKER>_<YYYYMMDD>.json 文件，
无需修改本文件。K线数据由 fetch_ohlc.py 写入 data/ohlc/<TICKER>.json。
"""
import json
import glob
import os
from datetime import datetime, date

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="交易分析报告 Dashboard", layout="wide")

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
OHLC_DIR = os.path.join(BASE_DIR, "data", "ohlc")
MACRO_EVENTS_PATH = os.path.join(BASE_DIR, "config", "macro_events.json")

# ---------- 配色（跟分析prompt里的评分分档对应，全站统一用这一套） ----------
SCORE_BUCKETS = [
    (75, 100, "#22c55e", "高质量偏多"),
    (60, 74, "#84cc16", "中等偏多"),
    (45, 59, "#f59e0b", "中性/信号冲突"),
    (30, 44, "#f97316", "中等偏空"),
    (0, 29, "#ef4444", "高质量偏空"),
]

VERDICT_COLOR = {
    "看多": "#22c55e",
    "中性偏多": "#84cc16",
    "中性": "#f59e0b",
    "中性偏空": "#f97316",
    "看空": "#ef4444",
}

CONFIDENCE_DOTS = {"高": "●●●", "中": "●●○", "低": "●○○"}


def score_color(score):
    for lo, hi, color, _ in SCORE_BUCKETS:
        if lo <= score <= hi:
            return color
    return "#94a3b8"


def verdict_color(verdict):
    return VERDICT_COLOR.get(verdict, "#94a3b8")


def esc(text):
    """Streamlit的markdown会把 $...$ 当成LaTeX数学公式，报告里的价格全是$xxx，
    必须转义成\\$，否则像"SMA50($303.56)"这种两个$会被当成公式渲染错位。"""
    return str(text).replace("$", "\\$")


st.markdown(
    """
    <style>
    .badge {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 999px;
        font-size: 1.3rem;
        font-weight: 700;
        color: white;
    }
    .badge-sm {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        color: white;
    }
    .score-track {
        background: rgba(148,163,184,0.2);
        border-radius: 999px;
        height: 14px;
        width: 100%;
        overflow: hidden;
    }
    .score-track-sm {
        background: rgba(148,163,184,0.2);
        border-radius: 999px;
        height: 6px;
        width: 100%;
        overflow: hidden;
    }
    .score-fill {
        height: 100%;
        border-radius: 999px;
    }
    .evidence-card {
        border-left: 4px solid;
        padding: 8px 14px;
        margin-bottom: 8px;
        border-radius: 4px;
        background: rgba(148,163,184,0.08);
    }
    .plain-summary {
        font-size: 1.05rem;
        line-height: 1.6;
        margin-bottom: 0.6rem;
    }
    .event-card {
        border-left: 3px solid;
        padding: 10px 16px;
        border-radius: 6px;
        background: rgba(148,163,184,0.08);
        height: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _dir_fingerprint(directory):
    """基于文件名+mtime生成签名，目录有新增或修改的json时自动使缓存失效。"""
    paths = sorted(glob.glob(os.path.join(directory, "*.json")))
    return tuple((p, os.path.getmtime(p)) for p in paths)


@st.cache_data
def load_reports(_fingerprint):
    reports = {}
    for path, _ in _fingerprint:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        label = os.path.splitext(os.path.basename(path))[0]  # e.g. AAPL_20260718
        reports[label] = data
    return reports


@st.cache_data
def load_ohlc_all(_fingerprint):
    ohlc = {}
    for path, _ in _fingerprint:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ohlc[data["ticker"]] = data["candles"]
    return ohlc


def load_macro_events():
    if not os.path.exists(MACRO_EVENTS_PATH):
        return []
    with open(MACRO_EVENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("events", [])


def build_candlestick(candles, interactive=True, height=380):
    dates = [datetime.fromtimestamp(c["t"]) for c in candles]
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=dates,
                open=[c["o"] for c in candles],
                high=[c["h"] for c in candles],
                low=[c["l"] for c in candles],
                close=[c["c"] for c in candles],
                increasing_line_color="#22c55e",
                decreasing_line_color="#ef4444",
                increasing_fillcolor="#22c55e",
                decreasing_fillcolor="#ef4444",
            )
        ]
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=4, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8"),
        xaxis_rangeslider_visible=False,
        showlegend=False,
    )
    if interactive:
        fig.update_layout(xaxis_rangeslider_visible=True, dragmode="pan")
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.15)")
    else:
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
    return fig


reports = load_reports(_dir_fingerprint(DATA_DIR))
ohlc_by_ticker = load_ohlc_all(_dir_fingerprint(OHLC_DIR)) if os.path.isdir(OHLC_DIR) else {}

if not reports:
    st.error(f"未在 {DATA_DIR} 找到任何报告数据（*.json）")
    st.stop()

# ---------- 侧边栏：视图切换 ----------
st.sidebar.title("📁 报告选择")
if st.sidebar.button("🔄 刷新数据"):
    st.cache_data.clear()
    st.rerun()

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "🏠 首页总览"
if "selected_label" not in st.session_state:
    st.session_state.selected_label = list(reports.keys())[0]


def _goto_report(label):
    """从卡片按钮跳转到完整报告。必须用on_click回调（在本次rerun的组件渲染之前执行），
    不能在渲染完组件后直接给同一个key的session_state赋值，Streamlit不允许那样做。"""
    st.session_state.selected_label = label
    st.session_state.view_mode = "📄 标的报告"


view_mode = st.sidebar.radio("视图", ["🏠 首页总览", "📄 标的报告"], key="view_mode")

if view_mode == "📄 标的报告":
    labels = list(reports.keys())
    idx = labels.index(st.session_state.selected_label) if st.session_state.selected_label in labels else 0
    selected_label = st.sidebar.selectbox("选择标的 / 日期", labels, index=idx, key="selected_label")


# ============================================================
# 首页总览
# ============================================================
def render_home():
    st.title("📊 我的股票分析总览")
    st.caption(f"共 {len(reports)} 份报告 · 点击卡片查看完整分析")

    st.subheader("持仓 / 关注标的")
    labels = list(reports.keys())
    cols_per_row = 3
    for row_start in range(0, len(labels), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, label in zip(cols, labels[row_start : row_start + cols_per_row]):
            rr = reports[label]
            with col:
                with st.container(border=True):
                    top_l, top_r = st.columns([1.4, 1])
                    with top_l:
                        st.markdown(f"**{rr['ticker']}**")
                        if rr.get("note"):
                            st.caption(esc(rr["note"]))
                    with top_r:
                        st.markdown(
                            f"<div style='text-align:right'><span class='badge-sm' "
                            f"style='background:{verdict_color(rr['verdict'])}'>{rr['verdict']}</span></div>",
                            unsafe_allow_html=True,
                        )

                    change_positive = rr["change"] >= 0
                    change_color = "#22c55e" if change_positive else "#ef4444"
                    change_arrow = "▲" if change_positive else "▼"
                    st.markdown(
                        f"<span style='font-size:1.5rem;font-weight:700'>\\${rr['price']}</span> "
                        f"<span style='color:{change_color};font-size:0.85rem;font-weight:600'>"
                        f"{change_arrow} {abs(rr['change'])} ({rr['change_pct']}%)</span>",
                        unsafe_allow_html=True,
                    )

                    candles = ohlc_by_ticker.get(rr["ticker"])
                    if candles:
                        fig = build_candlestick(candles[-40:], interactive=False, height=90)
                        st.plotly_chart(
                            fig,
                            use_container_width=True,
                            config={"staticPlot": True, "displayModeBar": False},
                            key=f"mini_{label}",
                        )
                    else:
                        st.caption("暂无K线数据（运行 fetch_ohlc.py 获取）")

                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:8px;font-size:0.75rem;color:#94a3b8'>"
                        f"<span>评分{rr['score']}</span>"
                        f"<span class='score-track-sm' style='flex:1'>"
                        f"<span class='score-fill' style='width:{rr['score']}%;background:{score_color(rr['score'])}'></span>"
                        f"</span><span>置信{rr['confidence']}</span></div>",
                        unsafe_allow_html=True,
                    )

                    st.button(
                        "查看完整报告 →",
                        key=f"goto_{label}",
                        use_container_width=True,
                        on_click=_goto_report,
                        args=(label,),
                    )

    st.subheader("近期重大事件")
    events = load_macro_events()
    if not events:
        st.caption("未配置宏观事件，编辑 config/macro_events.json 添加。")
    else:
        today = date.today()
        ev_cols = st.columns(min(len(events), 3))
        for col, ev in zip(ev_cols, events):
            ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
            days = (ev_date - today).days
            imminent = days <= 3
            color = "#ef4444" if imminent else "#3b82f6"
            countdown = f"还有 {days} 天" if days >= 0 else f"{-days} 天前"
            with col:
                st.markdown(
                    f"<div class='event-card' style='border-color:{color}'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center'>"
                    f"<b>{esc(ev['name'])}</b>"
                    f"<span class='badge-sm' style='background:{color}'>{countdown}</span>"
                    f"</div>"
                    f"<div style='color:#94a3b8;font-size:0.8rem;margin-top:4px'>{ev['date']}</div>"
                    f"<div style='color:#94a3b8;font-size:0.82rem;margin-top:6px'>{esc(ev['desc'])}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.divider()
    st.caption(
        "⚠️ 风险声明：本报告基于Stocks Intelligence MCP工具返回数据的研究性分析，不构成个性化投资建议。"
        "股票、期权及杠杆/保证金交易可能造成重大本金损失。宏观数据存在滞后，请交易前自行核实关键假设。"
    )


# ============================================================
# 单标的完整报告
# ============================================================
def render_report():
    r = reports[st.session_state.selected_label]

    title_suffix = f"（{esc(r['note'])}）" if r.get("note") else ""
    change_positive = r["change"] >= 0
    change_color = "#22c55e" if change_positive else "#ef4444"
    change_arrow = "▲" if change_positive else "▼"

    top_l, top_r = st.columns([2, 1])
    with top_l:
        st.title(f"📊 {r['ticker']} 交易分析报告{title_suffix}")
        st.markdown(
            f"<span style='font-size:2.2rem;font-weight:700'>\\${r['price']}</span> "
            f"<span style='color:{change_color};font-size:1.2rem;font-weight:600'>"
            f"{change_arrow} {abs(r['change'])} ({r['change_pct']}%)</span>",
            unsafe_allow_html=True,
        )
    with top_r:
        st.markdown(
            f"<div style='text-align:right'>"
            f"<span class='badge' style='background:{verdict_color(r['verdict'])}'>{r['verdict']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='text-align:right;margin-top:6px'>置信度 "
            f"<span style='font-size:1.3rem;letter-spacing:2px'>{CONFIDENCE_DOTS.get(r['confidence'], r['confidence'])}</span>"
            f" ({r['confidence']})</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div style='margin:10px 0 4px 0;font-size:0.9rem;color:#94a3b8'>综合评分 {r['score']} / 100</div>
        <div class='score-track'>
            <div class='score-fill' style='width:{r['score']}%;background:{score_color(r['score'])}'></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='plain-summary' style='background:rgba(59,130,246,0.12);"
        f"border-radius:8px;padding:14px 18px;margin-top:16px'>💬 {esc(r['one_liner'])}</div>",
        unsafe_allow_html=True,
    )

    with st.expander("ℹ️ 数据说明（时间戳 / 数据完整度 / 默认假设）"):
        st.markdown(f"- **数据时间**：{esc(r['as_of'])}")
        st.markdown(f"- **宏观数据时间**：{esc(r['macro_as_of'])} ⚠️可能滞后")
        st.markdown(f"- **数据完整度**：{esc(r['data_completeness'])}")
        st.markdown("- **分析周期**：2-10个交易日波段（默认假设，未特别指定时间周期）")

    tab_k, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "🕯️ K线图",
            "🌍 市场与板块",
            "📈 技术结构",
            "🧮 期权结构",
            "⚖️ 多空证据",
            "🎯 三种情景",
            "📋 交易计划 & 结论",
        ]
    )

    with tab_k:
        candles = ohlc_by_ticker.get(r["ticker"])
        if candles:
            st.caption("可拖动平移 / 滚轮或框选缩放 / 悬停查看具体日期和OHLC数值")
            fig = build_candlestick(candles, interactive=True, height=420)
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"scrollZoom": True, "displaylogo": False},
                key=f"full_{r['ticker']}",
            )
        else:
            st.info("暂无K线数据，运行 `python3 fetch_ohlc.py` 拉取后刷新。")

    with tab1:
        st.subheader("市场与板块环境")
        for line in r["market_context"]:
            st.markdown(f"- {esc(line)}")

    with tab2:
        st.subheader("价格与技术结构")
        st.caption(esc(r["atr_note"]))
        for row in r["tech_table"]:
            item, signal, explain = row
            st.markdown(f"**{esc(item)}**：{esc(signal)}")
            st.markdown(f"<span style='color:#94a3b8'>↳ {esc(explain)}</span>", unsafe_allow_html=True)
        with st.expander("📊 查看原始技术指标表格"):
            st.table(pd.DataFrame(r["tech_table"], columns=["项目", "当前信号", "解释"]))

    with tab3:
        st.subheader(f"期权结构（{r['ticker']}）")
        st.warning(esc(r["options_warning"]))
        for row in r["options_table"]:
            metric, value, explain = row
            st.markdown(f"**{esc(metric)}**：{esc(value)}")
            st.markdown(f"<span style='color:#94a3b8'>↳ {esc(explain)}</span>", unsafe_allow_html=True)
        with st.expander("📊 查看原始期权数据表格"):
            st.table(pd.DataFrame(r["options_table"], columns=["指标", "数值", "解读"]))

    with tab4:
        st.subheader("多空证据对照")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🟢 看多证据**")
            for e in r["bull_evidence"]:
                st.markdown(
                    f"<div class='evidence-card' style='border-color:#22c55e'>{esc(e)}</div>",
                    unsafe_allow_html=True,
                )
        with c2:
            st.markdown("**🔴 看空证据**")
            for e in r["bear_evidence"]:
                st.markdown(
                    f"<div class='evidence-card' style='border-color:#ef4444'>{esc(e)}</div>",
                    unsafe_allow_html=True,
                )

    with tab5:
        st.subheader("三种情景（概率合计100%）")

        scenario_colors = {"多头": "#22c55e", "中性/区间": "#f59e0b", "空头": "#ef4444"}
        segments = ""
        legend = ""
        for name, prob, *_ in r["scenarios"]:
            pct = prob.replace("%", "").strip()
            color = scenario_colors.get(name, "#94a3b8")
            segments += f"<div style='width:{pct}%;background:{color};height:100%;display:inline-block'></div>"
            legend += (
                f"<span style='color:{color};font-weight:600;margin-right:18px'>"
                f"● {esc(name)} {esc(prob)}</span>"
            )
        st.markdown(
            f"<div style='display:flex;height:24px;border-radius:8px;overflow:hidden;margin-bottom:8px'>{segments}</div>"
            f"<div style='margin-bottom:16px'>{legend}</div>",
            unsafe_allow_html=True,
        )

        for name, prob, trigger, target, invalid in r["scenarios"]:
            color = scenario_colors.get(name, "#94a3b8")
            st.markdown(
                f"<div class='evidence-card' style='border-color:{color}'>"
                f"<b style='color:{color}'>{esc(name)}（{esc(prob)}）</b><br>"
                f"触发条件：{esc(trigger)}<br>目标区域：{esc(target)}<br>失效条件：{esc(invalid)}"
                f"</div>",
                unsafe_allow_html=True,
            )

    with tab6:
        st.subheader("交易计划")
        plan_icons = {
            "激进型入场": "🔥",
            "确认型入场": "✅",
            "不追价区域": "🚫",
            "止损/失效位置": "🛑",
            "第一目标位": "🎯",
            "第二目标位": "🎯",
            "风险收益比": "⚖️",
            "建议最大风险预算": "💰",
        }
        for k, v in r["plan"].items():
            icon = plan_icons.get(k, "•")
            st.markdown(f"{icon} **{esc(k)}**：{esc(v)}")

        st.divider()
        st.subheader("最终判断")
        for q, a in r["final_judgement"]:
            st.markdown(f"**❓ {esc(q)}**")
            st.markdown(esc(a))

    st.divider()
    st.caption(
        "⚠️ 风险声明：本报告基于Stocks Intelligence MCP工具返回数据的研究性分析，不构成个性化投资建议。"
        "股票、期权及杠杆/保证金交易可能造成重大本金损失。宏观数据存在滞后，请交易前自行核实关键假设。"
    )


if view_mode == "🏠 首页总览":
    render_home()
else:
    render_report()
