FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Render injects PORT env var (default 10000)
ENV PORT=10000

EXPOSE ${PORT}

CMD uvicorn app.core.server:app --host 0.0.0.0 --port ${PORT}
