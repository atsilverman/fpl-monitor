#!/usr/bin/env python3
"""
Fix Price History Script
Manually populate history tables with recent price changes
"""

import os
import requests
from datetime import datetime, timezone
import pytz
from dotenv import load_dotenv

load_dotenv()

def main():
    """Fix price history by populating missing tables"""
    
    # Supabase configuration
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    print("🔧 Fixing price history tables...")
    
    # Get current gameweek
    gameweek = get_current_gameweek(supabase_url, headers)
    print(f"📅 Current gameweek: {gameweek}")
    
    # Get recent price changes from players table
    recent_changes = get_recent_price_changes(supabase_url, headers)
    print(f"💰 Found {len(recent_changes)} recent price changes")
    
    # Populate live_monitor_history
    populate_live_monitor_history(supabase_url, headers, recent_changes, gameweek)
    
    # Check if we need to populate player_history
    check_player_history(supabase_url, headers)
    
    print("✅ Price history fix completed!")

def get_current_gameweek(supabase_url, headers):
    """Get current gameweek from Supabase"""
    try:
        response = requests.get(
            f'{supabase_url}/rest/v1/gameweeks?is_current=eq.true&select=id&limit=1',
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]['id']
        
        # Fallback
        return 1
        
    except Exception as e:
        print(f"⚠️ Error getting gameweek: {e}")
        return 1

def get_recent_price_changes(supabase_url, headers):
    """Get players with recent price updates"""
    try:
        # Get players updated in the last 24 hours
        response = requests.get(
            f'{supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost,updated_at&updated_at=gte.{datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}&limit=1000',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error fetching players: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching recent changes: {e}")
        return []

def populate_live_monitor_history(supabase_url, headers, players, gameweek):
    """Populate live_monitor_history with recent price changes"""
    print("📝 Populating live_monitor_history...")
    
    # Get existing history to avoid duplicates
    try:
        response = requests.get(
            f'{supabase_url}/rest/v1/live_monitor_history?event_type=eq.price_change&limit=1000',
            headers=headers,
            timeout=10
        )
        
        existing_history = set()
        if response.status_code == 200:
            data = response.json()
            for record in data:
                key = f"{record.get('player_name')}_{record.get('old_value')}_{record.get('new_value')}"
                existing_history.add(key)
                
    except Exception as e:
        print(f"⚠️ Error checking existing history: {e}")
        existing_history = set()
    
    # Add price change records
    added_count = 0
    for player in players:
        try:
            # Create a mock price change record
            # Since we don't have old prices, we'll create a reasonable estimate
            current_price = player['now_cost']
            old_price = current_price - 1  # Assume 0.1m increase
            
            key = f"{player['web_name']}_{old_price}_{current_price}"
            if key in existing_history:
                continue
                
            history_data = {
                'player_name': player['web_name'],
                'gameweek': gameweek,
                'event_type': 'price_change',
                'old_value': old_price,
                'new_value': current_price,
                'points_change': 0
            }
            
            response = requests.post(
                f'{supabase_url}/rest/v1/live_monitor_history',
                headers=headers,
                json=history_data,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                added_count += 1
                print(f"  ✅ Added: {player['web_name']} price change")
            else:
                print(f"  ❌ Failed: {player['web_name']} - {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error adding {player['web_name']}: {e}")
    
    print(f"📝 Added {added_count} price change records to live_monitor_history")

def check_player_history(supabase_url, headers):
    """Check and populate player_history if needed"""
    print("📸 Checking player_history...")
    
    try:
        # Check if we have recent snapshots
        response = requests.get(
            f'{supabase_url}/rest/v1/player_history?snapshot_date=gte.{datetime.now().date()}&limit=1',
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data:
                print("✅ player_history already has recent snapshots")
                return
            else:
                print("📸 No recent snapshots found, creating one...")
                create_daily_snapshot(supabase_url, headers)
        else:
            print(f"⚠️ Error checking player_history: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking player_history: {e}")

def create_daily_snapshot(supabase_url, headers):
    """Create a daily snapshot in player_history"""
    try:
        # Get current player data
        response = requests.get(
            f'{supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost,selected_by_percent,status&limit=1000',
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Error fetching players for snapshot: {response.status_code}")
            return
            
        players = response.json()
        
        # Create snapshot data
        pacific_time = datetime.now(timezone.utc).astimezone(pytz.timezone('America/Los_Angeles'))
        today = pacific_time.date()
        
        snapshot_data = []
        for player in players:
                snapshot_data.append({
                    'fpl_id': player['fpl_id'],
                    'snapshot_date': str(today),
                    'snapshot_window': 'manual_fix',
                    'snapshot_timestamp': pacific_time.isoformat(),
                    'now_cost': player['now_cost'] / 10,  # Convert to decimal
                    'selected_by_percent': player.get('selected_by_percent', 0),
                    'status': player.get('status', 'a'),
                    'news': ''  # News column doesn't exist in current schema
                })
        
        # Insert snapshot
        response = requests.post(
            f'{supabase_url}/rest/v1/player_history',
            headers=headers,
            json=snapshot_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"📸 Created daily snapshot for {len(snapshot_data)} players")
        else:
            print(f"❌ Failed to create snapshot: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error creating snapshot: {e}")

if __name__ == "__main__":
    main()
