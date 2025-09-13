#!/usr/bin/env python3
"""
Check Production Monitoring Status
=================================

Simple script to check if the production monitoring service is running
and verify recent activity in Supabase.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def check_supabase_activity():
    """Check recent activity in Supabase"""
    print("🔍 Checking Supabase activity...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Check recent price updates
        response = requests.get(
            f'{supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost,updated_at&updated_at=gte.{datetime.now() - timedelta(hours=1)}&order=updated_at.desc&limit=5',
            headers=headers, timeout=10
        )
        
        if response.status_code == 200:
            recent_updates = response.json()
            if recent_updates:
                print(f"✅ Found {len(recent_updates)} recent price updates:")
                for update in recent_updates:
                    print(f"   • {update['web_name']}: {update['now_cost']} (updated: {update['updated_at']})")
            else:
                print("⚠️  No recent price updates found (last hour)")
        else:
            print(f"❌ Supabase error: {response.status_code}")
            
        # Check recent news updates
        response = requests.get(
            f'{supabase_url}/rest/v1/players?select=fpl_id,web_name,status,news,news_added&news_added=gte.{datetime.now() - timedelta(hours=2)}&order=news_added.desc&limit=5',
            headers=headers, timeout=10
        )
        
        if response.status_code == 200:
            recent_news = response.json()
            if recent_news:
                print(f"✅ Found {len(recent_news)} recent news updates:")
                for news in recent_news:
                    if news.get('news'):
                        print(f"   • {news['web_name']}: {news['news'][:50]}...")
            else:
                print("ℹ️  No recent news updates found (last 2 hours)")
        
        # Check monitoring history
        response = requests.get(
            f'{supabase_url}/rest/v1/live_monitor_history?change_timestamp=gte.{datetime.now() - timedelta(hours=1)}&order=change_timestamp.desc&limit=10',
            headers=headers, timeout=10
        )
        
        if response.status_code == 200:
            history = response.json()
            if history:
                print(f"✅ Found {len(history)} recent monitoring events:")
                for event in history[:3]:
                    print(f"   • {event['change_type']}: {event['player_name']} ({event['change_timestamp']})")
            else:
                print("⚠️  No recent monitoring events found")
                
    except Exception as e:
        print(f"❌ Error checking Supabase: {e}")

def check_local_api():
    """Check if local API is responding"""
    print("\n🌐 Checking local API...")
    
    try:
        # Check health endpoint
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Local API is responding")
        else:
            print(f"⚠️  Local API returned status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Local API is not responding (service may not be running)")
    except Exception as e:
        print(f"❌ Error checking local API: {e}")

def check_monitoring_status():
    """Check monitoring service status"""
    print("\n📊 Checking monitoring status...")
    
    try:
        # Check health endpoint
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            status = response.json()
            print("✅ Event-based monitoring service is active")
            print(f"   • Service: {status.get('service', 'Unknown')}")
            print(f"   • Version: {status.get('version', 'Unknown')}")
            print(f"   • Architecture: {status.get('architecture', 'Unknown')}")
            print(f"   • Monitoring active: {status.get('monitoring_active', False)}")
        else:
            print(f"⚠️  Health check returned: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Monitoring service not responding")
    except Exception as e:
        print(f"❌ Error checking monitoring status: {e}")
    
    # Check events endpoint
    try:
        response = requests.get('http://localhost:8000/api/v1/events/recent?limit=5', timeout=5)
        if response.status_code == 200:
            events = response.json().get('events', [])
            print(f"✅ Events endpoint working - {len(events)} recent events")
            if events:
                print("   Recent events:")
                for event in events[:3]:
                    print(f"     - {event.get('event_type', 'unknown')}: {event.get('player_name', 'unknown')}")
        else:
            print(f"⚠️  Events endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking events: {e}")

def main():
    """Main checking function"""
    print("🔍 FPL Production Monitoring Status Check")
    print("=" * 50)
    
    check_supabase_activity()
    check_local_api()
    check_monitoring_status()
    
    print("\n" + "=" * 50)
    print("💡 Tips:")
    print("   • Run this script every few hours to verify service health")
    print("   • Check Supabase directly for most recent data")
    print("   • Use 'sudo journalctl -u fpl-monitor -f' for live logs")

if __name__ == "__main__":
    main()
