#!/usr/bin/env python3
"""
Update Supabase directly using REST API
"""

import os
import requests
import json
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    print("🔧 UPDATING SUPABASE PRICES DIRECTLY")
    print("=" * 50)
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return
    
    # Get current prices from FPL API
    print("1. Fetching current prices from FPL API...")
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=30)
        response.raise_for_status()
        data = response.json()
        players = data['elements']
        print(f"   ✅ Found {len(players)} players in FPL API")
    except Exception as e:
        print(f"   ❌ Failed to fetch FPL API: {e}")
        return
    
    # Find Solanke
    solanke = None
    for player in players:
        if player['id'] == 596:  # Solanke's FPL ID
            solanke = player
            break
    
    if solanke:
        print(f"   📊 FPL API Solanke: {solanke['web_name']}, Price: {solanke['now_cost']} (raw), {solanke['now_cost']/10:.1f}m")
    else:
        print("   ❌ Solanke not found in FPL API")
        return
    
    # Check current Solanke in Supabase
    print("\n2. Checking current Solanke in Supabase...")
    try:
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{supabase_url}/rest/v1/players?fpl_id=eq.596&select=fpl_id,web_name,now_cost,updated_at",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data:
                player = data[0]
                print(f"   📊 Supabase Solanke: {player['web_name']}, Price: {player['now_cost']} (raw), {player['now_cost']/10:.1f}m, Updated: {player['updated_at']}")
            else:
                print("   ❌ Solanke not found in Supabase")
                return
        else:
            print(f"   ❌ Failed to fetch from Supabase: {response.status_code} - {response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ Error checking Supabase: {e}")
        return
    
    # Update all player prices
    print("\n3. Updating player prices in Supabase...")
    updated_count = 0
    
    for player in players:
        fpl_id = player['id']
        now_cost = player['now_cost']
        
        try:
            # Update the player price
            update_data = {
                'now_cost': now_cost,
                'updated_at': 'now()'
            }
            
            response = requests.patch(
                f"{supabase_url}/rest/v1/players?fpl_id=eq.{fpl_id}",
                headers=headers,
                json=update_data
            )
            
            if response.status_code in [200, 204]:
                updated_count += 1
            else:
                print(f"   ⚠️ Failed to update player {fpl_id}: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ Error updating player {fpl_id}: {e}")
    
    print(f"   ✅ Updated {updated_count} players in Supabase")
    
    # Verify Solanke update
    print("\n4. Verifying Solanke update...")
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/players?fpl_id=eq.596&select=fpl_id,web_name,now_cost,updated_at",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data:
                player = data[0]
                print(f"   📊 Updated Supabase Solanke: {player['web_name']}, Price: {player['now_cost']} (raw), {player['now_cost']/10:.1f}m, Updated: {player['updated_at']}")
                
                if player['now_cost'] == 72:  # 7.2m
                    print("   🎉 SUCCESS! Solanke price is now correct (7.2m)")
                else:
                    print(f"   ⚠️ Price still incorrect: {player['now_cost']/10:.1f}m")
            else:
                print("   ❌ Solanke not found after update")
        else:
            print(f"   ❌ Failed to verify update: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error verifying update: {e}")
    
    print("\n🎉 SUPABASE UPDATE COMPLETE!")
    print("   Your mobile app should now show correct prices")

if __name__ == "__main__":
    main()

