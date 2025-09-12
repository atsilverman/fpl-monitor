#!/usr/bin/env python3
"""
Check Simple Monitoring Status
=============================
Quick script to check the status of all monitoring services using simple HTTP requests.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from services.simple_monitoring_logger import check_monitoring_status
from datetime import datetime, timezone

def main():
    print(f"🔍 Checking monitoring status at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    services = check_monitoring_status()
    
    if not services:
        print("❌ No monitoring services found or Supabase connection failed")
        print("\n💡 Make sure you've:")
        print("   1. Created the monitoring_log table in Supabase SQL Editor")
        print("   2. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        return
    
    # Summary
    online_count = sum(1 for s in services if s['health_status'] in ['running', 'recent'])
    total_count = len(services)
    
    print(f"\n📊 SUMMARY: {online_count}/{total_count} services online")
    
    # Check for offline services
    offline_services = [s for s in services if s['health_status'] == 'offline']
    if offline_services:
        print(f"\n⚠️  OFFLINE SERVICES:")
        for service in offline_services:
            print(f"   - {service['service_name']} (last run: {service['started_at']})")
    
    # Check for stale services
    stale_services = [s for s in services if s['health_status'] == 'stale']
    if stale_services:
        print(f"\n🟡 STALE SERVICES:")
        for service in stale_services:
            print(f"   - {service['service_name']} (last run: {service['started_at']})")

if __name__ == "__main__":
    main()
