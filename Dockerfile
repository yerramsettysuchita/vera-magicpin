FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Runtime configuration
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080

EXPOSE 8080

# Health check matches judge's 60s polling interval
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/v1/healthz')" || exit 1

CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
