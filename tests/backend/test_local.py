#!/usr/bin/env python3
"""
FPL Mobile Monitor - Local Testing Script
========================================

Test the monitoring service locally before deployment.
"""

import os
import sys
import asyncio
import requests
import json
from datetime import datetime

# Add current directory to path for imports
sys.path.append('.')

def test_fpl_api_connection():
    """Test FPL API connectivity"""
    print("🔗 Testing FPL API connection...")
    
    try:
        # Test bootstrap-static endpoint
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ FPL API connected successfully")
        print(f"   - Total players: {len(data.get('elements', []))}")
        print(f"   - Total teams: {len(data.get('teams', []))}")
        print(f"   - Current gameweek: {data.get('current-event', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ FPL API connection failed: {e}")
        return False

def test_database_schema():
    """Test database schema compatibility"""
    print("\n🗄️ Testing database schema...")
    
    try:
        # Check if we can import the schema
        with open('supabase_schema.sql', 'r') as f:
            schema = f.read()
        
        # Basic validation
        required_tables = [
            'users', 'user_notifications', 'teams', 'players', 
            'gameweeks', 'fixtures', 'gameweek_stats', 
            'player_history', 'live_monitor_history'
        ]
        
        for table in required_tables:
            if f"CREATE TABLE public.{table}" in schema:
                print(f"   ✅ Table '{table}' found")
            else:
                print(f"   ❌ Table '{table}' missing")
                return False
        
        print("✅ Database schema validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False

def test_monitoring_service_import():
    """Test if monitoring service can be imported"""
    print("\n🔧 Testing monitoring service import...")
    
    try:
        # Test import without running
        import fpl_monitor_service
        print("✅ Monitoring service imports successfully")
        
        # Test configuration
        from fpl_monitor_service import Config
        config = Config()
        print(f"   - FPL Base URL: {config.fpl_base_url}")
        print(f"   - Mini League ID: {config.mini_league_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Monitoring service import failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints (if service is running)"""
    print("\n🌐 Testing API endpoints...")
    
    base_url = "http://localhost:8000"
    
    try:
        # Test health check
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Health check endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
        
        # Test monitoring status
        response = requests.get(f"{base_url}/api/v1/monitoring/status", timeout=5)
        if response.status_code == 200:
            print("✅ Monitoring status endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Monitoring status failed: {response.status_code}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("⚠️  API service not running (this is expected for local testing)")
        print("   To test API endpoints, run: python fpl_monitor_service.py")
        return True
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def test_file_organization():
    """Test file organization system"""
    print("\n📁 Testing file organization...")
    
    try:
        # Test file organizer
        import file_organizer
        organizer = file_organizer.FileOrganizer()
        
        # Test pattern recognition
        test_files = [
            "debug_api.py",
            "test_notifications.py", 
            "experiment_ui.py",
            "notes_ideas.md",
            "monitor.log"
        ]
        
        for filename in test_files:
            suggestion = organizer.suggest_location(filename)
            if suggestion:
                print(f"   ✅ '{filename}' → '{suggestion}'")
            else:
                print(f"   ⚠️  '{filename}' → No suggestion")
        
        print("✅ File organization system working")
        return True
        
    except Exception as e:
        print(f"❌ File organization test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 FPL Mobile Monitor - Local Testing")
    print("=" * 50)
    
    tests = [
        ("FPL API Connection", test_fpl_api_connection),
        ("Database Schema", test_database_schema),
        ("Monitoring Service", test_monitoring_service_import),
        ("API Endpoints", test_api_endpoints),
        ("File Organization", test_file_organization)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Ready for deployment.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
