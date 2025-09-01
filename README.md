# OpenTAKServer - Core Fork

![GitHub Release Date](https://img.shields.io/github/release-date/allipry/OpenTAKServer)
![GitHub Tag](https://img.shields.io/github/v/tag/allipry/OpenTAKServer)

This is a fork of OpenTAKServer (OTS) with consolidated local modifications and enhanced API server functionality. This repository serves as the source of truth for the core OpenTAKServer container builds.

**Original Project**: [brian7704/OpenTAKServer](https://github.com/brian7704/OpenTAKServer)  
**Join the community**: [Discord server](https://discord.gg/6uaVHjtfXN)

## Fork Enhancements

This fork includes the following enhancements over the original:

- **Enhanced API Server**: Integrated `fixed_server.py` with improved API endpoint handling
- **Container-Ready**: Optimized for containerized deployment with Docker
- **Configuration Management**: Enhanced environment variable support for container orchestration
- **Startup Scripts**: Improved startup procedures for reliable container initialization

## Current Features
- Connect via TCP from ATAK, WinTAK, and iTAK
- SSL
- Authentication
- [WebUI with a live map](https://github.com/brian7704/OpenTAKServer-UI)
- Client certificate enrollment
- Send and receive messages
- Send and receive points
- Send and receive routes
- Send and receive images
- Share location with other users
- Save CoT messages to a database
- Data Packages
- Alerts
- CasEvac
- Optional Mumble server authentication
  - Use your OpenTAKServer username and password to log into your Mumble server
- Video Streaming
- Mission API
  - Data Sync plugin
  - Fire Area Survey plugin

## Planned Features
- Federation
- Groups/Channels

## Requirements
- RabbitMQ
- MediaMTX (Only required for video streaming)
- openssl
- nginx

## Container Usage

This repository is designed to be used as a source for Docker container builds. The recommended way to use this fork is through the consolidated deployment project.

### Docker Build

```bash
# Build the container directly from this repository
docker build -t opentakserver-core:latest .

# Or use in docker-compose.yml
services:
  opentakserver-core:
    build:
      context: https://github.com/allipry/OpenTAKServer.git#v1.0.0-consolidation
    environment:
      - OTS_DB_URL=postgresql://user:pass@db:5432/opentakserver
      - OTS_SECRET_KEY=your-secret-key
    ports:
      - "8080:8080"
      - "8089:8089"
```

### Environment Variables

Key environment variables for container deployment:

- `OTS_DB_URL`: Database connection string
- `OTS_SECRET_KEY`: Application secret key
- `OTS_DEBUG`: Enable debug mode (default: false)
- `OTS_HOST`: Host to bind to (default: 0.0.0.0)
- `OTS_PORT`: Port to bind to (default: 8080)

### API Server Features

The enhanced API server (`fixed_server.py`) provides:

- Improved error handling and logging
- Enhanced CORS support for web UI integration
- Better environment variable configuration
- Optimized startup procedures for containers
- Health check endpoints for container orchestration

## Installation (Standalone)

For standalone installations, refer to the original project documentation. The following installers work with the upstream version:

## Documentation

https://docs.opentakserver.io

## Supporting the project

If you would like to support the project you can do so [here](https://buymeacoffee.com/opentakserver)
###
 Ubuntu

`curl https://i.opentakserver.io/ubuntu_installer -Ls | bash -`

### Raspberry Pi

`curl https://i.opentakserver.io/raspberry_pi_installer -Ls | bash -`

### Rocky 9

`curl -s -L https://i.opentakserver.io/rocky_linux_installer | bash -`

### Windows

Open PowerShell as an administrator and run the following command

`Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://i.opentakserver.io/windows_installer'))`

### MacOS

`curl -Ls https://i.opentakserver.io/macos_installer | bash -`

## Development

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/allipry/OpenTAKServer.git
cd OpenTAKServer

# Install dependencies
pip install -r requirements.txt

# Run the enhanced API server
python opentakserver/api_server/fixed_server.py
```

### Container Development

```bash
# Build development container
docker build -t opentakserver-core:dev .

# Run with development settings
docker run -it --rm \
  -e OTS_DEBUG=true \
  -e OTS_DB_URL=sqlite:///tmp/opentakserver.db \
  -p 8080:8080 \
  opentakserver-core:dev
```

## Contributing

This fork maintains compatibility with the upstream OpenTAKServer project. When contributing:

1. Ensure changes don't break container deployment
2. Test with the consolidated deployment project
3. Update documentation for any new environment variables
4. Follow the existing code style and patterns

## Changelog

### v1.0.0-consolidation
- Integrated `fixed_server.py` with enhanced API functionality
- Added container-optimized startup scripts
- Improved environment variable configuration
- Enhanced error handling and logging
- Added health check endpoints for container orchestration

## License

This project maintains the same license as the original OpenTAKServer project.