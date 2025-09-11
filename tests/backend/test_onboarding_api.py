#!/usr/bin/env python3
"""
Test script for onboarding API endpoints
Tests manager search and league functionality
"""

import requests
import json

# API base URL
BASE_URL = "http://138.68.28.59:8000/api/v1"

def test_api_endpoint(endpoint, description):
    """Test an API endpoint and print results"""
    print(f"\n🧪 Testing: {description}")
    print(f"📍 URL: {BASE_URL}{endpoint}")
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Response: {json.dumps(data, indent=2)[:200]}...")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🚀 FPL Monitor Onboarding API Test")
    print("=" * 50)
    
    # Test basic health
    test_api_endpoint("/", "Health Check")
    
    # Test manager search
    test_api_endpoint("/managers/search?query=test", "Manager Search (by name)")
    test_api_endpoint("/managers/search?query=12345", "Manager Search (by ID)")
    
    # Test league search
    test_api_endpoint("/leagues/search?query=test", "League Search")
    
    # Test specific manager (if we have one)
    test_api_endpoint("/managers/12345", "Manager Details (ID: 12345)")
    test_api_endpoint("/managers/12345/leagues", "Manager Leagues (ID: 12345)")
    
    # Test league details
    test_api_endpoint("/leagues/12345", "League Details (ID: 12345)")
    
    print("\n🎯 Test Complete!")
    print("\nTo test with real data:")
    print("1. Find a real FPL manager ID from fantasy.premierleague.com")
    print("2. Replace 12345 with the real ID in the URLs above")
    print("3. Run the test again")

if __name__ == "__main__":
    main()
