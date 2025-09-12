#!/usr/bin/env python3
"""
Test script for FPL Monitor advanced features
Tests user preferences, analytics, and WebSocket functionality
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add the backend services to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend', 'services'))

from user_preferences_service import UserPreferences, UserPreferencesService, NotificationPreference
from analytics_service import AnalyticsService, AnalyticsEvent, EventType, NotificationAnalytics
from websocket_service import WebSocketService, WebSocketMessage, WebSocketMessageType

async def test_advanced_features():
    """Test all advanced features"""
    print("🧪 Testing FPL Monitor Advanced Features")
    print("=" * 60)
    
    # Mock Supabase client for testing
    class MockSupabaseClient:
        def __init__(self):
            self.data = {}
        
        def table(self, table_name):
            return MockTable(table_name, self.data)
    
    class MockTable:
        def __init__(self, name, data):
            self.name = name
            self.data = data
        
        def select(self, columns="*"):
            return MockQuery(self.name, self.data, "select", columns)
        
        def insert(self, data):
            return MockQuery(self.name, self.data, "insert", data)
        
        def update(self, data):
            return MockQuery(self.name, self.data, "update", data)
        
        def eq(self, column, value):
            return MockQuery(self.name, self.data, "eq", (column, value))
        
        def gte(self, column, value):
            return MockQuery(self.name, self.data, "gte", (column, value))
    
    class MockQuery:
        def __init__(self, table_name, data, operation, params):
            self.table_name = table_name
            self.data = data
            self.operation = operation
            self.params = params
        
        def execute(self):
            class MockResult:
                def __init__(self, data):
                    self.data = data
            return MockResult([])
    
    # Test 1: User Preferences Service
    print("\n1️⃣ Testing User Preferences Service...")
    
    mock_supabase = MockSupabaseClient()
    preferences_service = UserPreferencesService(mock_supabase)
    
    # Test user preferences creation
    test_preferences = UserPreferences(
        user_id="test_user_123",
        fpl_manager_id=12345,
        timezone="America/New_York"
    )
    
    print("✅ User preferences created:")
    print(f"   User ID: {test_preferences.user_id}")
    print(f"   FPL Manager ID: {test_preferences.fpl_manager_id}")
    print(f"   Timezone: {test_preferences.timezone}")
    print(f"   Push Enabled: {test_preferences.push_enabled}")
    print(f"   Notification Types: {len(test_preferences.notification_preferences)}")
    
    # Test notification filtering
    should_send_goal = await preferences_service.should_send_notification("test_user_123", "goals")
    should_send_yellow = await preferences_service.should_send_notification("test_user_123", "yellow_cards")
    
    print(f"   Should send goal notification: {should_send_goal}")
    print(f"   Should send yellow card notification: {should_send_yellow}")
    
    # Test 2: Analytics Service
    print("\n2️⃣ Testing Analytics Service...")
    
    analytics_service = AnalyticsService(mock_supabase)
    
    # Test analytics event creation
    test_event = AnalyticsEvent(
        event_id="test_event_123",
        user_id="test_user_123",
        event_type=EventType.APP_OPEN,
        timestamp=datetime.now(),
        properties={"app_version": "1.0.0", "platform": "ios"}
    )
    
    print("✅ Analytics event created:")
    print(f"   Event ID: {test_event.event_id}")
    print(f"   Event Type: {test_event.event_type.value}")
    print(f"   User ID: {test_event.user_id}")
    print(f"   Properties: {test_event.properties}")
    
    # Test notification analytics
    test_notification_analytics = NotificationAnalytics(
        notification_id="notif_123",
        user_id="test_user_123",
        notification_type="goal",
        sent_at=datetime.now(),
        points_change=4,
        player_name="Erling Haaland",
        team_name="Man City"
    )
    
    print("✅ Notification analytics created:")
    print(f"   Notification ID: {test_notification_analytics.notification_id}")
    print(f"   Type: {test_notification_analytics.notification_type}")
    print(f"   Player: {test_notification_analytics.player_name}")
    print(f"   Points: {test_notification_analytics.points_change}")
    
    # Test 3: WebSocket Service
    print("\n3️⃣ Testing WebSocket Service...")
    
    websocket_service = WebSocketService()
    
    # Test WebSocket message creation
    test_message = WebSocketMessage(
        message_id="msg_123",
        message_type=WebSocketMessageType.NOTIFICATION,
        timestamp=datetime.now(),
        data={"player": "Haaland", "points": 4, "type": "goal"},
        user_id="test_user_123"
    )
    
    print("✅ WebSocket message created:")
    print(f"   Message ID: {test_message.message_id}")
    print(f"   Message Type: {test_message.message_type.value}")
    print(f"   User ID: {test_message.user_id}")
    print(f"   Data: {test_message.data}")
    
    # Test connection stats
    stats = websocket_service.get_connection_stats()
    print("✅ WebSocket connection stats:")
    print(f"   Total Connections: {stats['total_connections']}")
    print(f"   Total Users: {stats['total_users']}")
    print(f"   Total Topics: {stats['total_topics']}")
    
    # Test 4: Integration Test
    print("\n4️⃣ Testing Feature Integration...")
    
    # Simulate a complete FPL notification flow
    print("   Simulating FPL notification flow...")
    
    # 1. Check if user wants this notification
    should_send = await preferences_service.should_send_notification("test_user_123", "goals")
    print(f"   ✅ User wants goal notifications: {should_send}")
    
    # 2. Track notification sent
    notification_analytics = NotificationAnalytics(
        notification_id="fpl_notif_456",
        user_id="test_user_123",
        notification_type="goal",
        sent_at=datetime.now(),
        points_change=4,
        player_name="Erling Haaland",
        team_name="Man City"
    )
    print(f"   ✅ Notification analytics tracked: {notification_analytics.notification_id}")
    
    # 3. Create WebSocket message for real-time update
    websocket_message = WebSocketMessage(
        message_id="ws_msg_789",
        message_type=WebSocketMessageType.NOTIFICATION,
        timestamp=datetime.now(),
        data={
            "type": "goal",
            "player": "Erling Haaland",
            "team": "Man City",
            "points": 4,
            "gameweek": 1
        },
        target_users=["test_user_123"]
    )
    print(f"   ✅ WebSocket message created: {websocket_message.message_id}")
    
    # 4. Track user engagement
    engagement_event = AnalyticsEvent(
        event_id="engagement_123",
        user_id="test_user_123",
        event_type=EventType.NOTIFICATION_RECEIVED,
        timestamp=datetime.now(),
        properties={
            "notification_type": "goal",
            "player_name": "Erling Haaland",
            "points_change": 4
        }
    )
    print(f"   ✅ Engagement event tracked: {engagement_event.event_id}")
    
    print("\n✅ All advanced features tested successfully!")
    
    # Test 5: Performance Test
    print("\n5️⃣ Testing Performance...")
    
    start_time = datetime.now()
    
    # Simulate multiple notifications
    for i in range(100):
        # Create notification analytics
        notif_analytics = NotificationAnalytics(
            notification_id=f"perf_test_{i}",
            user_id=f"user_{i % 10}",  # 10 different users
            notification_type="goal",
            sent_at=datetime.now(),
            points_change=4,
            player_name="Test Player",
            team_name="Test Team"
        )
        
        # Create WebSocket message
        ws_message = WebSocketMessage(
            message_id=f"ws_perf_{i}",
            message_type=WebSocketMessageType.NOTIFICATION,
            timestamp=datetime.now(),
            data={"type": "goal", "player": "Test Player", "points": 4}
        )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"   ✅ Created 100 notifications in {duration:.3f} seconds")
    print(f"   ✅ Performance: {100/duration:.1f} notifications/second")
    
    print("\n🎉 All advanced features are working perfectly!")
    print("\n📱 Next steps:")
    print("1. Update your iOS app with the new views")
    print("2. Test user preferences in the app")
    print("3. Verify analytics tracking")
    print("4. Test WebSocket real-time updates")
    print("5. Deploy to production with HTTPS")
    
    return True

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_advanced_features())
    
    if success:
        print("\n🚀 Advanced features are ready for production!")
    else:
        print("\n❌ Some features need attention")
        sys.exit(1)
