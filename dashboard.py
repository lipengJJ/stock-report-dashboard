"""
固定不变的渲染代码。
新增标的分析后，只需在 data/ 目录下新增一个 <TICKER>_<YYYYMMDD>.json 文件，
无需修改本文件。
"""
import json
import glob
import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="交易分析报告 Dashboard", layout="wide")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

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
    .score-track {
        background: rgba(148,163,184,0.2);
        border-radius: 999px;
        height: 14px;
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
    </style>
    """,
    unsafe_allow_html=True,
)


def _data_dir_fingerprint():
    """基于文件名+mtime生成签名，data/目录有新增或修改的json时自动使缓存失效。"""
    paths = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
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


reports = load_reports(_data_dir_fingerprint())

if not reports:
    st.error(f"未在 {DATA_DIR} 找到任何报告数据（*.json）")
    st.stop()

st.sidebar.title("📁 报告选择")
if st.sidebar.button("🔄 刷新数据"):
    st.cache_data.clear()
    st.rerun()
selected_label = st.sidebar.selectbox("选择标的 / 日期", list(reports.keys()))
r = reports[selected_label]

# ---------- 顶部：标题 + 价格 ----------
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

# ---------- 综合评分：色阶进度条，跟评分标准的5档配色一致 ----------
st.markdown(
    f"""
    <div style='margin:10px 0 4px 0;font-size:0.9rem;color:#94a3b8'>综合评分 {r['score']} / 100</div>
    <div class='score-track'>
        <div class='score-fill' style='width:{r['score']}%;background:{score_color(r['score'])}'></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- 一句话结论（给新手看的最重要一句话） ----------
st.markdown(
    f"<div class='plain-summary' style='background:rgba(59,130,246,0.12);"
    f"border-radius:8px;padding:14px 18px;margin-top:16px'>💬 {esc(r['one_liner'])}</div>",
    unsafe_allow_html=True,
)

# ---------- 数据时间/完整度/默认假设，折叠起来不占地方 ----------
with st.expander("ℹ️ 数据说明（时间戳 / 数据完整度 / 默认假设）"):
    st.markdown(f"- **数据时间**：{esc(r['as_of'])}")
    st.markdown(f"- **宏观数据时间**：{esc(r['macro_as_of'])} ⚠️可能滞后")
    st.markdown(f"- **数据完整度**：{esc(r['data_completeness'])}")
    st.markdown("- **分析周期**：2-10个交易日波段（默认假设，未特别指定时间周期）")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["🌍 市场与板块", "📈 技术结构", "🧮 期权结构", "⚖️ 多空证据", "🎯 三种情景", "📋 交易计划 & 结论"]
)

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
