# 🚀 FPL Monitor Deployment Guide

## Overview

This guide covers deploying the FPL Monitor application to production environments.

## Prerequisites

- DigitalOcean account
- Supabase account
- Domain name (optional)
- SSL certificate (for HTTPS)

## Environment Setup

### 1. DigitalOcean Droplet

Create a new droplet with the following specifications:
- **OS**: Ubuntu 22.04 LTS
- **Size**: Basic $8/month (1GB RAM, 1 CPU, 25GB SSD)
- **Region**: Choose closest to your users
- **Authentication**: SSH key

### 2. Supabase Database

1. Create a new Supabase project
2. Run the database schema:
   ```sql
   -- Copy contents from database/supabase_schema.sql
   ```
3. Note down your project URL and anon key

### 3. Environment Variables

Create a `.env` file on your server:

```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Server
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Push Notifications (iOS)
APNS_BUNDLE_ID=com.yourcompany.fplmonitor
APNS_KEY_ID=your_key_id
APNS_TEAM_ID=your_team_id
APNS_KEY_PATH=/opt/fpl-monitor/keys/AuthKey.p8
```

## Deployment Methods

### Method 1: Docker Deployment (Recommended)

#### 1. Install Docker
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Deploy Application
```bash
# Clone repository
git clone <your-repo-url> /opt/fpl-monitor
cd /opt/fpl-monitor

# Copy environment file
cp env.example .env
# Edit .env with your values

# Build and run
docker-compose up -d
```

#### 3. Configure Nginx (Optional)
```bash
# Install Nginx
sudo apt install nginx -y

# Create configuration
sudo nano /etc/nginx/sites-available/fpl-monitor
```

Nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/fpl-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Method 2: Systemd Service

#### 1. Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-pip -y

# Install system dependencies
sudo apt install gcc g++ libpq-dev -y
```

#### 2. Setup Application
```bash
# Create application directory
sudo mkdir -p /opt/fpl-monitor
sudo chown $USER:$USER /opt/fpl-monitor

# Clone repository
git clone <your-repo-url> /opt/fpl-monitor
cd /opt/fpl-monitor

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp env.example .env
# Edit .env with your values
```

#### 3. Create Systemd Service
```bash
sudo nano /etc/systemd/system/fpl-monitor.service
```

Service file:
```ini
[Unit]
Description=FPL Monitor Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/fpl-monitor
Environment=PATH=/opt/fpl-monitor/venv/bin
ExecStart=/opt/fpl-monitor/venv/bin/python -m backend.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4. Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable fpl-monitor
sudo systemctl start fpl-monitor

# Check status
sudo systemctl status fpl-monitor
```

## SSL/HTTPS Setup

### Using Let's Encrypt (Free)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Using Cloudflare (Recommended)

1. Add your domain to Cloudflare
2. Update nameservers
3. Enable SSL/TLS encryption mode: "Full (strict)"
4. Configure page rules for HTTPS redirect

## Monitoring and Logs

### View Logs
```bash
# Docker
docker-compose logs -f

# Systemd
sudo journalctl -u fpl-monitor -f
```

### Health Checks
```bash
# Check API health
curl http://localhost:8000/

# Check monitoring status
curl http://localhost:8000/api/v1/monitoring/status
```

### Backup Database
```bash
# Create backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
psql $DATABASE_URL < backup_file.sql
```

## Scaling and Performance

### Horizontal Scaling
- Use load balancer (Nginx, HAProxy)
- Deploy multiple instances behind load balancer
- Use Redis for session storage

### Vertical Scaling
- Upgrade droplet size
- Add more CPU/RAM
- Optimize database queries

### Database Optimization
- Enable connection pooling
- Add database indexes
- Use read replicas for read-heavy workloads

## Security Considerations

### Firewall Setup
```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow application port (if not using reverse proxy)
sudo ufw allow 8000
```

### Application Security
- Use environment variables for secrets
- Enable HTTPS only
- Implement rate limiting
- Regular security updates
- Monitor for suspicious activity

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
sudo journalctl -u fpl-monitor -n 50

# Check configuration
python -m backend.main --check-config
```

#### Database Connection Issues
```bash
# Test connection
python -c "import psycopg2; print('DB OK')"

# Check environment variables
env | grep -E "(SUPABASE|DATABASE)"
```

#### High Memory Usage
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Restart service
sudo systemctl restart fpl-monitor
```

### Performance Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs -y

# Monitor resources
htop
iotop
nethogs
```

## Maintenance

### Regular Tasks
- Update system packages
- Backup database
- Monitor disk space
- Check service logs
- Update application dependencies

### Update Application
```bash
# Pull latest changes
cd /opt/fpl-monitor
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart fpl-monitor
```

## Support

For deployment issues:
1. Check logs first
2. Verify environment variables
3. Test database connectivity
4. Check firewall settings
5. Open GitHub issue with logs
