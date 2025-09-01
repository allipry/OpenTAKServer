# OpenTAKServer API Server

This module contains the custom API server implementation for OpenTAKServer with enhanced dashboard compatibility and real-time monitoring capabilities.

## Features

- **Dashboard API Endpoints**: Compatible with OpenTAK UI dashboard
- **Real-time Monitoring**: System metrics (CPU, memory, disk usage)
- **Socket.IO Support**: Real-time updates for dashboard
- **Authentication**: Mock authentication for development/testing
- **QR Code Generation**: Support for iTAK and ATAK QR codes
- **Health Checks**: Comprehensive health monitoring
- **Metrics Export**: Prometheus-compatible metrics endpoint

## API Endpoints

### Core Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /api/status` - Comprehensive system status
- `GET /metrics` - Prometheus metrics

### Authentication
- `GET|POST /api/login` - Login endpoint
- `POST /api/logout` - Logout endpoint
- `GET /api/auth/status` - Authentication status

### System Monitoring
- `GET /api/system` - System metrics
- `GET /api/cpu` - CPU metrics
- `GET /api/memory` - Memory metrics
- `GET /api/disk` - Disk metrics
- `GET /api/uptime` - Server uptime

### TAK Integration
- `GET|POST /api/itak_qr_string` - iTAK QR code generation
- `GET|POST /api/atak_qr_string` - ATAK QR code generation
- `GET /Marti/api/version` - Marti API version
- `GET /Marti/api/tls/config` - TLS configuration

### Dashboard Data
- `GET /api/eud` - End User Devices
- `GET /api/missions` - Missions data
- `GET /api/alerts` - Alerts data
- `GET /api/data_packages` - Data packages
- `GET /api/video_streams` - Video streams

## Socket.IO Events

The server emits various real-time events:
- `status_update` - Complete system status
- `metrics_update` - System metrics
- `cpu_update` - CPU metrics
- `memory_update` - Memory metrics
- `disk_update` - Disk metrics
- `uptime_update` - Uptime information

## Configuration

The server uses environment variables for configuration:

### Server Settings
- `OTS_LISTENER_ADDRESS` - Server bind address (default: 0.0.0.0)
- `OTS_LISTENER_PORT` - Server port (default: 8080)
- `FLASK_DEBUG` - Debug mode (default: false)

### Database Settings
- `POSTGRES_HOST` - PostgreSQL host (default: postgresql)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `POSTGRES_DB` - Database name (default: opentakserver)
- `POSTGRES_USER` - Database user (default: ots)
- `POSTGRES_PASSWORD` - Database password (default: changeme)

### RabbitMQ Settings
- `RABBITMQ_HOST` - RabbitMQ host (default: rabbitmq)
- `RABBITMQ_PORT` - RabbitMQ port (default: 5672)
- `RABBITMQ_USER` - RabbitMQ user (default: ots)
- `RABBITMQ_PASSWORD` - RabbitMQ password (default: changeme)
- `RABBITMQ_VHOST` - RabbitMQ virtual host (default: ots)

## Usage

### Direct Execution
```bash
python3 -m opentakserver.api_server.server
```

### Using Poetry
```bash
poetry run opentakserver-api
```

### Docker
```bash
docker build -t opentakserver-core .
docker run -p 8080:8080 opentakserver-core
```

## Development

The API server is designed to be compatible with the OpenTAK UI dashboard while providing enhanced monitoring and real-time capabilities. It includes comprehensive error handling and fallback mechanisms to ensure reliability.

### Key Components

1. **fixed_server.py** - Main server implementation
2. **server.py** - Entry point module
3. **config.py** - Configuration management
4. **start.sh** - Startup script with dependency checks

### Testing

The server includes health checks and can be tested using:
```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/status
```