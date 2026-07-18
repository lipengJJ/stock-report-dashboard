#!/usr/bin/env bash
# 在容器内执行：./analyze.sh
# 读取 run_analysis.md 作为固定prompt，config/tickers.json 里配置要分析的标的
set -euo pipefail
cd "$(dirname "$0")"
claude -p "$(cat run_analysis.md)"
