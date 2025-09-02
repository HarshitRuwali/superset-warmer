FROM ghcr.io/astral-sh/uv:debian

WORKDIR /app

COPY pyproject.toml .
COPY uv.lock .
COPY main.py .

VOLUME ["/app", "/config"]

# Install required packages
RUN apt-get update && \
    apt-get install -y wget gnupg ca-certificates fonts-unifont && \
    rm -rf /var/lib/apt/lists/*

RUN uv sync

RUN uv run playwright install --with-deps chromium

CMD ["uv", "run", "main.py"]
