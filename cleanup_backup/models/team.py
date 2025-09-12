"""
FPL Team Data Model
"""

from pydantic import BaseModel


class Team(BaseModel):
    """FPL team data model"""
    
    id: int
    name: str
    short_name: str
    strength: int
    strength_attack_home: int
    strength_attack_away: int
    strength_defence_home: int
    strength_defence_away: int
    team_division: Optional[int] = None
    code: int
    played: int
    win: int
    draw: int
    loss: int
    points: int
    position: int
    form: Optional[str] = None
    pulse_id: int
