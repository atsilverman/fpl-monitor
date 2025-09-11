#!/usr/bin/env python3
"""
Fast Supabase update using bulk operations
"""

import os
import requests
import json
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    print("🚀 FAST SUPABASE UPDATE")
    print("=" * 30)
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return
    
    # Get current prices from FPL API
    print("1. Fetching FPL API data...")
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        response.raise_for_status()
        data = response.json()
        players = data['elements']
        print(f"   ✅ Found {len(players)} players")
    except Exception as e:
        print(f"   ❌ FPL API error: {e}")
        return
    
    # Find Solanke
    solanke = None
    for player in players:
        if player['id'] == 596:
            solanke = player
            break
    
    if solanke:
        print(f"   📊 FPL Solanke: {solanke['web_name']}, Price: {solanke['now_cost']/10:.1f}m")
    
    # Check current Solanke in Supabase
    print("\n2. Checking current Supabase data...")
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/players?fpl_id=eq.596&select=fpl_id,web_name,now_cost",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data:
                player = data[0]
                print(f"   📊 Supabase Solanke: {player['web_name']}, Price: {player['now_cost']/10:.1f}m")
            else:
                print("   ❌ Solanke not found")
                return
        else:
            print(f"   ❌ Supabase error: {response.status_code}")
            return
            
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return
    
    # Fast bulk update using upsert
    print("\n3. Fast bulk update...")
    try:
        # Prepare bulk data
        bulk_data = []
        for player in players:
            bulk_data.append({
                'fpl_id': player['id'],
                'now_cost': player['now_cost'],
                'web_name': player['web_name'],
                'updated_at': 'now()'
            })
        
        # Use upsert for bulk update
        response = requests.post(
            f"{supabase_url}/rest/v1/players",
            headers={
                **headers,
                'Prefer': 'resolution=merge-duplicates'
            },
            json=bulk_data
        )
        
        if response.status_code in [200, 201]:
            print(f"   ✅ Bulk update successful!")
        else:
            print(f"   ❌ Bulk update failed: {response.status_code} - {response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ Bulk update error: {e}")
        return
    
    # Verify Solanke
    print("\n4. Verifying update...")
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/players?fpl_id=eq.596&select=fpl_id,web_name,now_cost",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data:
                player = data[0]
                print(f"   📊 Updated Solanke: {player['web_name']}, Price: {player['now_cost']/10:.1f}m")
                
                if player['now_cost'] == 72:
                    print("   🎉 SUCCESS! Solanke is now 7.2m")
                else:
                    print(f"   ⚠️ Still wrong: {player['now_cost']/10:.1f}m")
            else:
                print("   ❌ Solanke not found after update")
        else:
            print(f"   ❌ Verification failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
    
    print("\n🎉 UPDATE COMPLETE!")

if __name__ == "__main__":
    main()

