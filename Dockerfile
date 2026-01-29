FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code package
COPY src/ ./src/

# Copy application entry points
COPY scraper.py .
COPY videoGenerator.py .
COPY list_models.py .

# Copy configuration files
COPY .env .
COPY data/ ./data/

# Create output directories
RUN mkdir -p insights_idosos roteiros

# Default command
CMD ["python", "scraper.py"]
