#!/usr/bin/env python3
"""
Analytics Service for FPL Monitor
Tracks user engagement, notification effectiveness, and app performance
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class EventType(Enum):
    """Analytics event types"""
    APP_OPEN = "app_open"
    NOTIFICATION_RECEIVED = "notification_received"
    NOTIFICATION_TAPPED = "notification_tapped"
    NOTIFICATION_DISMISSED = "notification_dismissed"
    PLAYER_SEARCH = "player_search"
    SETTINGS_UPDATED = "settings_updated"
    PUSH_ENABLED = "push_enabled"
    PUSH_DISABLED = "push_disabled"
    ERROR_OCCURRED = "error_occurred"
    API_REQUEST = "api_request"

@dataclass
class AnalyticsEvent:
    """Analytics event data"""
    event_id: str
    user_id: str
    event_type: EventType
    timestamp: datetime
    properties: Dict[str, Any] = None
    session_id: str = None
    app_version: str = None
    platform: str = "ios"
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class NotificationAnalytics:
    """Notification-specific analytics"""
    notification_id: str
    user_id: str
    notification_type: str
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    tapped_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    points_change: int = 0
    player_name: str = ""
    team_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['sent_at'] = self.sent_at.isoformat()
        data['delivered_at'] = self.delivered_at.isoformat() if self.delivered_at else None
        data['tapped_at'] = self.tapped_at.isoformat() if self.tapped_at else None
        data['dismissed_at'] = self.dismissed_at.isoformat() if self.dismissed_at else None
        return data

class AnalyticsService:
    """Service for tracking analytics and user engagement"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def track_event(self, event: AnalyticsEvent) -> bool:
        """Track an analytics event"""
        try:
            # Store in analytics_events table
            event_data = event.to_dict()
            result = self.supabase.table('analytics_events').insert(event_data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error tracking event: {e}")
            return False
    
    async def track_notification_sent(self, notification_analytics: NotificationAnalytics) -> bool:
        """Track notification sent event"""
        try:
            # Store in notification_analytics table
            analytics_data = notification_analytics.to_dict()
            result = self.supabase.table('notification_analytics').insert(analytics_data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error tracking notification sent: {e}")
            return False
    
    async def track_notification_delivered(self, notification_id: str, delivered_at: datetime = None) -> bool:
        """Track notification delivery"""
        try:
            if delivered_at is None:
                delivered_at = datetime.now()
            
            result = self.supabase.table('notification_analytics').update({
                'delivered_at': delivered_at.isoformat()
            }).eq('notification_id', notification_id).execute()
            
            return len(result.data) > 0
        except Exception as e:
            print(f"Error tracking notification delivery: {e}")
            return False
    
    async def track_notification_tapped(self, notification_id: str, tapped_at: datetime = None) -> bool:
        """Track notification tap"""
        try:
            if tapped_at is None:
                tapped_at = datetime.now()
            
            result = self.supabase.table('notification_analytics').update({
                'tapped_at': tapped_at.isoformat()
            }).eq('notification_id', notification_id).execute()
            
            return len(result.data) > 0
        except Exception as e:
            print(f"Error tracking notification tap: {e}")
            return False
    
    async def track_notification_dismissed(self, notification_id: str, dismissed_at: datetime = None) -> bool:
        """Track notification dismissal"""
        try:
            if dismissed_at is None:
                dismissed_at = datetime.now()
            
            result = self.supabase.table('notification_analytics').update({
                'dismissed_at': dismissed_at.isoformat()
            }).eq('notification_id', notification_id).execute()
            
            return len(result.data) > 0
        except Exception as e:
            print(f"Error tracking notification dismissal: {e}")
            return False
    
    async def get_user_engagement_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user engagement statistics"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get user events
            events_result = self.supabase.table('analytics_events').select('*').eq('user_id', user_id).gte('timestamp', start_date.isoformat()).execute()
            
            # Get notification analytics
            notifications_result = self.supabase.table('notification_analytics').select('*').eq('user_id', user_id).gte('sent_at', start_date.isoformat()).execute()
            
            events = events_result.data
            notifications = notifications_result.data
            
            # Calculate engagement metrics
            total_events = len(events)
            app_opens = len([e for e in events if e.get('event_type') == EventType.APP_OPEN.value])
            notifications_received = len([n for n in notifications if n.get('delivered_at')])
            notifications_tapped = len([n for n in notifications if n.get('tapped_at')])
            
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(events, notifications)
            
            return {
                'user_id': user_id,
                'period_days': days,
                'total_events': total_events,
                'app_opens': app_opens,
                'notifications_received': notifications_received,
                'notifications_tapped': notifications_tapped,
                'notification_tap_rate': notifications_tapped / max(notifications_received, 1),
                'engagement_score': engagement_score,
                'most_active_hour': self._get_most_active_hour(events),
                'favorite_notification_type': self._get_favorite_notification_type(notifications)
            }
        except Exception as e:
            print(f"Error getting user engagement stats: {e}")
            return {}
    
    async def get_notification_effectiveness(self, days: int = 30) -> Dict[str, Any]:
        """Get notification effectiveness metrics"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get all notifications in period
            result = self.supabase.table('notification_analytics').select('*').gte('sent_at', start_date.isoformat()).execute()
            notifications = result.data
            
            if not notifications:
                return {}
            
            # Calculate metrics
            total_sent = len(notifications)
            total_delivered = len([n for n in notifications if n.get('delivered_at')])
            total_tapped = len([n for n in notifications if n.get('tapped_at')])
            total_dismissed = len([n for n in notifications if n.get('dismissed_at')])
            
            # Calculate rates
            delivery_rate = total_delivered / total_sent if total_sent > 0 else 0
            tap_rate = total_tapped / total_delivered if total_delivered > 0 else 0
            dismissal_rate = total_dismissed / total_delivered if total_delivered > 0 else 0
            
            # Group by notification type
            type_stats = {}
            for notif in notifications:
                notif_type = notif.get('notification_type', 'unknown')
                if notif_type not in type_stats:
                    type_stats[notif_type] = {'sent': 0, 'delivered': 0, 'tapped': 0}
                
                type_stats[notif_type]['sent'] += 1
                if notif.get('delivered_at'):
                    type_stats[notif_type]['delivered'] += 1
                if notif.get('tapped_at'):
                    type_stats[notif_type]['tapped'] += 1
            
            return {
                'period_days': days,
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_tapped': total_tapped,
                'total_dismissed': total_dismissed,
                'delivery_rate': delivery_rate,
                'tap_rate': tap_rate,
                'dismissal_rate': dismissal_rate,
                'type_breakdown': type_stats
            }
        except Exception as e:
            print(f"Error getting notification effectiveness: {e}")
            return {}
    
    def _calculate_engagement_score(self, events: List[Dict], notifications: List[Dict]) -> float:
        """Calculate user engagement score (0-100)"""
        if not events:
            return 0.0
        
        # Weight different activities
        app_opens = len([e for e in events if e.get('event_type') == EventType.APP_OPEN.value])
        searches = len([e for e in events if e.get('event_type') == EventType.PLAYER_SEARCH.value])
        settings_updates = len([e for e in events if e.get('event_type') == EventType.SETTINGS_UPDATED.value])
        notifications_tapped = len([n for n in notifications if n.get('tapped_at')])
        
        # Calculate score (max 100)
        score = min(100, (app_opens * 2) + (searches * 3) + (settings_updates * 5) + (notifications_tapped * 4))
        return score / 100.0
    
    def _get_most_active_hour(self, events: List[Dict]) -> int:
        """Get the hour when user is most active"""
        if not events:
            return 0
        
        hour_counts = {}
        for event in events:
            try:
                timestamp = datetime.fromisoformat(event.get('timestamp', ''))
                hour = timestamp.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            except:
                continue
        
        return max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 0
    
    def _get_favorite_notification_type(self, notifications: List[Dict]) -> str:
        """Get user's favorite notification type based on taps"""
        if not notifications:
            return "none"
        
        type_taps = {}
        for notif in notifications:
            if notif.get('tapped_at'):
                notif_type = notif.get('notification_type', 'unknown')
                type_taps[notif_type] = type_taps.get(notif_type, 0) + 1
        
        return max(type_taps.items(), key=lambda x: x[1])[0] if type_taps else "none"

# Example usage and testing
if __name__ == "__main__":
    # Test analytics event
    event = AnalyticsEvent(
        event_id="test_event_123",
        user_id="test_user_123",
        event_type=EventType.APP_OPEN,
        properties={"app_version": "1.0.0", "platform": "ios"}
    )
    
    print("Analytics event:")
    print(json.dumps(event.to_dict(), indent=2))
    
    # Test notification analytics
    notif_analytics = NotificationAnalytics(
        notification_id="notif_123",
        user_id="test_user_123",
        notification_type="goal",
        sent_at=datetime.now(),
        points_change=4,
        player_name="Erling Haaland",
        team_name="Man City"
    )
    
    print("\nNotification analytics:")
    print(json.dumps(notif_analytics.to_dict(), indent=2))
