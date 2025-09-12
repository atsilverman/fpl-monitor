#!/usr/bin/env python3
"""
Setup Monitoring State Table
============================
Create the monitoring_state table in Supabase for tracking processed gameweeks.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def create_monitoring_state_table():
    """Create monitoring_state table in Supabase"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json'
    }
    
    # SQL to create the table
    sql = """
    CREATE TABLE IF NOT EXISTS monitoring_state (
        id SERIAL PRIMARY KEY,
        gameweek INTEGER NOT NULL,
        bonus_processed BOOLEAN DEFAULT FALSE,
        last_processed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(gameweek)
    );
    
    CREATE INDEX IF NOT EXISTS idx_monitoring_state_gameweek ON monitoring_state(gameweek);
    CREATE INDEX IF NOT EXISTS idx_monitoring_state_bonus ON monitoring_state(bonus_processed);
    """
    
    print("🔧 Creating monitoring_state table...")
    print("📝 Please run this SQL in your Supabase SQL Editor:")
    print("=" * 60)
    print(sql)
    print("=" * 60)
    
    # Try to test the table by inserting a test record
    test_data = {
        'gameweek': 1,
        'bonus_processed': False,
        'last_processed_at': '2025-01-01T00:00:00Z'
    }
    
    try:
        response = requests.post(
            f'{supabase_url}/rest/v1/monitoring_state',
            headers=headers,
            json=test_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print("✅ monitoring_state table is accessible")
        elif response.status_code == 409:
            print("✅ monitoring_state table exists (duplicate key error expected)")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            print("\n💡 Please create the table manually using the SQL above")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Please create the table manually using the SQL above")

if __name__ == "__main__":
    create_monitoring_state_table()
