FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Download basic NLTK corpora for heuristic metrics
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)"

# Copy application source code
COPY . .

# Expose default port
EXPOSE 8080

# Default command
CMD ["bash", "-c", "uvicorn evalforge.main:app --host 0.0.0.0 --port 8080"]
