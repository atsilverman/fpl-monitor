#!/usr/bin/env python3
"""
Production FPL Price Monitor
Runs 24/7 on DigitalOcean to detect and update FPL price changes
"""

import os
import requests
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
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
        self.previous_prices = {}
        self.monitoring = True
        
    def get_fpl_data(self):
        """Get current FPL data from the API"""
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
        """Get current player data from Supabase"""
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
        """Detect price changes between FPL API and Supabase"""
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
        """Update Supabase with new prices"""
        if not changes:
            return True
        
        logger.info(f"Updating {len(changes)} players in Supabase...")
        
        success_count = 0
        for change in changes:
            try:
                response = requests.patch(
                    f'{self.supabase_url}/rest/v1/players?fpl_id=eq.{change["fpl_id"]}',
                    headers=self.headers,
                    json={'now_cost': change['new_price'], 'updated_at': 'now()'},
                    timeout=5
                )
                
                if response.status_code in [200, 204]:
                    success_count += 1
                    logger.info(f"  ✅ {change['name']}: {change['old_price']} → {change['new_price']}")
                else:
                    logger.error(f"  ❌ {change['name']}: Failed ({response.status_code})")
                    
            except Exception as e:
                logger.error(f"  ❌ {change['name']}: Error - {e}")
        
        logger.info(f"Updated {success_count}/{len(changes)} players successfully")
        return success_count == len(changes)
    
    def is_price_update_window(self):
        """Check if we're in the FPL price update window (6:30-6:40 PM Pacific)"""
        now = datetime.now(timezone.utc)
        pacific_time = now.astimezone(timezone(timedelta(hours=-8)))  # Pacific Time
        
        hour = pacific_time.hour
        minute = pacific_time.minute
        
        # FPL price updates typically happen between 6:30-6:40 PM Pacific
        return (hour == 18 and minute >= 30) and (hour == 18 and minute < 40)
    
    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        try:
            logger.info("Starting monitoring cycle...")
            
            # Get current data
            fpl_data = self.get_fpl_data()
            if not fpl_data:
                logger.warning("No FPL data available")
                return
            
            supabase_data = self.get_supabase_players()
            if not supabase_data:
                logger.warning("No Supabase data available")
                return
            
            # Detect changes
            changes = self.detect_price_changes(fpl_data, supabase_data)
            
            # Update Supabase if there are changes
            if changes:
                update_success = self.update_supabase_prices(changes)
                if update_success:
                    logger.info("✅ All price updates completed successfully")
                else:
                    logger.error("❌ Some price updates failed")
            else:
                logger.info("No price changes detected")
                
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
    
    def start_monitoring(self):
        """Start the monitoring service"""
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
