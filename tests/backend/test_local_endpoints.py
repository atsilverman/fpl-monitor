#!/usr/bin/env python3
"""
Test the new manager and league endpoints locally
"""

import requests
import json

def test_endpoints():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Manager and League Endpoints Locally")
    print("=" * 50)
    
    # Test manager search by ID
    print("\n1. Testing manager search by ID (344182)...")
    try:
        response = requests.get(f"{base_url}/api/v1/managers/search?query=344182", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data.get('managers', []))} managers")
            if data.get('managers'):
                manager = data['managers'][0]
                print(f"   Manager: {manager.get('player_name')} (ID: {manager.get('id')})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test manager details
    print("\n2. Testing manager details (344182)...")
    try:
        response = requests.get(f"{base_url}/api/v1/managers/344182", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Manager: {data.get('player_name')} (ID: {data.get('id')})")
            print(f"   Points: {data.get('summary_overall_points')}")
            print(f"   Rank: {data.get('summary_overall_rank')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test manager leagues
    print("\n3. Testing manager leagues (344182)...")
    try:
        response = requests.get(f"{base_url}/api/v1/managers/344182/leagues", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            classic_leagues = data.get('classic', [])
            print(f"   Found {len(classic_leagues)} classic leagues")
            for league in classic_leagues[:3]:  # Show first 3
                print(f"   - {league.get('name')} (ID: {league.get('id')})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test league details
    print("\n4. Testing league details (814685)...")
    try:
        response = requests.get(f"{base_url}/api/v1/leagues/814685", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   League: {data.get('league', {}).get('name')}")
            print(f"   Members: {data.get('league', {}).get('rank_count')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_endpoints()
