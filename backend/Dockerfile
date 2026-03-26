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
RUN playwright install chromium --with-deps

COPY . .

RUN chmod +x /app/scripts/start.sh

EXPOSE 8000
CMD ["/app/scripts/start.sh"]
