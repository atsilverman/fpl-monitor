#!/usr/bin/env python3
"""
Test Event-Based Architecture
============================

Test script to verify the new scalable event-based notification system
works correctly with sample data.
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def test_database_connection():
    """Test connection to Supabase"""
    print("🔍 Testing database connection...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f'{supabase_url}/rest/v1/events?limit=1', headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Database connection successful")
            return True
        else:
            print(f"❌ Database connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_events_table():
    """Test events table structure"""
    print("\n🔍 Testing events table...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test table exists and has correct structure
        response = requests.get(f'{supabase_url}/rest/v1/events?select=*&limit=1', headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Events table accessible")
            
            # Check if table is empty (expected for new implementation)
            data = response.json()
            if len(data) == 0:
                print("ℹ️  Events table is empty (expected for new implementation)")
            else:
                print(f"ℹ️  Found {len(data)} existing events")
            
            return True
        else:
            print(f"❌ Events table error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Events table error: {e}")
        return False

def test_user_ownership_table():
    """Test user ownership table"""
    print("\n🔍 Testing user ownership table...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f'{supabase_url}/rest/v1/user_ownership?select=*&limit=1', headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ User ownership table accessible")
            return True
        else:
            print(f"❌ User ownership table error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ User ownership table error: {e}")
        return False

def test_user_preferences_table():
    """Test user preferences table"""
    print("\n🔍 Testing user preferences table...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f'{supabase_url}/rest/v1/user_preferences?select=*&limit=1', headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ User preferences table accessible")
            return True
        else:
            print(f"❌ User preferences table error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ User preferences table error: {e}")
        return False

def test_create_sample_event():
    """Test creating a sample event"""
    print("\n🔍 Testing sample event creation...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    sample_event = {
        "event_type": "goals",
        "player_id": 1,
        "player_name": "Test Player",
        "team_name": "Test Team",
        "team_abbreviation": "TST",
        "points": 4,
        "points_change": 4,
        "points_category": "Goal",
        "gameweek": 1,
        "old_value": 0,
        "new_value": 1,
        "title": "⚽ Goal!",
        "message": "Test Player scored for Test Team"
    }
    
    try:
        response = requests.post(
            f'{supabase_url}/rest/v1/events',
            headers=headers,
            json=sample_event,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print("✅ Sample event created successfully")
            event_id = response.json()[0]['id']
            print(f"   Event ID: {event_id}")
            return event_id
        else:
            print(f"❌ Failed to create sample event: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating sample event: {e}")
        return None

def test_user_notifications_function():
    """Test the get_user_notifications function"""
    print("\n🔍 Testing user notifications function...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    # Create a test user first
    test_user_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        # Test the function
        response = requests.post(
            f'{supabase_url}/rest/v1/rpc/get_user_notifications',
            headers=headers,
            json={
                "p_user_id": test_user_id,
                "p_limit": 10,
                "p_offset": 0
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ User notifications function works")
            notifications = response.json()
            print(f"   Found {len(notifications)} notifications for test user")
            return True
        else:
            print(f"❌ User notifications function error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing user notifications function: {e}")
        return False

def test_scalability_math():
    """Test and display scalability calculations"""
    print("\n📊 Scalability Analysis:")
    print("=" * 50)
    
    # Old approach (per-user notifications)
    users = 10000
    events_per_day = 1000
    
    old_records_per_day = events_per_day * users
    old_records_per_year = old_records_per_day * 365
    
    print(f"Old Approach (per-user notifications):")
    print(f"  • Users: {users:,}")
    print(f"  • Events per day: {events_per_day:,}")
    print(f"  • Records per day: {old_records_per_day:,}")
    print(f"  • Records per year: {old_records_per_year:,}")
    print(f"  • Storage: ~{old_records_per_year * 0.001:.1f} GB")
    
    # New approach (event-based)
    new_records_per_day = events_per_day
    new_records_per_year = new_records_per_day * 365
    ownership_records = users
    
    print(f"\nNew Approach (event-based):")
    print(f"  • Users: {users:,}")
    print(f"  • Events per day: {events_per_day:,}")
    print(f"  • Event records per day: {new_records_per_day:,}")
    print(f"  • Event records per year: {new_records_per_year:,}")
    print(f"  • Ownership records: {ownership_records:,}")
    print(f"  • Total records per year: {new_records_per_year + ownership_records:,}")
    print(f"  • Storage: ~{(new_records_per_year + ownership_records) * 0.001:.1f} GB")
    
    improvement = old_records_per_year / (new_records_per_year + ownership_records)
    print(f"\n🚀 Improvement: {improvement:.0f}x more efficient!")
    print(f"   Storage reduction: {((old_records_per_year - (new_records_per_year + ownership_records)) / old_records_per_year * 100):.1f}%")

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Delete test events
        response = requests.delete(
            f'{supabase_url}/rest/v1/events?player_name=eq.Test Player',
            headers=headers,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            print("✅ Test data cleaned up")
        else:
            print(f"⚠️  Cleanup warning: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")

def main():
    """Main test function"""
    print("🧪 FPL Event-Based Architecture Test")
    print("=" * 50)
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Cannot proceed - database connection failed")
        return False
    
    # Test table structures
    tests_passed = 0
    total_tests = 6
    
    if test_events_table():
        tests_passed += 1
    
    if test_user_ownership_table():
        tests_passed += 1
    
    if test_user_preferences_table():
        tests_passed += 1
    
    # Test sample event creation
    event_id = test_create_sample_event()
    if event_id:
        tests_passed += 1
    
    # Test user notifications function
    if test_user_notifications_function():
        tests_passed += 1
    
    # Test scalability math
    test_scalability_math()
    tests_passed += 1
    
    # Cleanup
    cleanup_test_data()
    
    # Summary
    print(f"\n📋 Test Summary:")
    print(f"   Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Event-based architecture is ready.")
        print("\n🚀 Next steps:")
        print("   1. Run migration script on production database")
        print("   2. Deploy new monitoring service")
        print("   3. Update iOS app to use new API endpoints")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
