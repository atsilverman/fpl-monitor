#!/bin/bash
# Deploy FPL Monitor to DigitalOcean Droplet

DROPLET_IP="138.68.28.59"
DROPLET_USER="root"
SSH_KEY="~/.ssh/id_ed25519"

echo "🚀 Deploying FPL Monitor to DigitalOcean Droplet..."
echo "📍 Droplet IP: $DROPLET_IP"

# Create deployment directory on droplet
echo "📁 Creating deployment directory..."
ssh -i $SSH_KEY $DROPLET_USER@$DROPLET_IP "mkdir -p /opt/fpl-monitor"

# Copy project files to droplet
echo "📤 Uploading project files..."
scp -i $SSH_KEY -r /Users/silverman/Desktop/fpl-monitor/* $DROPLET_USER@$DROPLET_IP:/opt/fpl-monitor/

# Install dependencies on droplet
echo "📦 Installing dependencies..."
ssh -i $SSH_KEY $DROPLET_USER@$DROPLET_IP "cd /opt/fpl-monitor && apt update && apt install -y python3 python3-pip python3-venv"

# Create virtual environment and install requirements
echo "🐍 Setting up Python environment..."
ssh -i $SSH_KEY $DROPLET_USER@$DROPLET_IP "cd /opt/fpl-monitor && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"

# Create systemd service
echo "⚙️ Creating systemd service..."
ssh -i $SSH_KEY $DROPLET_USER@$DROPLET_IP "cat > /etc/systemd/system/fpl-monitor.service << 'EOF'
[Unit]
Description=FPL Monitor Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpl-monitor
Environment=PATH=/opt/fpl-monitor/venv/bin
ExecStart=/opt/fpl-monitor/venv/bin/python /opt/fpl-monitor/backend/services/fpl_monitor_simple.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

# Enable and start service
echo "🔄 Starting FPL Monitor service..."
ssh -i $SSH_KEY $DROPLET_USER@$DROPLET_IP "systemctl daemon-reload && systemctl enable fpl-monitor && systemctl start fpl-monitor"

# Check service status
echo "✅ Checking service status..."
ssh -i $SSH_KEY $DROPLET_USER@$DROPLET_IP "systemctl status fpl-monitor --no-pager"

echo "🎉 Deployment complete!"
echo "🌐 Service should be running on: http://$DROPLET_IP:8000"
echo "📱 Update your iOS app to use: http://$DROPLET_IP:8000"
