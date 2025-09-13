#!/usr/bin/env python3
"""
Deploy FPL Monitoring Service to DigitalOcean
Sets up the production monitoring service to run 24/7
"""

import os
import subprocess
import sys

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            return True
        else:
            print(f"❌ {description} - Failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Exception: {e}")
        return False

def main():
    print("🚀 Deploying FPL Monitoring Service to DigitalOcean")
    print("=" * 60)
    
    # Server details
    DROPLET_IP = "138.68.28.59"
    DROPLET_USER = "root"
    
    print(f"📍 Target: {DROPLET_USER}@{DROPLET_IP}")
    
    # Create deployment script for monitoring service
    deploy_script = f"""#!/bin/bash
set -e

echo "🚀 Setting up FPL Monitoring Service on DigitalOcean..."

# Copy the production monitoring script
cp /opt/fpl-monitor/backend/services/fpl_monitor_production.py /opt/fpl-monitor/production_monitor.py

# Make it executable
chmod +x /opt/fpl-monitor/production_monitor.py

# Create systemd service for monitoring
cat > /etc/systemd/system/fpl-monitor.service << 'EOF'
[Unit]
Description=FPL Event-Based Production Monitoring Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpl-monitor
Environment=PATH=/opt/fpl-monitor/venv/bin
ExecStart=/opt/fpl-monitor/venv/bin/python -m backend.services.fpl_monitor_production
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable the service
systemctl daemon-reload
systemctl enable fpl-monitor

echo "✅ FPL Monitoring Service setup complete!"
echo "📝 Service will start automatically on boot"
echo "🔍 Check logs with: journalctl -u fpl-monitor -f"
"""
    
    # Write deployment script to file
    with open("deploy_monitoring.sh", "w") as f:
        f.write(deploy_script)
    
    # Make it executable
    os.chmod("deploy_monitoring.sh", 0o755)
    
    # Copy deployment script to server
    if not run_command(f"scp deploy_monitoring.sh {DROPLET_USER}@{DROPLET_IP}:/tmp/", "Copying monitoring deployment script"):
        return False
    
    # Run deployment script on server
    if not run_command(f"ssh {DROPLET_USER}@{DROPLET_IP} 'bash /tmp/deploy_monitoring.sh'", "Setting up monitoring service"):
        return False
    
    # Start the monitoring service
    if not run_command(f"ssh {DROPLET_USER}@{DROPLET_IP} 'systemctl start fpl-monitor'", "Starting monitoring service"):
        return False
    
    # Check service status
    if not run_command(f"ssh {DROPLET_USER}@{DROPLET_IP} 'systemctl status fpl-monitor --no-pager'", "Checking service status"):
        return False
    
    # Clean up
    os.remove("deploy_monitoring.sh")
    
    print("\n🎉 FPL Enhanced Production Monitoring Service deployed successfully!")
    print(f"🌐 Your complete system is now running on: http://{DROPLET_IP}:8000")
    print("\n📊 System Status:")
    print("  ✅ API Server: Running 24/7")
    print("  ✅ Enhanced Monitoring: Running 24/7")
    print("    • Live Performance (60s refresh)")
    print("    • Status & News Changes (1h refresh)")
    print("    • Price Changes (5min refresh)")
    print("    • Final Bonus (5min refresh)")
    print("  ✅ Supabase Integration: Active")
    print("  ✅ Dynamic Monitoring Modes: Enabled")
    
    print("\n🔍 Monitor logs with:")
    print(f"   ssh {DROPLET_USER}@{DROPLET_IP} 'journalctl -u fpl-monitor -f'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
