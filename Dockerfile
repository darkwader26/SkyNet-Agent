FROM python:3.11-slim

WORKDIR /app

# Install curl for web_search tool
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory
RUN mkdir -p data

# Run
ENTRYPOINT ["python", "main.py"]
CMD []
