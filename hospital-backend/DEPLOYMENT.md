# FHIR R5 Hospital IoT Backend - Deployment Guide

## Production Deployment Guide

This guide covers deploying the FHIR R5 Hospital IoT Backend to production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Database Setup](#database-setup)
3. [Application Configuration](#application-configuration)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Environment Variables](#environment-variables)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Security Hardening](#security-hardening)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 100 GB SSD
- OS: Ubuntu 22.04 LTS / CentOS 8 / Windows Server 2022

**Recommended:**
- CPU: 8 cores
- RAM: 16 GB
- Disk: 500 GB NVMe SSD
- OS: Ubuntu 22.04 LTS

### Software Requirements

- Docker 24.0+
- Docker Compose 2.20+
- PostgreSQL 15+ with TimescaleDB 2.11+
- Python 3.11+
- Nginx 1.24+ (for reverse proxy)

---

## Database Setup

### 1. Install PostgreSQL with TimescaleDB

**Ubuntu/Debian:**
```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# Install PostgreSQL 15
sudo apt install postgresql-15 postgresql-contrib-15

# Add TimescaleDB repository
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update

# Install TimescaleDB
sudo apt install timescaledb-2-postgresql-15

# Configure TimescaleDB
sudo timescaledb-tune --quiet --yes
```

**Windows:**
```powershell
# Download and install PostgreSQL 15 from:
# https://www.postgresql.org/download/windows/

# Download and install TimescaleDB from:
# https://docs.timescale.com/install/latest/self-hosted/installation-windows/
```

### 2. Create Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE hospital_iot;
CREATE USER hospital_user WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE hospital_iot TO hospital_user;

# Enable TimescaleDB extension
\c hospital_iot
CREATE EXTENSION IF NOT EXISTS timescaledb;

# Exit
\q
```

### 3. Configure PostgreSQL for Production

Edit `/etc/postgresql/15/main/postgresql.conf`:

```conf
# Connection settings
listen_addresses = '*'
max_connections = 200

# Memory settings
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10485kB
min_wal_size = 1GB
max_wal_size = 4GB

# TimescaleDB settings
timescaledb.max_background_workers = 8
max_worker_processes = 16

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log/postgresql'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

Edit `/etc/postgresql/15/main/pg_hba.conf`:

```conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
host    hospital_iot    hospital_user   0.0.0.0/0               scram-sha-256
host    hospital_iot    hospital_user   ::/0                    scram-sha-256
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 4. Run Database Migration

```bash
cd hospital-backend
python migrate_to_fhir_r5.py
python seed_fhir_data.py
```

---

## Application Configuration

### 1. Create Production Environment File

Create `.env.production`:

```env
# Database
DATABASE_URL=postgresql://hospital_user:your-secure-password@localhost:5432/hospital_iot

# JWT
JWT_SECRET_KEY=your-256-bit-secret-key-here-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# HMS Integration
HMS_BASE_URL=https://hms.hospital.org/api
HMS_API_KEY=your-hms-api-key

# CORS
CORS_ORIGINS=["https://dashboard.hospital.org", "https://mobile.hospital.org"]

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=false
LOG_LEVEL=info

# TimescaleDB
TIMESCALEDB_RETENTION_DAYS=365

# Compliance
AUDIT_RETENTION_YEARS=6
CALIBRATION_RETENTION_YEARS=5

# MQTT (for ESP32 devices)
MQTT_BROKER=mqtt.hospital.org
MQTT_PORT=8883
MQTT_USERNAME=hospital_iot
MQTT_PASSWORD=your-mqtt-password
MQTT_USE_TLS=true

# Redis (for caching and rate limiting)
REDIS_URL=redis://localhost:6379/0

# Sentry (error tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
ENVIRONMENT=production
```

### 2. Generate Secure Secrets

```bash
# Generate JWT secret (256-bit)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate database password
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

---

## Docker Deployment

### 1. Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. Create Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: hospital-postgres
    restart: always
    environment:
      POSTGRES_DB: hospital_iot
      POSTGRES_USER: hospital_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      TIMESCALEDB_TELEMETRY: off
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    networks:
      - hospital-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hospital_user -d hospital_iot"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: hospital-redis
    restart: always
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    networks:
      - hospital-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: hospital-backend
    restart: always
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - hospital-network
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:1.24-alpine
    container_name: hospital-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - backend
    networks:
      - hospital-network

networks:
  hospital-network:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
```

### 3. Deploy with Docker Compose

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker-compose -f docker-compose.prod.yml ps
```

---

## Kubernetes Deployment

### 1. Create Kubernetes Manifests

**namespace.yaml:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: hospital-iot
```

**configmap.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hospital-config
  namespace: hospital-iot
data:
  HOST: "0.0.0.0"
  PORT: "8000"
  WORKERS: "4"
  LOG_LEVEL: "info"
  ENVIRONMENT: "production"
```

**secret.yaml:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: hospital-secrets
  namespace: hospital-iot
type: Opaque
stringData:
  DATABASE_URL: postgresql://hospital_user:password@postgres:5432/hospital_iot
  JWT_SECRET_KEY: your-secret-key
  REDIS_URL: redis://:password@redis:6379/0
```

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hospital-backend
  namespace: hospital-iot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hospital-backend
  template:
    metadata:
      labels:
        app: hospital-backend
    spec:
      containers:
      - name: backend
        image: hospital-backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: hospital-config
        - secretRef:
            name: hospital-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: hospital-backend
  namespace: hospital-iot
spec:
  selector:
    app: hospital-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**ingress.yaml:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: hospital-ingress
  namespace: hospital-iot
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.hospital.org
    secretName: hospital-tls
  rules:
  - host: api.hospital.org
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: hospital-backend
            port:
              number: 80
```

### 2. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create config and secrets
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# Deploy application
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Check status
kubectl get pods -n hospital-iot
kubectl get svc -n hospital-iot
kubectl get ingress -n hospital-iot
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | `your-256-bit-secret` |
| `HMS_BASE_URL` | Hospital Management System API URL | `https://hms.hospital.org/api` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRATION_HOURS` | Token expiration in hours | `24` |
| `CORS_ORIGINS` | Allowed CORS origins | `["*"]` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `WORKERS` | Uvicorn worker processes | `4` |
| `LOG_LEVEL` | Logging level | `info` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SENTRY_DSN` | Sentry error tracking DSN | `""` |

---

## SSL/TLS Configuration

### 1. Obtain SSL Certificate

**Using Let's Encrypt (Certbot):**
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d api.hospital.org

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 2. Configure Nginx

Create `nginx.conf`:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/m;

    # Upstream backend
    upstream backend {
        least_conn;
        server backend:8000 max_fails=3 fail_timeout=30s;
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name api.hospital.org;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name api.hospital.org;

        # SSL certificates
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # SSL configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # API endpoints
        location /fhir/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Auth endpoints (stricter rate limit)
        location /auth/ {
            limit_req zone=auth_limit burst=5 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket endpoints
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 86400;
        }

        # Health check (no rate limit)
        location /health {
            proxy_pass http://backend;
            access_log off;
        }
    }
}
```

---

## Monitoring & Logging

### 1. Application Logging

Configure structured logging in `app/main.py`:

```python
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s'
)
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

### 2. Prometheus Metrics

Install dependencies:
```bash
pip install prometheus-fastapi-instrumentator
```

Add to `app/main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

Instrumentator().instrument(app).expose(app)
```

### 3. Grafana Dashboard

Import dashboard JSON from:
- FastAPI metrics: Dashboard ID 14286
- PostgreSQL: Dashboard ID 9628
- Nginx: Dashboard ID 12708

### 4. Log Aggregation (ELK Stack)

**docker-compose.monitoring.yml:**
```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.9.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.9.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.9.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  elasticsearch-data:
```

---

## Backup & Recovery

### 1. Database Backup

**Automated backup script** (`backup.sh`):

```bash
#!/bin/bash

BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="hospital_iot"
DB_USER="hospital_user"

# Create backup
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

# Delete backups older than 30 days
find $BACKUP_DIR -name "${DB_NAME}_*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${DB_NAME}_${TIMESTAMP}.sql.gz"
```

**Set up cron job:**
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

### 2. Database Restore

```bash
# Restore from backup
gunzip -c /backups/hospital_iot_20251121_020000.sql.gz | psql -U hospital_user hospital_iot
```

### 3. Cloud Backup (AWS S3)

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure

# Upload to S3
aws s3 cp /backups/hospital_iot_20251121_020000.sql.gz s3://hospital-backups/
```

---

## Security Hardening

### 1. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Block direct database access from internet
sudo ufw deny 5432/tcp
```

### 2. Database Security

```sql
-- Revoke public access
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Create read-only user for reports
CREATE USER readonly_user WITH PASSWORD 'password';
GRANT CONNECT ON DATABASE hospital_iot TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

### 3. Application Security

**Enable HTTPS only:**
```python
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(HTTPSRedirectMiddleware)
```

**Set secure cookie flags:**
```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",
    https_only=True,
    same_site="strict"
)
```

### 4. Security Scanning

```bash
# Scan Docker images
docker scan hospital-backend:latest

# Scan Python dependencies
pip install safety
safety check

# OWASP ZAP security scan
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://api.hospital.org
```

---

## Performance Tuning

### 1. Database Connection Pooling

Configure in `app/database.py`:
```python
import asyncpg

pool = await asyncpg.create_pool(
    dsn=DATABASE_URL,
    min_size=10,
    max_size=50,
    max_queries=50000,
    max_inactive_connection_lifetime=300,
    command_timeout=60
)
```

### 2. Redis Caching

```python
from redis import asyncio as aioredis

redis = await aioredis.from_url(
    "redis://localhost",
    encoding="utf-8",
    decode_responses=True,
    max_connections=50
)
```

### 3. Uvicorn Workers

```bash
# Start with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

---

## Health Checks

Add health check endpoint in `app/main.py`:

```python
@app.get("/health")
async def health_check():
    # Check database
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    # Check Redis
    try:
        await redis.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"

    overall = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "timestamp": datetime.now().isoformat()
    }
```

---

## Troubleshooting

### Common Issues

**1. Database connection refused**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check firewall
sudo ufw status

# Check connection string
echo $DATABASE_URL
```

**2. High memory usage**
```bash
# Check container stats
docker stats

# Reduce worker processes
WORKERS=2
```

**3. WebSocket disconnections**
```nginx
# Increase nginx timeouts
proxy_read_timeout 86400;
proxy_send_timeout 86400;
```

---

## Support

For deployment issues:
- Email: devops@hospital.org
- Slack: #hospital-iot-support
