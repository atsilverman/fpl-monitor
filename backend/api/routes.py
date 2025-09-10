"""
FPL Monitor API Routes
Centralized API endpoint definitions
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..services.fpl_monitor_service import FPLMonitorService
from ..models.notification import FPLNotification
from ..models.player import Player
from ..models.gameweek import GameweekInfo

# Create router
router = APIRouter()

# Initialize service
fpl_service = FPLMonitorService()


@router.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fpl-monitor"}


@router.get("/monitoring/status")
async def get_monitoring_status():
    """Get current monitoring status"""
    try:
        status = await fpl_service.get_monitoring_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications", response_model=List[FPLNotification])
async def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get FPL notifications with pagination"""
    try:
        notifications = await fpl_service.get_notifications(limit=limit, offset=offset)
        return notifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/players/search")
async def search_players(query: str = Query(..., min_length=2)):
    """Search for players by name"""
    try:
        players = await fpl_service.search_players(query)
        return {"players": players, "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fpl/current-gameweek")
async def get_current_gameweek():
    """Get current gameweek information"""
    try:
        gameweek = await fpl_service.get_current_gameweek()
        return gameweek
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fpl/teams")
async def get_teams():
    """Get all Premier League teams"""
    try:
        teams = await fpl_service.get_teams()
        return {"teams": teams}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fpl/players")
async def get_players(
    team_id: Optional[int] = Query(None),
    position: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """Get players with optional filtering"""
    try:
        players = await fpl_service.get_players(
            team_id=team_id,
            position=position,
            limit=limit
        )
        return {"players": players}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/device-tokens")
async def register_device_token(device_data: dict):
    """Register device token for push notifications"""
    try:
        device_token = device_data.get("device_token")
        platform = device_data.get("platform", "ios")
        
        # Store device token in database
        await fpl_service.register_device_token(device_token, platform)
        return {"status": "success", "message": "Device token registered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-preferences")
async def get_user_preferences():
    """Get user preferences"""
    try:
        preferences = await fpl_service.get_user_preferences()
        return preferences
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-preferences")
async def save_user_preferences(preferences: dict):
    """Save user preferences"""
    try:
        await fpl_service.save_user_preferences(preferences)
        return {"status": "success", "message": "Preferences saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/events")
async def track_analytics_event(event_data: dict):
    """Track analytics event"""
    try:
        await fpl_service.track_analytics_event(event_data)
        return {"status": "success", "message": "Event tracked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/data")
async def get_analytics_data(time_range: str = "week"):
    """Get analytics data for specified time range"""
    try:
        analytics_data = await fpl_service.get_analytics_data(time_range)
        return analytics_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
