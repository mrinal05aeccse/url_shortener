# Deployment Guide

Comprehensive guide for deploying the URL Shortener to production.

---

## 1. Pre-Deployment Checklist

### Code & Configuration
- [ ] All tests passing (`pytest backend/tests/`)
- [ ] No security warnings (`pip-audit`, `safety check`)
- [ ] API documentation reviewed (`/api/docs`)
- [ ] Environment variables documented
- [ ] .env file NOT committed to git
- [ ] All dependencies pinned in requirements.txt

### Database
- [ ] Migration plan documented (SQLite → PostgreSQL)
- [ ] Backup strategy defined
- [ ] Connection pooling configured
- [ ] Performance tested with expected load

### Infrastructure
- [ ] HTTPS certificate obtained (Let's Encrypt)
- [ ] Reverse proxy configured (nginx/Caddy)
- [ ] Firewall rules defined
- [ ] VPC/security groups configured
- [ ] DNS records prepared

### Security
- [ ] API key rotated
- [ ] CORS configuration restricted
- [ ] Rate limiting configured
- [ ] Monitoring and alerting set up
- [ ] Incident response plan documented

---

## 2. Database Migration (SQLite → PostgreSQL)

### Step 1: Create PostgreSQL Database

```bash
# Remote server
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
postgres=# CREATE DATABASE url_shortener;
postgres=# CREATE USER url_app WITH PASSWORD 'secure_password_here';
postgres=# ALTER ROLE url_app SET client_encoding TO 'utf8';
postgres=# ALTER ROLE url_app SET default_transaction_isolation TO 'read committed';
postgres=# ALTER ROLE url_app SET default_transaction_deferrable TO on;
postgres=# ALTER ROLE url_app SET timezone TO 'UTC';
postgres=# GRANT ALL PRIVILEGES ON DATABASE url_shortener TO url_app;
postgres=# \q
```

### Step 2: Configure Connection String

```bash
# .env
DATABASE_URL=postgresql://url_app:secure_password_here@db.example.com:5432/url_shortener

# Verify connection
psql postgresql://url_app:secure_password_here@db.example.com:5432/url_shortener -c "\dt"
```

### Step 3: Initialize Database Schema

```bash
cd backend
python -c "from app.database import init_db; init_db()"
```

### Step 4: Optional - Migrate Existing Data

If you have existing SQLite data to migrate:

```python
# backend/scripts/migrate_sqlite_to_pg.py
import os
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from backend.app.database import engine as target_engine
from backend.app.models import URL, ClickEvent

# Source: SQLite
source_db_path = "sqlite:///./old_data.db"
source_engine = create_engine(source_db_path, echo=False)

# Read from SQLite
with Session(source_engine) as source_session:
    urls = source_session.query(URL).all()
    click_events = source_session.query(ClickEvent).all()

# Write to PostgreSQL
with Session(target_engine) as target_session:
    for url in urls:
        target_session.add(url)
    for event in click_events:
        target_session.add(event)
    target_session.commit()

print(f"Migrated {len(urls)} URLs and {len(click_events)} click events")
```

---

## 3. Application Server Setup

### Option 1: Gunicorn + Systemd (Recommended)

```bash
# Install Gunicorn
pip install gunicorn[gevent]

# Create systemd service file
sudo nano /etc/systemd/system/url-shortener.service
```

```ini
[Unit]
Description=URL Shortener FastAPI Application
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/url-shortener/backend
ExecStart=/opt/url-shortener/.venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 30 \
    --access-logfile /var/log/url-shortener/access.log \
    --error-logfile /var/log/url-shortener/error.log \
    app.main:app
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

# Environment
EnvironmentFile=/opt/url-shortener/.env
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable url-shortener
sudo systemctl start url-shortener

# Check status
sudo systemctl status url-shortener
```

### Option 2: Docker (Alternative)

```dockerfile
# backend/Dockerfile.prod
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn[gevent]

# Copy application
COPY app/ ./app/

# Run with Gunicorn
CMD ["gunicorn", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "30", \
     "app.main:app"]
```

---

## 4. Reverse Proxy Configuration

### Nginx Setup

```bash
# Install Nginx
sudo apt-get install nginx

# Create config file
sudo nano /etc/nginx/sites-available/url-shortener
```

```nginx
upstream url_shortener {
    server 127.0.0.1:8000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name shortener.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS configuration
server {
    listen 443 ssl http2;
    server_name shortener.example.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/shortener.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/shortener.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=shorten_limit:10m rate=5r/s;

    # Proxy to FastAPI
    location / {
        proxy_pass http://url_shortener;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
    }

    # API endpoint with stricter rate limiting
    location ~ ^/api/v1/shorten {
        proxy_pass http://url_shortener;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        limit_req zone=shorten_limit burst=5 nodelay;
    }

    # API documentation (restrict to internal networks)
    location ~ ^/api/(docs|redoc|openapi.json) {
        # Allow internal IPs only
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;

        proxy_pass http://url_shortener;
    }

    # Static files (if any frontend served from same host)
    location /static/ {
        alias /opt/url-shortener/frontend/dist/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Logging
    access_log /var/log/nginx/url-shortener-access.log;
    error_log /var/log/nginx/url-shortener-error.log;
}
```

```bash
# Enable site and restart Nginx
sudo ln -s /etc/nginx/sites-available/url-shortener /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Get SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d shortener.example.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## 5. Monitoring & Logging

### Application Logging

```python
# backend/app/logging_config.py
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("/var/log/url-shortener/app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()
```

### System Monitoring

```bash
# Install monitoring tools
sudo apt-get install htop iotop nethogs

# Check service status
sudo systemctl status url-shortener

# View logs
sudo journalctl -u url-shortener -f

# Monitor database
sudo -u postgres psql url_shortener -c "SELECT COUNT(*) FROM url; SELECT COUNT(*) FROM click_event;"
```

### Prometheus & Grafana (Optional)

```bash
# Add metrics to FastAPI
pip install prometheus-client

# Expose metrics endpoint
from prometheus_client import Counter, Histogram, make_wsgi_app
from fastapi.middleware.wsgi import WSGIMiddleware

app.add_middleware(WSGIMiddleware, app=make_wsgi_app())
```

---

## 6. Backup & Disaster Recovery

### Database Backups

```bash
# Daily backup
sudo crontab -e

# Add:
0 2 * * * /usr/bin/pg_dump -U url_app url_shortener | gzip > /backups/url_shortener_$(date +\%Y\%m\%d).sql.gz

# Verify backup
ls -lh /backups/url_shortener_*.sql.gz

# Restore from backup
gunzip < /backups/url_shortener_20240101.sql.gz | psql -U url_app url_shortener
```

### Offsite Backup

```bash
# Copy to S3
sudo apt-get install awscli

# Add to cron:
0 3 * * * aws s3 cp /backups/url_shortener_$(date +\%Y\%m\%d).sql.gz s3://my-backup-bucket/
```

---

## 7. Performance Tuning

### PostgreSQL Optimization

```sql
-- Increase connection pool (pgbouncer)
CREATE INDEX idx_click_event_url_id ON click_event(url_id);
CREATE INDEX idx_click_event_timestamp ON click_event(timestamp);
CREATE INDEX idx_url_alias ON url(alias);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM url WHERE alias = 'abc123';
```

### Application Scaling

```bash
# Use multiple Gunicorn workers
gunicorn --workers 8 --worker-class uvicorn.workers.UvicornWorker ...

# Use connection pooling
DATABASE_URL=postgresql://...?pool_size=20&max_overflow=40
```

### Caching Layer (Redis)

```bash
# Install Redis
sudo apt-get install redis-server

# Configure in app
import redis
cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
```

---

## 8. Environment Variables (Production)

```bash
# .env.production
DEBUG=false
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://url_app:PASSWORD@db.example.com/url_shortener

# Security
ADMIN_API_KEY=<secure_random_key>
SECRET_KEY=<jwt_secret_key>

# Logging
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PROVIDER=redis
REDIS_URL=redis://localhost:6379

# Geolocation
GEOIP_DB_PATH=/opt/url-shortener/data/GeoLite2-City.mmdb

# CORS
CORS_ORIGINS=["https://example.com"]
```

---

## 9. Troubleshooting

### Application Won't Start

```bash
# Check logs
sudo journalctl -u url-shortener -n 50

# Verify configuration
python -c "from backend.app.database import init_db; init_db()"

# Check database connection
psql postgresql://url_app:PASSWORD@db.example.com/url_shortener -c "SELECT 1"
```

### High Response Times

```bash
# Check database performance
EXPLAIN ANALYZE SELECT * FROM url WHERE alias = 'xxx';

# Check system resources
top, htop, iostat

# Increase workers
systemctl stop url-shortener
# Edit unit file, increase --workers
systemctl daemon-reload
systemctl start url-shortener
```

### Database Connection Errors

```bash
# Verify connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check pg_hba.conf permissions
sudo nano /etc/postgresql/12/main/pg_hba.conf
# Ensure host line for your app IP
```

---

## 10. Post-Deployment

### Verification

- [ ] Homepage loads at https://shortener.example.com
- [ ] Can create short URL: `curl -X POST https://shortener.example.com/api/v1/shorten -d '{"target":"https://example.com"}'`
- [ ] Redirect works: `curl -L https://shortener.example.com/abc123`
- [ ] Admin endpoints protected: `curl https://shortener.example.com/api/v1/info/abc123` (should return 401)
- [ ] API docs accessible: https://shortener.example.com/api/docs (check if restricted)

### Monitoring Setup

- [ ] Uptime monitoring (Ping uptime service)
- [ ] Error rate alerting (Sentry or Datadog)
- [ ] Database disk space alerting
- [ ] Performance degradation alerting

### Documentation

- [ ] Runbook created for common operations
- [ ] Incident response plan prepared
- [ ] Team trained on deployment

