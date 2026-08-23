FROM python:3.12-slim

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ ./config/
COPY src/ ./src/
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV LM_STUDIO_HOST=host.docker.internal
ENV LM_STUDIO_PORT=1234
ENV RULER_MODEL=qwen3.6-27b
ENV CROWD_MODEL=google/gemma-4-e4b
ENV ZUNDA_AI_DIR=/models

VOLUME ["/workspace/logs", "/workspace/checkpoints", "/models"]

ENTRYPOINT ["./entrypoint.sh"]
CMD ["--standard", "zunda", "--start", "1603-01", "--end", "2026-08"]
