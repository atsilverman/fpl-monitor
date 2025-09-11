#!/usr/bin/env python3
"""
FPL Price Monitoring Simulation Test
This script simulates the real FPL price monitoring process to test the entire system.
"""

import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class FPLPriceMonitoringSimulation:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.headers = {
            'apikey': self.service_key,
            'Authorization': f'Bearer {self.service_key}',
            'Content-Type': 'application/json'
        }
        
    def get_current_fpl_data(self):
        """Get current FPL data from the API"""
        print("📡 Fetching current FPL data...")
        try:
            response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/', timeout=10)
            if response.status_code == 200:
                data = response.json()
                players = data['elements']
                print(f"✅ Fetched {len(players)} players from FPL API")
                return players
            else:
                print(f"❌ FPL API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error fetching FPL data: {e}")
            return None
    
    def get_supabase_players(self):
        """Get current player data from Supabase"""
        print("📊 Fetching current Supabase data...")
        try:
            response = requests.get(f'{self.supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost,updated_at&limit=100', 
                                   headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Fetched {len(data)} players from Supabase")
                return data
            else:
                print(f"❌ Supabase error: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error fetching Supabase data: {e}")
            return None
    
    def detect_price_changes(self, fpl_data, supabase_data):
        """Detect price changes between FPL API and Supabase"""
        print("🔍 Detecting price changes...")
        
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
        
        print(f"📈 Found {len(changes)} price changes:")
        for change in changes[:5]:  # Show first 5 changes
            print(f"  {change['name']} (ID {change['fpl_id']}): {change['old_price']} → {change['new_price']} ({change['change']:+d})")
        if len(changes) > 5:
            print(f"  ... and {len(changes) - 5} more")
            
        return changes
    
    def update_supabase_prices(self, changes):
        """Update Supabase with new prices"""
        if not changes:
            print("ℹ️  No price changes to update")
            return True
            
        print(f"🔄 Updating {len(changes)} players in Supabase...")
        
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
                    print(f"  ✅ {change['name']}: {change['old_price']} → {change['new_price']}")
                else:
                    print(f"  ❌ {change['name']}: Failed ({response.status_code})")
                    
            except Exception as e:
                print(f"  ❌ {change['name']}: Error - {e}")
        
        print(f"📊 Updated {success_count}/{len(changes)} players successfully")
        return success_count == len(changes)
    
    def verify_updates(self, changes):
        """Verify that updates were successful"""
        if not changes:
            return True
            
        print("🔍 Verifying updates...")
        
        fpl_ids = [change['fpl_id'] for change in changes]
        response = requests.get(
            f'{self.supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost&fpl_id=in.({",".join(map(str, fpl_ids))})',
            headers=self.headers,
            timeout=10
        )
        
        if response.status_code == 200:
            updated_players = response.json()
            print("📋 Verification results:")
            
            all_correct = True
            for change in changes:
                updated_player = next((p for p in updated_players if p['fpl_id'] == change['fpl_id']), None)
                if updated_player:
                    if updated_player['now_cost'] == change['new_price']:
                        print(f"  ✅ {change['name']}: {updated_player['now_cost']} (correct)")
                    else:
                        print(f"  ❌ {change['name']}: {updated_player['now_cost']} (expected {change['new_price']})")
                        all_correct = False
                else:
                    print(f"  ❌ {change['name']}: Not found in Supabase")
                    all_correct = False
            
            return all_correct
        else:
            print(f"❌ Verification failed: {response.status_code}")
            return False
    
    def run_simulation(self):
        """Run the complete price monitoring simulation"""
        print("🚀 Starting FPL Price Monitoring Simulation")
        print("=" * 50)
        
        # Step 1: Get current data
        fpl_data = self.get_current_fpl_data()
        if not fpl_data:
            print("❌ Failed to get FPL data")
            return False
        
        supabase_data = self.get_supabase_players()
        if not supabase_data:
            print("❌ Failed to get Supabase data")
            return False
        
        # Step 2: Detect changes
        changes = self.detect_price_changes(fpl_data, supabase_data)
        
        # Step 3: Update Supabase
        if changes:
            update_success = self.update_supabase_prices(changes)
            if not update_success:
                print("❌ Failed to update some prices")
                return False
            
            # Step 4: Verify updates
            verification_success = self.verify_updates(changes)
            if not verification_success:
                print("❌ Verification failed")
                return False
        
        print("=" * 50)
        print("🎉 Simulation completed successfully!")
        print(f"📊 Processed {len(fpl_data)} players from FPL API")
        print(f"📊 Updated {len(changes)} players in Supabase")
        print("✅ All systems working correctly!")
        
        return True

def main():
    print("FPL Price Monitoring Simulation Test")
    print("This will test the complete monitoring system with real FPL data")
    print()
    
    # Ask for confirmation
    response = input("Continue with simulation? (y/n): ").lower().strip()
    if response not in ['y', 'yes']:
        print("Simulation cancelled")
        return
    
    # Run simulation
    simulation = FPLPriceMonitoringSimulation()
    success = simulation.run_simulation()
    
    if success:
        print("\n🎯 Your monitoring system is ready for production!")
        print("The next FPL price changes will be automatically detected and updated.")
    else:
        print("\n❌ Simulation failed. Please check the errors above.")

if __name__ == "__main__":
    main()
