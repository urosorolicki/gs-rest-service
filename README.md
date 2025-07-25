# GS Rest Service DevOps Implementation

This repository contains the complete DevOps implementation for the GS Rest Service project, including Docker containerization, CI/CD pipelines, deployment automation, and monitoring.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Git Repository │    │   Jenkins CI    │    │  Deployment     │
│   (Source Code)  │───▶│   Pipeline      │───▶│  Server         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Slack           │    │ Docker Registry │    │ Monitoring      │
│ Notifications   │    │ (Images)        │    │ Service         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🐳 Task 1 - Docker Implementation

### Features
- **Multi-stage build** for minimal image size
- **Security hardened** with non-root user
- **Health checks** built-in
- **JVM optimization** for containers
- **Port mapping** from 8080 to 777

### Files
- `complete/Dockerfile` - Multi-stage Docker build
- `complete/.dockerignore` - Build optimization
- `complete/docker-compose.yml` - Local testing

### Usage
```bash
# Build image
cd complete
docker build -t gs-rest-service:latest .

# Run locally
docker-compose up -d

# Test service
curl http://localhost:777/greeting
```

## 🔄 Task 2 - Jenkins CI/CD

### Pipeline Features
- **Multi-branch support** (master/main and develop)
- **Automated testing** with result reporting
- **Docker image building** and testing
- **Slack notifications** for all stages
- **Artifact archiving**
- **Automatic deployment** triggering

### Files
- `Jenkinsfile` - Main CI pipeline
- `Jenkinsfile.deploy` - Deployment pipeline

### Pipeline Stages
1. **Checkout** - Clone repository and send start notification
2. **Build** - Maven compilation
3. **Test** - Run unit tests with reporting
4. **Package** - Create JAR artifact
5. **Docker Build** - Build and tag container image
6. **Docker Test** - Test container functionality
7. **Trigger Deployment** - Start deployment job (main branch only)

### Jenkins Setup
```groovy
// Required Jenkins plugins:
// - Pipeline
// - Git
// - Maven Integration
// - Docker Pipeline
// - Slack Notification
// - Test Results Analyzer

// Required tools:
// - Maven 3.9.6
// - OpenJDK 17
// - Docker

// Required credentials:
// - slack-webhook-url
// - deployment-server-ssh
// - docker-registry (if using private registry)
```

## 🚀 Task 3 - Deployment Automation

### Bash Deployment Script (`deploy.sh`)
Comprehensive deployment script with multiple options:

```bash
# Local deployment with build
./deploy.sh --local --build

# Remote deployment
./deploy.sh --server myserver.com --user deploy --build

# Dry run
./deploy.sh --server myserver.com --dry-run

# Help
./deploy.sh --help
```

### Python Deployment Script (`deploy.py`)
Advanced deployment with better error handling:

```bash
# Install dependencies
pip install -r requirements.txt

# Deploy locally
python3 deploy.py --local --build

# Deploy to remote server
python3 deploy.py --server myserver.com --user deploy --build
```

### Features
- **Local and remote deployment**
- **SSH-based remote execution**
- **Health checks**
- **Rollback capabilities**
- **Dry-run mode**
- **Comprehensive logging**

## 📊 Task 4 - Monitoring

### Bash Monitor (`monitor.sh`)
Lightweight monitoring with Slack integration:

```bash
# Start monitoring
./monitor.sh --url http://localhost:777/greeting

# Run as daemon
./monitor.sh --url http://localhost:777/greeting --daemon

# With Slack notifications
./monitor.sh --url http://localhost:777/greeting \
  --slack-webhook https://hooks.slack.com/services/YOUR/WEBHOOK
```

### Python Monitor (`monitor.py`)
Advanced monitoring with better daemon management:

```bash
# Install dependencies
pip install -r requirements.txt

# Start monitoring
python3 monitor.py --url http://localhost:777/greeting

# Daemon management
python3 monitor.py --daemon start --url http://localhost:777/greeting
python3 monitor.py --daemon status
python3 monitor.py --daemon stop
```

### Monitoring Features
- **HTTP health checks**
- **Configurable intervals and timeouts**
- **Retry logic**
- **Status change detection**
- **Slack notifications**
- **Daemon mode**
- **Comprehensive logging**
- **Graceful shutdown**

## 📁 Project Structure

```
gs-rest-service/
├── complete/                    # Main application
│   ├── src/                     # Source code
│   ├── Dockerfile              # Container definition
│   ├── .dockerignore           # Docker build optimization
│   ├── docker-compose.yml      # Local testing
│   └── pom.xml                 # Maven configuration
├── Jenkinsfile                 # CI pipeline
├── Jenkinsfile.deploy          # Deployment pipeline
├── deploy.sh                   # Bash deployment script
├── deploy.py                   # Python deployment script
├── monitor.sh                  # Bash monitoring script
├── monitor.py                  # Python monitoring script
├── requirements.txt            # Python dependencies
├── config.env                  # Configuration template
└── README.md                   # This file
```

## 🔧 Configuration

### Environment Variables
Copy `config.env` and customize:

```bash
# Copy configuration template
cp config.env .env

# Edit configuration
nano .env

# Source configuration
source .env
```

### Slack Setup
1. Create Slack workspace
2. Create channels: `#gs-rest-service-ci` and `#gs-rest-service-monitor`
3. Create incoming webhook
4. Configure webhook URL in scripts

### Jenkins Setup
1. Install required plugins
2. Configure tools (Maven, JDK, Docker)
3. Create multibranch pipeline job
4. Configure webhook for Git repository
5. Add required credentials

## 🔐 Security Considerations

- **Non-root containers** for reduced attack surface
- **SSH key-based authentication** for deployments
- **Secrets management** via Jenkins credentials
- **Network security** with proper firewall rules
- **Resource limits** in container configuration

## 📈 Monitoring and Alerting

### Health Check Endpoint
```bash
curl http://your-server:777/greeting
```

### Log Files
- Application logs: Container logs via `docker logs`
- Deployment logs: `deploy.log`
- Monitor logs: `monitor.log`
- Jenkins logs: Jenkins job console output

### Slack Notifications
- **CI Pipeline**: Build start, test results, build completion
- **Monitoring**: Service down/up alerts with timestamps

## 🚀 Getting Started

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-username/gs-rest-service.git
   cd gs-rest-service
   ```

2. **Local Testing**
   ```bash
   cd complete
   docker-compose up -d
   curl http://localhost:777/greeting
   ```

3. **Setup Jenkins**
   - Install Jenkins with required plugins
   - Create multibranch pipeline
   - Configure webhooks

4. **Deploy to Server**
   ```bash
   ./deploy.sh --server your-server.com --user deploy --build
   ```

5. **Start Monitoring**
   ```bash
   ./monitor.sh --url http://your-server.com:777/greeting --daemon
   ```

## 🛠️ Troubleshooting

### Common Issues

1. **Docker build fails**
   - Check Dockerfile syntax
   - Verify base image availability
   - Check network connectivity

2. **Deployment fails**
   - Verify SSH connectivity
   - Check server resources
   - Review deployment logs

3. **Monitoring alerts**
   - Check service status: `docker ps`
   - Review application logs: `docker logs gs-rest-service`
   - Verify network connectivity

4. **Jenkins pipeline fails**
   - Check tool configurations
   - Verify credentials
   - Review console output

### Log Locations
- Container logs: `docker logs gs-rest-service`
- Deployment logs: `deploy.log`
- Monitor logs: `monitor.log`
- Jenkins logs: Job console output

## 📚 Best Practices

- **Version tagging** for Docker images
- **Blue-green deployments** for zero-downtime
- **Resource monitoring** for capacity planning
- **Regular backups** of configurations
- **Security updates** for base images
- **Documentation maintenance**
