FROM python:3.11-slim

# --- Node.js + Claude Code CLI（用于容器内直接跑分析生成新的 data/*.json）---
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get purge -y gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard.py .
COPY run_analysis.md .
COPY analyze.sh .
COPY config/ ./config/
COPY data/ ./data/
RUN chmod +x analyze.sh

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
