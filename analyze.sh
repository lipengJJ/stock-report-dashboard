#!/usr/bin/env bash
# 在容器内执行：./analyze.sh
# 读取 run_analysis.md 作为固定prompt，config/tickers.json 里配置要分析的标的
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p logs
LOG_FILE="logs/analyze_$(date +%Y%m%d_%H%M%S).log"

# headless模式(claude -p)没有交互终端，无法手动点信任弹窗，
# 提前把 /app 标记为已信任，否则 .claude/settings.json 里的 permissions.allow 会被忽略。
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path.home() / ".claude.json"
data = json.loads(p.read_text()) if p.exists() and p.stat().st_size > 0 else {}
data.setdefault("projects", {})
data["projects"].setdefault("/app", {})["hasTrustDialogAccepted"] = True
p.write_text(json.dumps(data, indent=2))
EOF

echo "开始执行分析任务，日志文件：$LOG_FILE"
# claude的输出对象是管道(tee)而非终端时，很多程序会切成全缓冲，导致日志文件长时间看起来是空的。
# 用stdbuf强制成行缓冲，保证tee能实时写入。
stdbuf -oL -eL claude -p "$(cat run_analysis.md)" --verbose 2>&1 | tee "$LOG_FILE"
echo "执行完成，日志已保存到 $LOG_FILE"
