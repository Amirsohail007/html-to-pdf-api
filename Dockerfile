FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/lib/playwright
# Add environment variables to optimize Playwright
ENV PYTHONUNBUFFERED=1
ENV NODE_OPTIONS="--max-old-space-size=1024"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    xz-utils \
    xvfb \
    libnss3 \
    libatk-bridge2.0-0 \
    libxss1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libstdc++6 \
    libxcomposite1 \
    libfontconfig1 \
    fonts-liberation \
    fontconfig \
    fonts-dejavu \
    fonts-freefont-ttf \
    libgbm1 \
    libasound2 \
    # wkhtmltopdf \
    procps \
    # Add optimization packages
    ca-certificates \
    dbus-x11 \
    libdrm2 \
    libgles2 \
    libglib2.0-0 \
    && wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && dpkg -i wkhtmltox_0.12.6.1-3.bookworm_amd64.deb || apt-get install -f -y \
    && rm wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Update font cache
RUN fc-cache -f -v

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional packages that Playwright needs
RUN apt-get update && apt-get install -y \
    fonts-unifont \
    libcups2 \
    libxkbcommon0 \
    libxdamage1 \
    libxfixes3 \
    libpango-1.0-0 \
    libcairo2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Playwright with chromium browser only (skip deps to avoid font conflicts)
RUN pip install playwright && playwright install chromium

# Copy code
COPY . .

# Expose app port
EXPOSE 8000

# Run the app with Gunicorn + Uvicorn workers and OpenTelemetry instrumentation
# CMD ["opentelemetry-instrument", "gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "--preload", "-b", "0.0.0.0:8000", "--timeout", "120", "src.main:app"]
CMD ["opentelemetry-instrument", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
