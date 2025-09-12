#!/usr/bin/env python3
"""
Push Notification Service for FPL Monitor
Handles sending push notifications to iOS devices via Apple Push Notification Service (APNs)
Enhanced with FPL-specific notification types and user preferences
"""

import json
import requests
import base64
import jwt
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum

class NotificationType(Enum):
    """FPL notification types"""
    GOAL = "goal"
    ASSIST = "assist"
    CLEAN_SHEET = "clean_sheet"
    BONUS = "bonus"
    RED_CARD = "red_card"
    YELLOW_CARD = "yellow_card"
    PENALTY_SAVED = "penalty_saved"
    PENALTY_MISSED = "penalty_missed"
    OWN_GOAL = "own_goal"
    SAVE = "save"
    GOAL_CONCEDED = "goal_conceded"
    PRICE_CHANGE = "price_change"
    STATUS_CHANGE = "status_change"

@dataclass
class FPLNotification:
    """FPL-specific notification data"""
    player_name: str
    team_name: str
    notification_type: NotificationType
    points_change: int
    old_value: int
    new_value: int
    gameweek: int
    fixture: Optional[str] = None
    timestamp: Optional[datetime] = None

class PushNotificationService:
    def __init__(self, team_id: str, key_id: str, bundle_id: str, private_key_path: str, 
                 use_sandbox: bool = True):
        self.team_id = team_id
        self.key_id = key_id
        self.bundle_id = bundle_id
        self.private_key_path = private_key_path
        self.use_sandbox = use_sandbox
        self.token = None
        self.token_expires = None
        
        # APNs URLs
        self.apns_url = "https://api.sandbox.push.apple.com" if use_sandbox else "https://api.push.apple.com"
        
    def _generate_jwt_token(self) -> str:
        """Generate JWT token for APNs authentication"""
        now = datetime.utcnow()
        
        # Token expires in 1 hour
        payload = {
            'iss': self.team_id,
            'iat': now,
            'exp': now + timedelta(hours=1)
        }
        
        # Read private key
        with open(self.private_key_path, 'r') as f:
            private_key = f.read()
        
        # Generate JWT token
        token = jwt.encode(payload, private_key, algorithm='ES256', headers={
            'kid': self.key_id
        })
        
        return token
    
    def _get_auth_token(self) -> str:
        """Get valid auth token, refreshing if needed"""
        if not self.token or (self.token_expires and datetime.utcnow() >= self.token_expires):
            self.token = self._generate_jwt_token()
            self.token_expires = datetime.utcnow() + timedelta(minutes=55)  # Refresh 5 min early
        
        return self.token
    
    def send_fpl_notification(self, device_token: str, fpl_notification: FPLNotification, 
                             user_preferences: Optional[Dict] = None) -> bool:
        """Send FPL-specific push notification with user preferences"""
        # Check if user wants this type of notification
        if user_preferences and not user_preferences.get(fpl_notification.notification_type.value, True):
            return True  # User has disabled this notification type
        
        # Generate title and body based on notification type
        title, body = self._generate_fpl_message(fpl_notification)
        
        # Create custom data payload
        data = {
            "type": fpl_notification.notification_type.value,
            "player_name": fpl_notification.player_name,
            "team_name": fpl_notification.team_name,
            "points_change": fpl_notification.points_change,
            "gameweek": fpl_notification.gameweek,
            "fixture": fpl_notification.fixture,
            "timestamp": fpl_notification.timestamp.isoformat() if fpl_notification.timestamp else None
        }
        
        return self.send_notification(device_token, title, body, data)
    
    def _generate_fpl_message(self, notification: FPLNotification) -> tuple[str, str]:
        """Generate title and body for FPL notification"""
        emoji_map = {
            NotificationType.GOAL: "⚽",
            NotificationType.ASSIST: "🎯",
            NotificationType.CLEAN_SHEET: "🛡️",
            NotificationType.BONUS: "⭐",
            NotificationType.RED_CARD: "🟥",
            NotificationType.YELLOW_CARD: "🟨",
            NotificationType.PENALTY_SAVED: "🧤",
            NotificationType.PENALTY_MISSED: "❌",
            NotificationType.OWN_GOAL: "😱",
            NotificationType.SAVE: "💪",
            NotificationType.GOAL_CONCEDED: "😔",
            NotificationType.PRICE_CHANGE: "💰",
            NotificationType.STATUS_CHANGE: "📋"
        }
        
        emoji = emoji_map.get(notification.notification_type, "📢")
        points_text = f"+{notification.points_change}" if notification.points_change > 0 else str(notification.points_change)
        
        if notification.notification_type == NotificationType.GOAL:
            title = f"{emoji} {notification.player_name} scored!"
            body = f"{notification.team_name} • {points_text} points • GW{notification.gameweek}"
        elif notification.notification_type == NotificationType.ASSIST:
            title = f"{emoji} {notification.player_name} assist!"
            body = f"{notification.team_name} • {points_text} points • GW{notification.gameweek}"
        elif notification.notification_type == NotificationType.CLEAN_SHEET:
            title = f"{emoji} {notification.player_name} clean sheet!"
            body = f"{notification.team_name} • {points_text} points • GW{notification.gameweek}"
        elif notification.notification_type == NotificationType.BONUS:
            title = f"{emoji} {notification.player_name} bonus points!"
            body = f"{notification.team_name} • {points_text} points • GW{notification.gameweek}"
        elif notification.notification_type == NotificationType.PRICE_CHANGE:
            title = f"{emoji} {notification.player_name} price change"
            body = f"£{notification.old_value/10:.1f}m → £{notification.new_value/10:.1f}m"
        elif notification.notification_type == NotificationType.STATUS_CHANGE:
            title = f"{emoji} {notification.player_name} status update"
            body = f"{notification.team_name} • {notification.new_value}% chance"
        else:
            title = f"{emoji} {notification.player_name} update"
            body = f"{notification.team_name} • {points_text} points"
        
        return title, body

    def send_notification(self, device_token: str, title: str, body: str, 
                         data: Optional[Dict] = None, badge: Optional[int] = None) -> bool:
        """Send push notification to a single device"""
        try:
            # APNs URL
            url = f"{self.apns_url}/3/device/{device_token}"
            
            # Notification payload
            payload = {
                "aps": {
                    "alert": {
                        "title": title,
                        "body": body
                    },
                    "sound": "default",
                    "badge": badge,
                    "category": "FPL_NOTIFICATION"
                }
            }
            
            # Add custom data if provided
            if data:
                payload.update(data)
            
            # Headers
            headers = {
                "authorization": f"bearer {self._get_auth_token()}",
                "apns-topic": self.bundle_id,
                "apns-push-type": "alert",
                "apns-priority": "10",
                "apns-expiration": str(int(time.time()) + 3600)  # 1 hour expiration
            }
            
            # Send notification
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Push notification sent to {device_token[:8]}...")
                return True
            else:
                print(f"❌ Failed to send push notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending push notification: {e}")
            return False
    
    def send_bulk_notifications(self, device_tokens: List[str], title: str, body: str,
                               data: Optional[Dict] = None, badge: Optional[int] = None) -> Dict[str, bool]:
        """Send push notifications to multiple devices"""
        results = {}
        
        for device_token in device_tokens:
            results[device_token] = self.send_notification(device_token, title, body, data, badge)
            # Small delay to avoid rate limiting
            time.sleep(0.01)
        
        return results

# Example usage and configuration
def create_push_service() -> Optional[PushNotificationService]:
    """Create push notification service with configuration from environment"""
    import os
    
    team_id = os.getenv('APNS_TEAM_ID') or os.getenv('APPLE_TEAM_ID')
    key_id = os.getenv('APNS_KEY_ID') or os.getenv('APPLE_KEY_ID')
    bundle_id = os.getenv('APNS_BUNDLE_ID') or os.getenv('APPLE_BUNDLE_ID', 'com.silverman.fplmonitor')
    private_key_path = os.getenv('APNS_PRIVATE_KEY_PATH') or os.getenv('APPLE_PRIVATE_KEY_PATH')
    
    if not all([team_id, key_id, private_key_path]):
        print("Push notification configuration missing. Set APNS_TEAM_ID, APNS_KEY_ID, and APNS_PRIVATE_KEY_PATH")
        return None
    
    # Use sandbox for development, production for App Store
    use_sandbox = os.getenv('ENVIRONMENT', 'development') == 'development'
    
    return PushNotificationService(team_id, key_id, bundle_id, private_key_path, use_sandbox)

def send_fpl_notification_to_device(device_token: str, player_name: str, team_name: str, 
                                  notification_type: str, points_change: int, old_value: int, 
                                  new_value: int, gameweek: int, fixture: str = None) -> bool:
    """Convenience function to send FPL notification to a device"""
    push_service = create_push_service()
    if not push_service:
        return False
    
    # Convert string to enum
    try:
        notif_type = NotificationType(notification_type)
    except ValueError:
        print(f"Invalid notification type: {notification_type}")
        return False
    
    # Create FPL notification
    fpl_notification = FPLNotification(
        player_name=player_name,
        team_name=team_name,
        notification_type=notif_type,
        points_change=points_change,
        old_value=old_value,
        new_value=new_value,
        gameweek=gameweek,
        fixture=fixture,
        timestamp=datetime.now()
    )
    
    return push_service.send_fpl_notification(device_token, fpl_notification)

if __name__ == "__main__":
    # Test push notification service
    push_service = create_push_service()
    
    if push_service:
        # Test notification (replace with actual device token)
        test_token = "YOUR_DEVICE_TOKEN_HERE"
        success = push_service.send_notification(
            device_token=test_token,
            title="FPL Test Notification",
            body="This is a test notification from FPL Monitor!",
            data={"type": "test", "gameweek": 1}
        )
        
        if success:
            print("✅ Test notification sent successfully!")
        else:
            print("❌ Test notification failed!")
    else:
        print("❌ Push service not configured")
