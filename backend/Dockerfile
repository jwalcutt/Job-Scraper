FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Playwright browsers (needed for company career page scraping)
# Install Chromium system deps manually; skip --with-deps to avoid renamed/missing
# font packages on Debian Trixie (ttf-unifont → fonts-unifont, ttf-ubuntu removed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-unifont \
    fonts-freefont-ttf \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*
RUN playwright install chromium

COPY . .

RUN chmod +x /app/scripts/start.sh

EXPOSE 8000
CMD ["/app/scripts/start.sh"]
