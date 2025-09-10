#!/usr/bin/env python3
"""
Quick Health Check
==================

Quick health check for your FPL Monitor cloud server.
Run this anytime to verify everything is working.
"""

import requests
import json
from datetime import datetime

def quick_health_check():
    """Run a quick health check"""
    print("🔍 FPL Monitor - Quick Health Check")
    print("=" * 40)
    print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    server_url = "http://138.68.28.59:8000"
    
    # Check 1: Server health
    print("1. Server Health:")
    try:
        response = requests.get(f"{server_url}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Server responding - {data.get('status', 'unknown')}")
        else:
            print(f"   ❌ Server error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Server unreachable: {e}")
        return False
    
    # Check 2: Monitoring status
    print("2. Monitoring Status:")
    try:
        response = requests.get(f"{server_url}/api/v1/monitoring/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            active = status.get('monitoring_active', False)
            game_state = status.get('current_game_state', 'unknown')
            fpl_connected = status.get('fpl_api_connected', False)
            
            print(f"   ✅ Monitoring active: {active}")
            print(f"   ✅ Game state: {game_state}")
            print(f"   ✅ FPL API connected: {fpl_connected}")
        else:
            print(f"   ❌ Monitoring status error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Monitoring status error: {e}")
        return False
    
    # Check 3: Recent activity
    print("3. Recent Activity:")
    try:
        response = requests.get(f"{server_url}/api/v1/notifications?limit=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            recent = len(data.get('notifications', []))
            gameweek = data.get('current_gameweek', 0)
            
            print(f"   ✅ Total notifications: {total}")
            print(f"   ✅ Current gameweek: {gameweek}")
            print(f"   ✅ Recent notifications: {recent}")
        else:
            print(f"   ❌ Notifications error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Notifications error: {e}")
        return False
    
    # Check 4: FPL API
    print("4. FPL API Connection:")
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            players = len(data.get('elements', []))
            teams = len(data.get('teams', []))
            print(f"   ✅ FPL API connected")
            print(f"   ✅ Players: {players}, Teams: {teams}")
        else:
            print(f"   ❌ FPL API error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ FPL API error: {e}")
        return False
    
    print("\n🎉 All systems healthy!")
    print("   Your FPL Monitor is running perfectly.")
    return True

if __name__ == "__main__":
    success = quick_health_check()
    exit(0 if success else 1)
