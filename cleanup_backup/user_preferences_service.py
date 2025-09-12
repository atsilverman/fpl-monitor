#!/usr/bin/env python3
"""
User Preferences Service for FPL Monitor
Handles user notification preferences, team selections, and personalization
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class NotificationPreference(Enum):
    """Available notification types"""
    GOALS = "goals"
    ASSISTS = "assists"
    CLEAN_SHEETS = "clean_sheets"
    BONUS = "bonus"
    RED_CARDS = "red_cards"
    YELLOW_CARDS = "yellow_cards"
    PENALTY_SAVED = "penalty_saved"
    PENALTY_MISSED = "penalty_missed"
    OWN_GOALS = "own_goals"
    SAVES = "saves"
    GOAL_CONCEDED = "goal_conceded"
    PRICE_CHANGES = "price_changes"
    STATUS_CHANGES = "status_changes"

@dataclass
class UserPreferences:
    """User notification preferences and settings"""
    user_id: str
    fpl_manager_id: Optional[int] = None
    notification_preferences: Dict[str, bool] = None
    owned_players: List[int] = None
    mini_league_ids: List[int] = None
    timezone: str = "America/Los_Angeles"
    push_enabled: bool = True
    email_enabled: bool = False
    notification_frequency: str = "immediate"  # immediate, hourly, daily
    quiet_hours_start: Optional[str] = None  # "22:00"
    quiet_hours_end: Optional[str] = None    # "08:00"
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.notification_preferences is None:
            self.notification_preferences = self._get_default_preferences()
        if self.owned_players is None:
            self.owned_players = []
        if self.mini_league_ids is None:
            self.mini_league_ids = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def _get_default_preferences(self) -> Dict[str, bool]:
        """Get default notification preferences"""
        return {
            NotificationPreference.GOALS.value: True,
            NotificationPreference.ASSISTS.value: True,
            NotificationPreference.CLEAN_SHEETS.value: True,
            NotificationPreference.BONUS.value: True,
            NotificationPreference.RED_CARDS.value: True,
            NotificationPreference.YELLOW_CARDS.value: False,
            NotificationPreference.PENALTY_SAVED.value: True,
            NotificationPreference.PENALTY_MISSED.value: True,
            NotificationPreference.OWN_GOALS.value: True,
            NotificationPreference.SAVES.value: False,
            NotificationPreference.GOAL_CONCEDED.value: False,
            NotificationPreference.PRICE_CHANGES.value: True,
            NotificationPreference.STATUS_CHANGES.value: True,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create from dictionary"""
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and data['updated_at']:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

class UserPreferencesService:
    """Service for managing user preferences"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences by user ID"""
        try:
            result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if result.data:
                user_data = result.data[0]
                return UserPreferences.from_dict({
                    'user_id': user_data['id'],
                    'fpl_manager_id': user_data.get('fpl_manager_id'),
                    'notification_preferences': user_data.get('notification_preferences', {}),
                    'owned_players': user_data.get('owned_players', []),
                    'mini_league_ids': user_data.get('mini_league_ids', []),
                    'timezone': user_data.get('timezone', 'America/Los_Angeles'),
                    'push_enabled': user_data.get('notification_preferences', {}).get('push_enabled', True),
                    'email_enabled': user_data.get('notification_preferences', {}).get('email_enabled', False),
                    'created_at': user_data.get('created_at'),
                    'updated_at': user_data.get('updated_at')
                })
            return None
        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return None
    
    async def update_user_preferences(self, user_id: str, preferences: UserPreferences) -> bool:
        """Update user preferences"""
        try:
            preferences.updated_at = datetime.now()
            
            update_data = {
                'fpl_manager_id': preferences.fpl_manager_id,
                'notification_preferences': preferences.notification_preferences,
                'owned_players': preferences.owned_players,
                'mini_league_ids': preferences.mini_league_ids,
                'timezone': preferences.timezone,
                'updated_at': preferences.updated_at.isoformat()
            }
            
            result = self.supabase.table('users').update(update_data).eq('id', user_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating user preferences: {e}")
            return False
    
    async def create_user_preferences(self, user_id: str, preferences: UserPreferences) -> bool:
        """Create new user preferences"""
        try:
            preferences.user_id = user_id
            preferences.created_at = datetime.now()
            preferences.updated_at = datetime.now()
            
            user_data = {
                'id': user_id,
                'email': f"user_{user_id}@fplmonitor.com",  # Placeholder email
                'fpl_manager_id': preferences.fpl_manager_id,
                'notification_preferences': preferences.notification_preferences,
                'owned_players': preferences.owned_players,
                'mini_league_ids': preferences.mini_league_ids,
                'timezone': preferences.timezone,
                'created_at': preferences.created_at.isoformat(),
                'updated_at': preferences.updated_at.isoformat()
            }
            
            result = self.supabase.table('users').insert(user_data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error creating user preferences: {e}")
            return False
    
    async def should_send_notification(self, user_id: str, notification_type: str) -> bool:
        """Check if user wants to receive this type of notification"""
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return True  # Default to sending if no preferences
            
            # Check if push notifications are enabled
            if not preferences.push_enabled:
                return False
            
            # Check specific notification type preference
            return preferences.notification_preferences.get(notification_type, True)
        except Exception as e:
            print(f"Error checking notification preference: {e}")
            return True  # Default to sending on error
    
    async def get_users_for_notification(self, notification_type: str, player_id: int = None) -> List[str]:
        """Get list of user IDs who should receive this notification"""
        try:
            # Get all users who have this notification type enabled
            result = self.supabase.table('users').select('id, notification_preferences, owned_players').execute()
            
            user_ids = []
            for user_data in result.data:
                user_id = user_data['id']
                preferences = user_data.get('notification_preferences', {})
                owned_players = user_data.get('owned_players', [])
                
                # Check if user wants this notification type
                if not preferences.get(notification_type, True):
                    continue
                
                # Check if user owns this player (if specified)
                if player_id and player_id not in owned_players:
                    continue
                
                user_ids.append(user_id)
            
            return user_ids
        except Exception as e:
            print(f"Error getting users for notification: {e}")
            return []
    
    async def update_owned_players(self, user_id: str, player_ids: List[int]) -> bool:
        """Update user's owned players list"""
        try:
            result = self.supabase.table('users').update({
                'owned_players': player_ids,
                'updated_at': datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            return len(result.data) > 0
        except Exception as e:
            print(f"Error updating owned players: {e}")
            return False
    
    async def get_user_timezone(self, user_id: str) -> str:
        """Get user's timezone"""
        try:
            preferences = await self.get_user_preferences(user_id)
            return preferences.timezone if preferences else "America/Los_Angeles"
        except Exception as e:
            print(f"Error getting user timezone: {e}")
            return "America/Los_Angeles"

# Example usage and testing
if __name__ == "__main__":
    # Test user preferences
    preferences = UserPreferences(
        user_id="test_user_123",
        fpl_manager_id=12345,
        timezone="America/New_York"
    )
    
    print("Default preferences:")
    print(json.dumps(preferences.to_dict(), indent=2))
    
    # Test notification filtering
    print(f"\nShould send goal notification: {preferences.notification_preferences.get('goals', True)}")
    print(f"Should send yellow card notification: {preferences.notification_preferences.get('yellow_cards', True)}")
