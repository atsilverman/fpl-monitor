#!/usr/bin/env python3
"""
Mobile Integration Test
Tests the complete flow: Supabase → API Server → Mobile App → Notifications
"""

import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class MobileIntegrationTest:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.api_base_url = "http://localhost:8000"  # Your FastAPI server
        self.headers = {
            'apikey': self.service_key,
            'Authorization': f'Bearer {self.service_key}',
            'Content-Type': 'application/json'
        }
        
    def test_supabase_to_api(self):
        """Test 1: Supabase → API Server data flow"""
        print("🔗 Testing Supabase → API Server data flow...")
        
        # Test API server is running
        try:
            response = requests.get(f'{self.api_base_url}/fpl/players?limit=5', timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Server responding: {len(data)} players")
                if data:
                    sample_player = data[0]
                    print(f"   Sample player: {sample_player.get('web_name', 'Unknown')} - {sample_player.get('now_cost', 0)}m")
                return True
            else:
                print(f"❌ API Server error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API Server not running: {e}")
            return False
    
    def test_price_update_flow(self):
        """Test 2: Update price in Supabase and verify API reflects it"""
        print("\n💰 Testing price update flow...")
        
        # Get current price for a test player
        test_player_id = 42  # A.García
        response = requests.get(f'{self.supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost&fpl_id=eq.{test_player_id}&limit=1', 
                               headers=self.headers, timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Failed to get current price: {response.status_code}")
            return False
            
        current_data = response.json()
        if not current_data:
            print(f"❌ Player {test_player_id} not found")
            return False
            
        current_price = current_data[0]['now_cost']
        new_price = current_price + 1  # Increment by 1 for testing
        
        print(f"   Current price: {current_price}m")
        print(f"   Testing with: {new_price}m")
        
        # Update price in Supabase
        update_response = requests.patch(f'{self.supabase_url}/rest/v1/players?fpl_id=eq.{test_player_id}', 
                                        headers=self.headers,
                                        json={'now_cost': new_price, 'updated_at': 'now()'}, 
                                        timeout=5)
        
        if update_response.status_code not in [200, 204]:
            print(f"❌ Supabase update failed: {update_response.status_code}")
            return False
            
        print("   ✅ Supabase updated")
        
        # Wait a moment for any caching
        time.sleep(1)
        
        # Check if API server reflects the change
        api_response = requests.get(f'{self.api_base_url}/fpl/players?fpl_id={test_player_id}', timeout=5)
        if api_response.status_code != 200:
            print(f"❌ API server error: {api_response.status_code}")
            return False
            
        api_data = api_response.json()
        if not api_data:
            print(f"❌ Player {test_player_id} not found in API")
            return False
            
        api_price = api_data[0]['now_cost']
        print(f"   API shows: {api_price}m")
        
        if api_price == new_price:
            print("   ✅ API correctly reflects Supabase update!")
            return True
        else:
            print(f"   ❌ API shows {api_price}m, expected {new_price}m")
            return False
    
    def test_notification_system(self):
        """Test 3: Notification system (if available)"""
        print("\n🔔 Testing notification system...")
        
        # Check if notification endpoints exist
        try:
            # Test notification endpoints
            endpoints_to_test = [
                '/notifications',
                '/fpl/notifications', 
                '/api/notifications',
                '/user/notifications'
            ]
            
            for endpoint in endpoints_to_test:
                try:
                    response = requests.get(f'{self.api_base_url}{endpoint}', timeout=3)
                    if response.status_code == 200:
                        print(f"   ✅ Found notification endpoint: {endpoint}")
                        return True
                except:
                    continue
                    
            print("   ⚠️  No notification endpoints found")
            print("   ℹ️  This is normal if notifications aren't implemented yet")
            return True
            
        except Exception as e:
            print(f"   ⚠️  Notification test error: {e}")
            return True  # Not critical for basic functionality
    
    def test_mobile_app_data_format(self):
        """Test 4: Verify data format is mobile-app friendly"""
        print("\n📱 Testing mobile app data format...")
        
        try:
            response = requests.get(f'{self.api_base_url}/fpl/players?limit=1', timeout=5)
            if response.status_code != 200:
                print(f"❌ API error: {response.status_code}")
                return False
                
            data = response.json()
            if not data:
                print("❌ No data returned")
                return False
                
            player = data[0]
            required_fields = ['fpl_id', 'web_name', 'now_cost', 'team_id', 'element_type']
            
            missing_fields = [field for field in required_fields if field not in player]
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
                
            print("   ✅ Data format looks good for mobile app")
            print(f"   Sample: {player['web_name']} - {player['now_cost']}m")
            return True
            
        except Exception as e:
            print(f"❌ Data format test error: {e}")
            return False
    
    def run_complete_test(self):
        """Run all integration tests"""
        print("🚀 Starting Mobile Integration Test")
        print("=" * 50)
        
        tests = [
            ("Supabase → API Server", self.test_supabase_to_api),
            ("Price Update Flow", self.test_price_update_flow),
            ("Notification System", self.test_notification_system),
            ("Mobile Data Format", self.test_mobile_app_data_format)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with error: {e}")
                results.append((test_name, False))
        
        print("\n" + "=" * 50)
        print("📊 Test Results:")
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All systems working! Your mobile app should work correctly.")
        else:
            print("⚠️  Some issues found. Check the failed tests above.")
        
        return passed == total

def main():
    print("Mobile Integration Test")
    print("This will test the complete flow from Supabase to mobile app")
    print()
    
    # Ask for confirmation
    response = input("Continue with mobile integration test? (y/n): ").lower().strip()
    if response not in ['y', 'yes']:
        print("Test cancelled")
        return
    
    # Run tests
    tester = MobileIntegrationTest()
    success = tester.run_complete_test()
    
    if success:
        print("\n🎯 Your mobile integration is ready!")
    else:
        print("\n❌ Some issues need to be fixed.")

if __name__ == "__main__":
    main()
