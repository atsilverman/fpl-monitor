#!/usr/bin/env python3
"""
Fix Supabase prices by updating them with current FPL API data
This addresses the critical issue where monitoring service updates wrong database
"""

import os
import requests
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    print("🔧 FIXING SUPABASE PRICE SYNC ISSUE")
    print("=" * 50)
    
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
    
    # Try to connect to Supabase
    print("\n2. Connecting to Supabase...")
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("   ❌ No DATABASE_URL found in environment")
        return
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        print("   ✅ Connected to Supabase")
        
        # Check current Solanke price in Supabase
        cur.execute("SELECT fpl_id, web_name, now_cost, updated_at FROM players WHERE fpl_id = 596")
        result = cur.fetchone()
        
        if result:
            fpl_id, web_name, now_cost, updated_at = result
            print(f"   📊 Supabase Solanke: {web_name}, Price: {now_cost} (raw), {now_cost/10:.1f}m, Updated: {updated_at}")
        else:
            print("   ❌ Solanke not found in Supabase")
            return
        
        # Update all player prices
        print("\n3. Updating player prices in Supabase...")
        updated_count = 0
        
        for player in players:
            fpl_id = player['id']
            now_cost = player['now_cost']
            
            cur.execute("""
                UPDATE players 
                SET now_cost = %s, updated_at = CURRENT_TIMESTAMP
                WHERE fpl_id = %s
            """, (now_cost, fpl_id))
            
            if cur.rowcount > 0:
                updated_count += 1
        
        conn.commit()
        print(f"   ✅ Updated {updated_count} players in Supabase")
        
        # Verify Solanke update
        cur.execute("SELECT fpl_id, web_name, now_cost, updated_at FROM players WHERE fpl_id = 596")
        result = cur.fetchone()
        
        if result:
            fpl_id, web_name, now_cost, updated_at = result
            print(f"   📊 Updated Supabase Solanke: {web_name}, Price: {now_cost} (raw), {now_cost/10:.1f}m, Updated: {updated_at}")
        
        cur.close()
        conn.close()
        
        print("\n🎉 SUPABASE PRICES UPDATED SUCCESSFULLY!")
        print("   Your mobile app should now show correct prices")
        
    except Exception as e:
        print(f"   ❌ Error updating Supabase: {e}")
        print("\n🔧 TROUBLESHOOTING:")
        print("   1. Check your .env file has correct DATABASE_URL")
        print("   2. Verify Supabase credentials are valid")
        print("   3. Ensure Supabase database is accessible")
        
        # Try alternative connection method
        print("\n🔄 Trying alternative connection...")
        try:
            # Try with different connection parameters
            conn = psycopg2.connect(
                host="db.ukeptogquyuxaohgvhwd.supabase.co",
                port="5432",
                database="postgres",
                user="postgres",
                password=os.getenv('SUPABASE_DB_PASSWORD', '')
            )
            print("   ✅ Alternative connection successful")
            conn.close()
        except Exception as e2:
            print(f"   ❌ Alternative connection also failed: {e2}")

if __name__ == "__main__":
    main()

