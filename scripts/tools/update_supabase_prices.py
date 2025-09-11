#!/usr/bin/env python3
"""
Update Supabase with current FPL API prices
"""

import os
import requests
import psycopg2
from dotenv import load_dotenv

def update_supabase_prices():
    load_dotenv()
    
    # Get current prices from FPL API
    print("Fetching current prices from FPL API...")
    response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")
    data = response.json()
    
    players = data['elements']
    print(f"Found {len(players)} players in FPL API")
    
    # Find Solanke
    solanke = None
    for player in players:
        if player['id'] == 596:  # Solanke's FPL ID
            solanke = player
            break
    
    if solanke:
        print(f"FPL API Solanke: {solanke['web_name']}, Price: {solanke['now_cost']} (raw), {solanke['now_cost']/10:.1f}m")
    
    # Try to connect to Supabase
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ No DATABASE_URL found")
        return
    
    try:
        print("Connecting to Supabase...")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check current Solanke price in Supabase
        cur.execute("SELECT fpl_id, web_name, now_cost FROM players WHERE fpl_id = 596")
        result = cur.fetchone()
        
        if result:
            fpl_id, web_name, now_cost = result
            print(f"Supabase Solanke: {web_name}, Price: {now_cost} (raw), {now_cost/10:.1f}m")
        else:
            print("Solanke not found in Supabase")
        
        # Update all player prices
        print("Updating player prices in Supabase...")
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
        print(f"✅ Updated {updated_count} players in Supabase")
        
        # Check Solanke again
        cur.execute("SELECT fpl_id, web_name, now_cost FROM players WHERE fpl_id = 596")
        result = cur.fetchone()
        
        if result:
            fpl_id, web_name, now_cost = result
            print(f"Updated Supabase Solanke: {web_name}, Price: {now_cost} (raw), {now_cost/10:.1f}m")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error updating Supabase: {e}")
        print("This might be due to authentication issues with Supabase")

if __name__ == "__main__":
    update_supabase_prices()

