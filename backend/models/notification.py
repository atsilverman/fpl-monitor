"""
FPL Notification Data Model
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FPLNotification(BaseModel):
    """FPL notification data model"""
    
    id: int
    player_id: int
    player_name: str
    team_name: str
    notification_type: str
    message: str
    points: Optional[int] = None
    timestamp: datetime
    gameweek: int
    is_read: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
