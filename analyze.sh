#!/usr/bin/env bash
# 在容器内执行：./analyze.sh
# 读取 run_analysis.md 作为固定prompt，config/tickers.json 里配置要分析的标的
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p logs
LOG_FILE="logs/analyze_$(date +%Y%m%d_%H%M%S).log"

echo "开始执行分析任务，日志文件：$LOG_FILE"
claude -p "$(cat run_analysis.md)" --verbose 2>&1 | tee "$LOG_FILE"
echo "执行完成，日志已保存到 $LOG_FILE"
