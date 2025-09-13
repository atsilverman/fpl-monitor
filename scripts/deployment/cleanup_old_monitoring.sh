#!/bin/bash
# Cleanup Old Monitoring Files
# ============================
# 
# This script removes old monitoring files from the production server
# to ensure only the new event-based service is running.

set -e

DROPLET_IP="138.68.28.59"
DROPLET_USER="root"

echo "🧹 Cleaning up old monitoring files on production server..."
echo "📍 Target: $DROPLET_USER@$DROPLET_IP"

# Stop any running services
echo "🛑 Stopping existing services..."
ssh $DROPLET_USER@$DROPLET_IP 'systemctl stop fpl-monitor || true'

# Remove old monitoring files
echo "🗑️  Removing old monitoring files..."
ssh $DROPLET_USER@$DROPLET_IP '
    # Remove old monitoring scripts
    rm -f /opt/fpl-monitor/fpl_monitor_enhanced_production.py
    rm -f /opt/fpl-monitor/production_monitor.py
    rm -f /opt/fpl-monitor/start_production_monitor.py
    
    # Remove old logs
    rm -f /opt/fpl-monitor/logs/fpl_monitor.log
    
    # Clean up any old Python cache
    find /opt/fpl-monitor -name "*.pyc" -delete
    find /opt/fpl-monitor -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    echo "✅ Old files cleaned up"
'

# Verify cleanup
echo "🔍 Verifying cleanup..."
ssh $DROPLET_USER@$DROPLET_IP '
    echo "Remaining monitoring files:"
    find /opt/fpl-monitor -name "*monitor*" -type f
    echo ""
    echo "Current processes:"
    ps aux | grep -i fpl | grep -v grep || echo "No FPL processes running"
'

echo "✅ Cleanup complete!"
echo "🚀 Ready to deploy new event-based architecture"
