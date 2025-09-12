#!/bin/bash
set -e

echo "🚀 Updating FPL Monitoring Service with History Table Support..."

# Stop the current service
systemctl stop fpl-monitor

# Update the monitoring script
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
        self.headers = {
            'apikey': self.service_key,
            'Authorization': f'Bearer {self.service_key}',
            'Content-Type': 'application/json'
        }
        self.monitoring = True
        
    def get_fpl_data(self):
        try:
            response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/', timeout=10)
            if response.status_code == 200:
                data = response.json()
                players = data['elements']
                logger.info(f"Fetched {len(players)} players from FPL API")
                return players
            else:
                logger.error(f"FPL API error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching FPL data: {e}")
            return None
    
    def get_supabase_players(self):
        try:
            response = requests.get(f'{self.supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost&limit=1000', 
                                   headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Fetched {len(data)} players from Supabase")
                return data
            else:
                logger.error(f"Supabase error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching Supabase data: {e}")
            return None
    
    def detect_price_changes(self, fpl_data, supabase_data):
        if not fpl_data or not supabase_data:
            return []
        
        # Create lookup dictionaries
        fpl_prices = {player['id']: player['now_cost'] for player in fpl_data}
        supabase_prices = {player['fpl_id']: player['now_cost'] for player in supabase_data}
        
        changes = []
        for fpl_id, fpl_price in fpl_prices.items():
            if fpl_id in supabase_prices:
                supabase_price = supabase_prices[fpl_id]
                if fpl_price != supabase_price:
                    # Find player name
                    player_name = next((p['web_name'] for p in fpl_data if p['id'] == fpl_id), 'Unknown')
                    changes.append({
                        'fpl_id': fpl_id,
                        'name': player_name,
                        'old_price': supabase_price,
                        'new_price': fpl_price,
                        'change': fpl_price - supabase_price
                    })
        
        if changes:
            logger.info(f"Detected {len(changes)} price changes")
            for change in changes[:5]:  # Log first 5 changes
                logger.info(f"  {change['name']} (ID {change['fpl_id']}): {change['old_price']} → {change['new_price']} ({change['change']:+d})")
            if len(changes) > 5:
                logger.info(f"  ... and {len(changes) - 5} more")
        
        return changes
    
    def update_supabase_prices(self, changes):
        if not changes:
            return True
        
        logger.info(f"Updating {len(changes)} players in Supabase...")
        
        success_count = 0
        for change in changes:
            try:
                # Update the players table
                response = requests.patch(
                    f'{self.supabase_url}/rest/v1/players?fpl_id=eq.{change["fpl_id"]}',
                    headers=self.headers,
                    json={'now_cost': change['new_price'], 'updated_at': 'now()'},
                    timeout=5
                )
                
                if response.status_code in [200, 204]:
                    success_count += 1
                    logger.info(f"  ✅ {change['name']}: {change['old_price']} → {change['new_price']}")
                    
                    # Store price change in live_monitor_history
                    self.store_price_change_in_history(change)
                    
                else:
                    logger.error(f"  ❌ {change['name']}: Failed ({response.status_code})")
                    
            except Exception as e:
                logger.error(f"  ❌ {change['name']}: Error - {e}")
        
        logger.info(f"Updated {success_count}/{len(changes)} players successfully")
        return success_count == len(changes)
    
    def store_price_change_in_history(self, change):
        try:
            # Get current gameweek
            gameweek = self.get_current_gameweek()
            
            # Store in live_monitor_history
            history_data = {
                'player_name': change['name'],
                'gameweek': gameweek,
                'event_type': 'price_change',
                'old_value': change['old_price'],
                'new_value': change['new_price'],
                'points_change': 0
            }
            
            response = requests.post(
                f'{self.supabase_url}/rest/v1/live_monitor_history',
                headers=self.headers,
                json=history_data,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                logger.debug(f"  📝 Stored price change history for {change['name']}")
            else:
                logger.warning(f"  ⚠️ Failed to store history for {change['name']}: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"  ⚠️ Error storing price change history: {e}")
    
    def get_current_gameweek(self):
        try:
            response = requests.get(
                f'{self.supabase_url}/rest/v1/gameweeks?is_current=eq.true&select=id&limit=1',
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]['id']
            
            # Fallback
            from datetime import datetime
            now = datetime.now()
            return max(1, (now.month - 8) + 1) if now.month >= 8 else 1
            
        except Exception as e:
            logger.warning(f"Error getting current gameweek: {e}")
            return 1
    
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
            
            # Check if we should capture daily snapshot (once per day at 9 PM Pacific)
            self.check_and_capture_daily_snapshot(fpl_data)
                
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
    
    def check_and_capture_daily_snapshot(self, fpl_data):
        try:
            from datetime import datetime, timezone
            import pytz
            
            # Get current time in Pacific Time
            utc_now = datetime.now(timezone.utc)
            pacific_time = utc_now.astimezone(pytz.timezone('America/Los_Angeles'))
            
            # Check if it's 9 PM Pacific (daily snapshot time)
            if pacific_time.hour == 21 and pacific_time.minute < 5:  # 5-minute window
                # Check if we already captured today's snapshot
                today = pacific_time.date()
                if not self.has_daily_snapshot_today(today):
                    logger.info("📸 Capturing daily player snapshot...")
                    self.capture_daily_snapshot(fpl_data, today, pacific_time)
                else:
                    logger.debug("Daily snapshot already captured today")
                    
        except Exception as e:
            logger.warning(f"Error checking daily snapshot: {e}")
    
    def has_daily_snapshot_today(self, today):
        try:
            response = requests.get(
                f'{self.supabase_url}/rest/v1/player_history?snapshot_date=eq.{today}&snapshot_window=eq.daily_9pm_pdt&limit=1',
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return len(data) > 0
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking daily snapshot: {e}")
            return False
    
    def capture_daily_snapshot(self, fpl_data, today, pacific_time):
        try:
            snapshot_data = []
            
            for player in fpl_data:
                snapshot_data.append({
                    'fpl_id': player['id'],
                    'snapshot_date': str(today),
                    'snapshot_window': 'daily_9pm_pdt',
                    'snapshot_timestamp': pacific_time.isoformat(),
                    'now_cost': player['now_cost'] / 10,  # Convert to decimal
                    'selected_by_percent': player.get('selected_by_percent', 0),
                    'status': player.get('status', 'a'),
                    'news': player.get('news', '')
                })
            
            # Insert snapshot data
            response = requests.post(
                f'{self.supabase_url}/rest/v1/player_history',
                headers=self.headers,
                json=snapshot_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"📸 Captured daily snapshot for {len(snapshot_data)} players")
            else:
                logger.error(f"❌ Failed to capture daily snapshot: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error capturing daily snapshot: {e}")
    
    def start_monitoring(self):
        logger.info("🚀 Starting FPL Price Monitoring Service")
        logger.info("Monitoring will run every 2 minutes")
        logger.info("Price updates typically occur between 6:30-6:40 PM Pacific")
        
        while self.monitoring:
            try:
                self.run_monitoring_cycle()
                
                # Wait 2 minutes before next cycle
                logger.info("Waiting 2 minutes before next cycle...")
                time.sleep(120)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                logger.info("Waiting 5 minutes before retry...")
                time.sleep(300)  # Wait 5 minutes on error
        
        logger.info("FPL Price Monitoring Service stopped")

def main():
    monitor = ProductionFPLMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
EOF
EOF

# Make it executable
chmod +x /opt/fpl-monitor/production_monitor.py

# Restart the service
systemctl start fpl-monitor

echo "✅ Updated monitoring service deployed successfully!"
echo "📝 Service now includes history table population"
