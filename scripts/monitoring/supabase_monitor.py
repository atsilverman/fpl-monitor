#!/usr/bin/env python3
"""
Supabase FPL Monitor
===================

Proper monitoring service that updates Supabase directly.
This fixes the critical architecture issue where monitoring service
was updating local PostgreSQL instead of Supabase.
"""

import os
import time
import requests
import json
from datetime import datetime, timezone
import pytz
from dotenv import load_dotenv

class SupabaseFPLMonitor:
    def __init__(self):
        load_dotenv()
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
        self.fpl_base_url = "https://fantasy.premierleague.com/api"
        
        if not self.supabase_url or not self.supabase_key:
            raise Exception("Missing Supabase credentials")
        
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json'
        }
        
        print("🚀 Supabase FPL Monitor initialized")
        print(f"   Supabase URL: {self.supabase_url}")
        print(f"   FPL API: {self.fpl_base_url}")

    def is_price_window(self) -> bool:
        """Check if current time is within FPL price update window (6:30-6:40 PM Pacific)"""
        utc_now = datetime.now(timezone.utc)
        pacific_time = utc_now.astimezone(pytz.timezone('America/Los_Angeles'))
        
        hour = pacific_time.hour
        minute = pacific_time.minute
        
        # 6:30-6:40 PM Pacific Time
        is_window = (hour == 18 and minute >= 30) and (hour == 18 and minute < 40)
        return is_window

    def get_fpl_data(self):
        """Fetch current data from FPL API"""
        try:
            response = requests.get(f"{self.fpl_base_url}/bootstrap-static/", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ FPL API error: {e}")
            return None

    def get_supabase_players(self):
        """Get current players from Supabase"""
        try:
            response = requests.get(
                f"{self.supabase_url}/rest/v1/players?select=fpl_id,now_cost,web_name",
                headers=self.headers
            )
            if response.status_code == 200:
                return {player['fpl_id']: player for player in response.json()}
            else:
                print(f"❌ Supabase error: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ Supabase connection error: {e}")
            return {}

    def update_player_prices(self, fpl_data):
        """Update player prices in Supabase"""
        if not fpl_data or 'elements' not in fpl_data:
            return False
        
        # Get current Supabase data
        supabase_players = self.get_supabase_players()
        
        # Find price changes
        changes = []
        updates = []
        
        for player in fpl_data['elements']:
            fpl_id = player['id']
            new_price = player['now_cost']
            
            if fpl_id in supabase_players:
                old_price = supabase_players[fpl_id]['now_cost']
                if old_price != new_price:
                    changes.append({
                        'fpl_id': fpl_id,
                        'name': player['web_name'],
                        'old_price': old_price,
                        'new_price': new_price,
                        'change': new_price - old_price
                    })
            
            # Prepare for bulk update
            updates.append({
                'fpl_id': fpl_id,
                'now_cost': new_price,
                'web_name': player['web_name'],
                'updated_at': 'now()'
            })
        
        if changes:
            print(f"💰 Found {len(changes)} price changes:")
            for change in changes[:10]:  # Show first 10
                direction = "📈" if change['change'] > 0 else "📉"
                print(f"   {direction} {change['name']}: {change['old_price']/10:.1f}m → {change['new_price']/10:.1f}m")
        
        # Update players individually to avoid RLS issues
        success_count = 0
        for update in updates:
            try:
                response = requests.patch(
                    f"{self.supabase_url}/rest/v1/players?fpl_id=eq.{update['fpl_id']}",
                    headers=self.headers,
                    json={
                        'now_cost': update['now_cost'],
                        'web_name': update['web_name'],
                        'updated_at': 'now()'
                    }
                )
                
                if response.status_code in [200, 201, 204]:
                    success_count += 1
                else:
                    print(f"❌ Failed to update player {update['fpl_id']}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error updating player {update['fpl_id']}: {e}")
        
        if success_count > 0:
            print(f"✅ Updated {success_count}/{len(updates)} players in Supabase")
            return success_count == len(updates)
        else:
            print(f"❌ Failed to update any players")
            return False

    def check_solanke(self):
        """Check Solanke's current price"""
        try:
            response = requests.get(
                f"{self.supabase_url}/rest/v1/players?fpl_id=eq.596&select=fpl_id,web_name,now_cost,updated_at",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    player = data[0]
                    print(f"📊 Solanke: {player['web_name']}, Price: {player['now_cost']/10:.1f}m, Updated: {player['updated_at']}")
                    return player['now_cost']
            return None
        except Exception as e:
            print(f"❌ Error checking Solanke: {e}")
            return None

    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        print(f"\n🔄 Monitoring cycle at {datetime.now().strftime('%H:%M:%S')}")
        
        # Check if in price window
        is_price_window = self.is_price_window()
        if is_price_window:
            print("💰 PRICE WINDOW ACTIVE - Monitoring for changes")
        else:
            print("⏰ Normal monitoring")
        
        # Get FPL data
        fpl_data = self.get_fpl_data()
        if not fpl_data:
            return
        
        # Update prices
        success = self.update_player_prices(fpl_data)
        
        if success:
            # Check Solanke specifically
            solanke_price = self.check_solanke()
            if solanke_price == 72:
                print("🎉 Solanke is correctly priced at 7.2m!")
            elif solanke_price == 73:
                print("⚠️ Solanke still shows 7.3m - update may have failed")
        
        return success

    def start_monitoring(self):
        """Start the monitoring service"""
        print("🚀 Starting Supabase FPL Monitor...")
        print("Press Ctrl+C to stop")
        
        last_price_window = False
        
        try:
            while True:
                current_time = datetime.now()
                pacific_time = current_time.astimezone(pytz.timezone('America/Los_Angeles'))
                
                is_price_window = self.is_price_window()
                
                # Log state changes
                if is_price_window != last_price_window:
                    if is_price_window:
                        print("\n💰 PRICE WINDOW STARTED - Switching to high-frequency monitoring")
                    else:
                        print("\n💰 PRICE WINDOW ENDED - Switching to normal monitoring")
                    last_price_window = is_price_window
                
                # Run monitoring cycle
                self.run_monitoring_cycle()
                
                # Determine sleep interval
                if is_price_window:
                    sleep_interval = 30  # 30 seconds during price window
                    print(f"⏰ Price window mode - checking every 30 seconds")
                else:
                    sleep_interval = 3600  # 1 hour normal
                    print(f"⏰ Normal mode - checking every hour")
                
                print(f"💤 Sleeping for {sleep_interval} seconds...")
                time.sleep(sleep_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {e}")

def main():
    try:
        monitor = SupabaseFPLMonitor()
        monitor.start_monitoring()
    except Exception as e:
        print(f"❌ Failed to start monitor: {e}")

if __name__ == "__main__":
    main()
