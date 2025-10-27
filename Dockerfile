FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies (excluding dev and bot dependencies)
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --without dev --without bot

# Copy application code
COPY app/ ./app/

# Create media directory for uploaded files
RUN mkdir -p /app/media

# Create log directory
RUN mkdir -p /app/log && chmod 777 /app/log

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]