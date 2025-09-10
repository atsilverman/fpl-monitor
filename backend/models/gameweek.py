"""
FPL Gameweek Data Model
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class GameweekInfo(BaseModel):
    """FPL gameweek information model"""
    
    id: int
    name: str
    deadline_time: datetime
    is_current: bool
    is_next: bool
    is_previous: bool
    finished: bool
    is_updated: bool
    highest_score: Optional[int] = None
    most_selected: Optional[int] = None
    most_transferred_in: Optional[int] = None
    most_captained: Optional[int] = None
    most_vice_captained: Optional[int] = None
