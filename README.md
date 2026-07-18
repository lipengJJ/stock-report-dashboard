# Stock Report Dashboard

固定渲染代码 + JSON 数据驱动的美股交易分析报告看板（Streamlit）。
新增一支标的的分析后，只需要往 `data/` 目录里加一个 JSON 文件，`dashboard.py` 不需要改动。

## 目录结构

```
.
├── dashboard.py          # 固定不变的渲染逻辑
├── data/                 # 每份报告一个 json，文件名建议 <TICKER>_<YYYYMMDD>.json
│   ├── QQQ_20260718.json
│   └── AAPL_20260718.json
├── requirements.txt
├── Dockerfile            # 内含 Python + Streamlit + Node.js + Claude Code CLI
├── docker-compose.yml
└── .dockerignore
```

## 本地运行

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

浏览器打开 http://localhost:8501 ，侧边栏下拉切换不同标的/日期的报告，点"🔄 刷新数据"可在不重启进程的情况下加载新增的 json。

## Docker 部署

镜像内打包了 Streamlit 看板 **和** Claude Code CLI，方便直接在容器内跑分析、产出新的 `data/*.json`，看板立即可见（无需重新构建镜像）。

### 1. 构建镜像

```bash
docker compose build
```

### 2. 配置 Claude CLI 鉴权（二选一）

- **方式A（推荐，复用本机已登录状态）**：`docker-compose.yml` 里已经挂载了 `~/.claude` 和 `~/.claude.json`，只要你本机的 `claude` 已经登录过，容器内直接可用，无需重复认证。
- **方式B（API Key）**：新建 `.env` 文件（不要提交到git）：
  ```
  ANTHROPIC_API_KEY=sk-ant-xxxx
  ```

### 3. 启动服务

```bash
docker compose up -d
```

浏览器访问 `http://<部署机器IP>:8501` 即可看到渲染好的报告。

### 4. 在容器内生成新报告

Prompt已固定在 `run_analysis.md` 里，要分析哪些标的改 `config/tickers.json` 就行，不需要每次手写prompt：

```bash
docker compose exec stock-dashboard bash
./analyze.sh
```

`config/tickers.json` 示例：
```json
{
  "tickers": ["AAPL", "QQQ", "NVDA"],
  "period": "2-10个交易日波段"
}
```

改完这个文件、跑一次 `./analyze.sh`，就会把里面列出的所有标的都跑一遍分析，写入 `data/<TICKER>_<YYYYMMDD>.json`。生成完成后回到浏览器点"🔄 刷新数据"即可看到新标的。

也可以把 `./analyze.sh` 包装成宿主机的 cron / 定时任务，通过 `docker compose exec stock-dashboard ./analyze.sh` 定时触发。

## data/*.json 字段说明

字段结构以 `data/AAPL_20260718.json` 为例，`dashboard.py` 按以下 key 读取：

| 字段 | 说明 |
|---|---|
| `ticker` / `note` | 标的代码 / 备注（如"纳斯达克100代理"） |
| `as_of` / `macro_as_of` | 数据时间戳 / 宏观数据时间戳 |
| `price` / `change` / `change_pct` | 现价 / 涨跌额 / 涨跌幅 |
| `verdict` / `score` / `confidence` / `data_completeness` | 综合判断 / 评分(0-100) / 置信度 / 数据完整度 |
| `one_liner` | 一句话结论 |
| `market_context` | 字符串数组，市场与板块环境要点 |
| `tech_table` | 二维数组 `[项目, 当前信号, 解释]` |
| `atr_note` | ATR/历史统计补充说明 |
| `options_table` | 二维数组 `[指标, 数值, 解读]` |
| `options_warning` | 期权维度的限制/警告说明 |
| `bull_evidence` / `bear_evidence` | 字符串数组 |
| `scenarios` | 二维数组 `[情景, 概率, 触发条件, 目标区域, 失效条件]`，概率合计需为100% |
| `plan` | 对象，key为计划项名称，value为说明文本 |
| `final_judgement` | 二维数组 `[问题, 回答]` |

## 安全提示

- `.env`、`~/.claude.json` 含有鉴权凭据，已加入 `.gitignore` / `.dockerignore`，不要提交到 git 或打进镜像里。
- 本报告为工具数据驱动的研究性分析，不构成个性化投资建议。
# stock-report-dashboard
