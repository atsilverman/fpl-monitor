"""
FPL Notification Data Model
Enhanced to match iOS app requirements
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FPLNotification(BaseModel):
    """FPL notification data model - Enhanced for mobile app"""
    
    id: str
    title: str
    body: str
    type: str  # NotificationType enum value
    player: str
    team: str
    team_abbreviation: str
    points: int
    points_change: int
    points_category: str
    total_points: int
    league_ownership: float = 0.0
    overall_ownership: float = 0.0
    is_owned: bool = False
    timestamp: datetime
    is_read: bool = False
    home_team: str
    away_team: str
    fixture: str
    impact: str = "medium"  # low, medium, high, critical
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
