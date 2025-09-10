"""
FPL Player Data Model
"""

from typing import Optional
from pydantic import BaseModel


class Player(BaseModel):
    """FPL player data model"""
    
    id: int
    first_name: str
    second_name: str
    web_name: str
    team_id: int
    team_name: str
    position: str
    price: float
    total_points: int
    form: float
    selected_by_percent: str
    status: str
    news: Optional[str] = None
    news_added: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Get player's full name"""
        return f"{self.first_name} {self.second_name}"
