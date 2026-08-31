FROM golang:1.26.5-alpine AS grafana-mcp
RUN CGO_ENABLED=0 go install github.com/grafana/mcp-grafana/cmd/mcp-grafana@v1.3.0

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=grafana-mcp /go/bin/mcp-grafana /usr/local/bin/mcp-grafana
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
RUN pip install --no-cache-dir .
USER 65532:65532
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
