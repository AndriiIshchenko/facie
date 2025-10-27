FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies (only bot dependencies)
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only bot --only main

# Copy bot code
COPY bot/ ./bot/

# Create log directory
RUN mkdir -p /app/log && chmod 777 /app/log

# Set default environment variables
ENV TELEGRAM_BOT_TOKEN=""
ENV BACKEND_BASE_URL="http://api:8000"

# Run the bot
CMD ["python", "-m", "bot.main"]