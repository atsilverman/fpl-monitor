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

# Create monitoring service
cat > /opt/fpl-monitor/production_monitor.py << 'EOF'
#!/usr/bin/env python3
import os
import requests
import time
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/fpl-monitor/monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fpl_monitor')

class ProductionFPLMonitor:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.headers = {{
            'apikey': self.service_key,
            'Authorization': f'Bearer {{self.service_key}}',
            'Content-Type': 'application/json'
        }}
        self.monitoring = True
        
    def get_fpl_data(self):
        try:
            response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/', timeout=10)
            if response.status_code == 200:
                data = response.json()
                players = data['elements']
                logger.info(f"Fetched {{len(players)}} players from FPL API")
                return players
            else:
                logger.error(f"FPL API error: {{response.status_code}}")
                return None
        except Exception as e:
            logger.error(f"Error fetching FPL data: {{e}}")
            return None
    
    def get_supabase_players(self):
        try:
            response = requests.get(f'{{self.supabase_url}}/rest/v1/players?select=fpl_id,web_name,now_cost&limit=1000', 
                                   headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Fetched {{len(data)}} players from Supabase")
                return data
            else:
                logger.error(f"Supabase error: {{response.status_code}}")
                return None
        except Exception as e:
            logger.error(f"Error fetching Supabase data: {{e}}")
            return None
    
    def detect_price_changes(self, fpl_data, supabase_data):
        if not fpl_data or not supabase_data:
            return []
        
        fpl_prices = {{player['id']: player['now_cost'] for player in fpl_data}}
        supabase_prices = {{player['fpl_id']: player['now_cost'] for player in supabase_data}}
        
        changes = []
        for fpl_id, fpl_price in fpl_prices.items():
            if fpl_id in supabase_prices:
                supabase_price = supabase_prices[fpl_id]
                if fpl_price != supabase_price:
                    player_name = next((p['web_name'] for p in fpl_data if p['id'] == fpl_id), 'Unknown')
                    changes.append({{
                        'fpl_id': fpl_id,
                        'name': player_name,
                        'old_price': supabase_price,
                        'new_price': fpl_price,
                        'change': fpl_price - supabase_price
                    }})
        
        if changes:
            logger.info(f"Detected {{len(changes)}} price changes")
            for change in changes[:5]:
                logger.info(f"  {{change['name']}} (ID {{change['fpl_id']}}): {{change['old_price']}} → {{change['new_price']}} ({{change['change']:+d}})")
            if len(changes) > 5:
                logger.info(f"  ... and {{len(changes) - 5}} more")
        
        return changes
    
    def update_supabase_prices(self, changes):
        if not changes:
            return True
        
        logger.info(f"Updating {{len(changes)}} players in Supabase...")
        
        success_count = 0
        for change in changes:
            try:
                response = requests.patch(
                    f'{{self.supabase_url}}/rest/v1/players?fpl_id=eq.{{change["fpl_id"]}}',
                    headers=self.headers,
                    json={{'now_cost': change['new_price'], 'updated_at': 'now()'}},
                    timeout=5
                )
                
                if response.status_code in [200, 204]:
                    success_count += 1
                    logger.info(f"  ✅ {{change['name']}}: {{change['old_price']}} → {{change['new_price']}}")
                else:
                    logger.error(f"  ❌ {{change['name']}}: Failed ({{response.status_code}})")
                    
            except Exception as e:
                logger.error(f"  ❌ {{change['name']}}: Error - {{e}}")
        
        logger.info(f"Updated {{success_count}}/{{len(changes)}} players successfully")
        return success_count == len(changes)
    
    def is_price_update_window(self):
        now = datetime.now(timezone.utc)
        pacific_time = now.astimezone(timezone(timedelta(hours=-8)))
        
        hour = pacific_time.hour
        minute = pacific_time.minute
        
        return (hour == 18 and minute >= 30) and (hour == 18 and minute < 40)
    
    def run_monitoring_cycle(self):
        try:
            logger.info("Starting monitoring cycle...")
            
            fpl_data = self.get_fpl_data()
            if not fpl_data:
                logger.warning("No FPL data available")
                return
            
            supabase_data = self.get_supabase_players()
            if not supabase_data:
                logger.warning("No Supabase data available")
                return
            
            changes = self.detect_price_changes(fpl_data, supabase_data)
            
            if changes:
                update_success = self.update_supabase_prices(changes)
                if update_success:
                    logger.info("✅ All price updates completed successfully")
                else:
                    logger.error("❌ Some price updates failed")
            else:
                logger.info("No price changes detected")
                
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {{e}}")
    
    def start_monitoring(self):
        logger.info("🚀 Starting FPL Price Monitoring Service")
        logger.info("Monitoring will run every 2 minutes")
        logger.info("Price updates typically occur between 6:30-6:40 PM Pacific")
        
        while self.monitoring:
            try:
                self.run_monitoring_cycle()
                logger.info("Waiting 2 minutes before next cycle...")
                time.sleep(120)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {{e}}")
                logger.info("Waiting 5 minutes before retry...")
                time.sleep(300)
        
        logger.info("FPL Price Monitoring Service stopped")

def main():
    monitor = ProductionFPLMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
EOF

# Make it executable
chmod +x /opt/fpl-monitor/production_monitor.py

# Create systemd service for monitoring
cat > /etc/systemd/system/fpl-monitor.service << 'EOF'
[Unit]
Description=FPL Price Monitoring Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpl-monitor
Environment=PATH=/opt/fpl-monitor/venv/bin
ExecStart=/opt/fpl-monitor/venv/bin/python production_monitor.py
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
    
    print("\n🎉 FPL Monitoring Service deployed successfully!")
    print(f"🌐 Your complete system is now running on: http://{DROPLET_IP}:8000")
    print("\n📊 System Status:")
    print("  ✅ API Server: Running 24/7")
    print("  ✅ Price Monitoring: Running 24/7")
    print("  ✅ Supabase Integration: Active")
    print("  ✅ Automatic Price Updates: Enabled")
    
    print("\n🔍 Monitor logs with:")
    print(f"   ssh {DROPLET_USER}@{DROPLET_IP} 'journalctl -u fpl-monitor -f'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
