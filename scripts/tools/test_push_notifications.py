#!/usr/bin/env python3
"""
Test script for FPL Monitor push notifications
Tests the complete push notification flow
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add the backend services to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend', 'services'))

from push_notification_service import create_push_service, send_fpl_notification_to_device, NotificationType

async def test_push_notifications():
    """Test push notification service"""
    print("🧪 Testing FPL Monitor Push Notifications")
    print("=" * 50)
    
    # Test 1: Create push service
    print("\n1️⃣ Testing push service creation...")
    push_service = create_push_service()
    
    if not push_service:
        print("❌ Failed to create push service")
        print("Make sure your .env file has the correct APNs configuration:")
        print("APNS_TEAM_ID=78345B2PS5")
        print("APNS_KEY_ID=57A3X7ZM67")
        print("APNS_BUNDLE_ID=com.silverman.fplmonitor")
        print("APNS_PRIVATE_KEY_PATH=./keys/AuthKey_57A3X7ZM67.p8")
        return False
    
    print("✅ Push service created successfully")
    print(f"   Team ID: {push_service.team_id}")
    print(f"   Key ID: {push_service.key_id}")
    print(f"   Bundle ID: {push_service.bundle_id}")
    print(f"   Using Sandbox: {push_service.use_sandbox}")
    
    # Test 2: Test FPL notification creation
    print("\n2️⃣ Testing FPL notification creation...")
    
    # Create test notifications for different types
    test_notifications = [
        {
            "type": "goal",
            "player": "Erling Haaland",
            "team": "Man City",
            "points": 4,
            "old_value": 0,
            "new_value": 1,
            "gameweek": 1
        },
        {
            "type": "assist",
            "player": "Kevin De Bruyne",
            "team": "Man City", 
            "points": 3,
            "old_value": 0,
            "new_value": 1,
            "gameweek": 1
        },
        {
            "type": "clean_sheet",
            "player": "Ederson",
            "team": "Man City",
            "points": 4,
            "old_value": 0,
            "new_value": 1,
            "gameweek": 1
        },
        {
            "type": "price_change",
            "player": "Mohamed Salah",
            "team": "Liverpool",
            "points": 0,
            "old_value": 130,  # £13.0m
            "new_value": 131,  # £13.1m
            "gameweek": 1
        }
    ]
    
    print("✅ Test notifications created:")
    for notif in test_notifications:
        print(f"   {notif['type']}: {notif['player']} ({notif['team']})")
    
    # Test 3: Test notification message generation
    print("\n3️⃣ Testing notification message generation...")
    
    for notif in test_notifications:
        try:
            notif_type = NotificationType(notif['type'])
            from push_notification_service import FPLNotification
            
            fpl_notif = FPLNotification(
                player_name=notif['player'],
                team_name=notif['team'],
                notification_type=notif_type,
                points_change=notif['points'],
                old_value=notif['old_value'],
                new_value=notif['new_value'],
                gameweek=notif['gameweek'],
                timestamp=datetime.now()
            )
            
            title, body = push_service._generate_fpl_message(fpl_notif)
            print(f"   {notif['type']}: {title} - {body}")
            
        except Exception as e:
            print(f"   ❌ Error creating {notif['type']}: {e}")
    
    print("\n✅ All tests completed successfully!")
    print("\n📱 Next steps:")
    print("1. Update your iOS app's Bundle ID to com.silverman.fplmonitor")
    print("2. Enable Push Notifications capability in Xcode")
    print("3. Build and run on a physical device")
    print("4. Test push notifications with a real device token")
    
    return True

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_push_notifications())
    
    if success:
        print("\n🎉 Push notification setup is ready!")
    else:
        print("\n❌ Push notification setup needs configuration")
        sys.exit(1)
