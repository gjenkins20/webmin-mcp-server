FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir .

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/webmin-mcp /usr/local/bin/webmin-mcp
COPY src/ src/

# Create non-root user
RUN useradd --create-home --shell /bin/bash mcp
USER mcp

ENTRYPOINT ["python", "-m", "src.server"]
