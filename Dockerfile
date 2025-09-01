FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/certs /app/logs /app/data

# Make startup script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_ENV=production
ENV FLASK_DEBUG=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the server
CMD ["./start.sh"]