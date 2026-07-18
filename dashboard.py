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

# ---------- 页面 ----------
title_suffix = f"（{r['note']}）" if r.get("note") else ""
st.title(f"📊 {r['ticker']} 交易分析报告{title_suffix}")
st.caption(
    f"数据时间：{r['as_of']} ｜ 宏观数据：{r['macro_as_of']} ⚠️已滞后 ｜ 分析周期：2-10个交易日波段（默认假设）"
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("当前价格", f"${r['price']}", f"{r['change']} ({r['change_pct']}%)")
col2.metric("综合判断", r["verdict"])
col3.metric("综合评分", f"{r['score']} / 100")
col4.metric("置信度", r["confidence"])
col5.metric("数据完整度", r["data_completeness"].split("（")[0])

st.info(f"一句话结论：{r['one_liner']}")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["市场与板块", "技术结构", "期权结构", "多空证据", "三种情景", "交易计划 & 结论"]
)

with tab1:
    st.subheader("市场与板块环境")
    for line in r["market_context"]:
        st.markdown(f"- {line}")

with tab2:
    st.subheader("价格与技术结构")
    st.table(pd.DataFrame(r["tech_table"], columns=["项目", "当前信号", "解释"]))
    st.caption(r["atr_note"])

with tab3:
    st.subheader(f"期权结构（{r['ticker']}）")
    st.table(pd.DataFrame(r["options_table"], columns=["指标", "数值", "解读"]))
    st.warning(r["options_warning"])

with tab4:
    st.subheader("多空证据对照")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**看多证据**")
        for e in r["bull_evidence"]:
            st.markdown(f"- {e}")
    with c2:
        st.markdown("**看空证据**")
        for e in r["bear_evidence"]:
            st.markdown(f"- {e}")

with tab5:
    st.subheader("三种情景（概率合计100%）")
    st.table(
        pd.DataFrame(
            r["scenarios"], columns=["情景", "概率", "触发条件", "目标区域", "失效条件"]
        )
    )

with tab6:
    st.subheader("交易计划")
    for k, v in r["plan"].items():
        st.markdown(f"**{k}**：{v}")

    st.divider()
    st.subheader("最终判断")
    for q, a in r["final_judgement"]:
        st.markdown(f"**{q}** {a}")

st.divider()
st.caption(
    "⚠️ 风险声明：本报告基于Stocks Intelligence MCP工具返回数据的研究性分析，不构成个性化投资建议。"
    "股票、期权及杠杆/保证金交易可能造成重大本金损失。宏观数据存在滞后，请交易前自行核实关键假设。"
)
