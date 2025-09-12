#!/usr/bin/env python3
"""
Setup Supabase Monitoring Log
============================
Sets up the monitoring log system with Supabase.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

def setup_supabase_monitoring():
    """Set up monitoring log system with Supabase"""
    load_dotenv()
    
    print("🔧 Setting up Supabase monitoring log system...")
    
    # Check if Supabase credentials are available
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Missing Supabase credentials in .env file")
        print("   Please ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set")
        return False
    
    print("✅ Supabase credentials found")
    
    # Test Supabase connection
    try:
        headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }
        
        # Test connection
        response = requests.get(f"{url}/rest/v1/", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Supabase connection successful")
        else:
            print(f"❌ Supabase connection failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False
    
    print("\n📋 Next steps:")
    print("1. Go to your Supabase Dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Copy and paste the contents of database/supabase_monitoring_log.sql")
    print("4. Run the SQL to create the monitoring_log table and views")
    print("5. Test with: python3 scripts/tools/check_supabase_monitoring_status.py")
    
    return True

if __name__ == "__main__":
    setup_supabase_monitoring()
