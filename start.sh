#!/bin/bash
set -e

echo "Starting Fixed OpenTAKServer API..."

# Set environment variables
export PYTHONPATH=/app
export FLASK_ENV=production
export FLASK_DEBUG=false

# Database configuration - parse from DATABASE_URL if available
if [ -n "$DATABASE_URL" ]; then
    # Extract database details from DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    DB_REGEX="postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+)"
    if [[ $DATABASE_URL =~ $DB_REGEX ]]; then
        export POSTGRES_USER="${BASH_REMATCH[1]}"
        export POSTGRES_PASSWORD="${BASH_REMATCH[2]}"
        export POSTGRES_HOST="${BASH_REMATCH[3]}"
        export POSTGRES_PORT="${BASH_REMATCH[4]}"
        export POSTGRES_DB="${BASH_REMATCH[5]}"
        echo "Parsed DATABASE_URL: host=$POSTGRES_HOST, port=$POSTGRES_PORT, db=$POSTGRES_DB, user=$POSTGRES_USER"
    fi
else
    # Fallback to individual environment variables
    export POSTGRES_HOST=${POSTGRES_HOST:-postgresql}
    export POSTGRES_PORT=${POSTGRES_PORT:-5432}
    export POSTGRES_DB=${POSTGRES_DB:-opentakserver}
    export POSTGRES_USER=${POSTGRES_USER:-ots}
    export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
fi

# RabbitMQ configuration - use environment variables from docker-compose
export RABBITMQ_HOST=${RABBITMQ_HOST:-rabbitmq}
export RABBITMQ_PORT=${RABBITMQ_PORT:-5672}
export RABBITMQ_USER=${RABBITMQ_USER:-ots}
export RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD:-changeme}
export RABBITMQ_VHOST=${RABBITMQ_VHOST:-ots}

# Wait for database with timeout (optional - the fixed server can run without it)
echo "Checking database connectivity..."
timeout=30
counter=0
until python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='$POSTGRES_HOST', 
        port=$POSTGRES_PORT, 
        database='$POSTGRES_DB', 
        user='$POSTGRES_USER', 
        password='$POSTGRES_PASSWORD'
    )
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" 2>/dev/null; do
    if [ $counter -ge $timeout ]; then
        echo "Database connection timeout after ${timeout} seconds - continuing without database"
        break
    fi
    echo "Database not ready, waiting... ($counter/$timeout)"
    sleep 2
    counter=$((counter + 2))
done

# Wait for RabbitMQ with timeout (optional - the fixed server can run without it)
echo "Checking RabbitMQ connectivity..."
counter=0
until python3 -c "
import pika
try:
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host='$RABBITMQ_HOST', 
            port=$RABBITMQ_PORT, 
            virtual_host='$RABBITMQ_VHOST', 
            credentials=pika.PlainCredentials('$RABBITMQ_USER', '$RABBITMQ_PASSWORD')
        )
    )
    connection.close()
    print('RabbitMQ connection successful')
except Exception as e:
    print(f'RabbitMQ connection failed: {e}')
    exit(1)
" 2>/dev/null; do
    if [ $counter -ge $timeout ]; then
        echo "RabbitMQ connection timeout after ${timeout} seconds - continuing without RabbitMQ"
        break
    fi
    echo "RabbitMQ not ready, waiting... ($counter/$timeout)"
    sleep 2
    counter=$((counter + 2))
done

# Create basic SSL certificates for compatibility
echo "Creating basic SSL certificates..."
mkdir -p /app/certs
openssl req -x509 -newkey rsa:2048 -keyout /app/certs/server-key.pem -out /app/certs/server.pem \
    -days 365 -nodes -subj "/C=US/ST=State/L=City/O=OpenTAKServer/CN=localhost" \
    2>/dev/null || echo "Certificate creation failed, continuing..."

# Start the fixed OpenTAKServer
echo "Starting Fixed OpenTAKServer API on port 8080..."
cd /app
python3 -m opentakserver.api_server.server