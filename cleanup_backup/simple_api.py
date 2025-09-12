#!/usr/bin/env python3
"""
Simple FPL API Server
A minimal API server that serves FPL data from Supabase
"""

import os
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="FPL Monitor API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

def get_supabase_data(endpoint: str, params: dict = None):
    """Get data from Supabase"""
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/{endpoint}",
            headers=HEADERS,
            params=params or {},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "FPL Monitor API", "status": "running"}

@app.get("/fpl/players")
async def get_players(limit: int = 100, fpl_id: int = None):
    """Get FPL players from Supabase"""
    params = {"limit": limit}
    if fpl_id:
        params["fpl_id"] = f"eq.{fpl_id}"
    
    return get_supabase_data("players", params)

@app.get("/fpl/teams")
async def get_teams():
    """Get FPL teams from Supabase"""
    return get_supabase_data("teams")

@app.get("/fpl/fixtures")
async def get_fixtures():
    """Get FPL fixtures from Supabase"""
    return get_supabase_data("fixtures")

@app.get("/fpl/gameweeks")
async def get_gameweeks():
    """Get FPL gameweeks from Supabase"""
    return get_supabase_data("gameweeks")

@app.get("/api/v1/managers/search")
async def search_managers(query: str = "", limit: int = 20):
    """Search for managers by name or ID"""
    if not query:
        return {"managers": []}
    
    try:
        # Check if query is numeric (manager ID)
        if query.isdigit():
            manager_id = int(query)
            # Try to fetch manager directly from FPL API
            try:
                response = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    manager_data = {
                        "id": data.get("id"),
                        "playerName": data.get("player_name"),
                        "playerFirstName": data.get("player_first_name"),
                        "playerLastName": data.get("player_last_name"),
                        "playerRegionName": data.get("player_region_name"),
                        "playerRegionCode": data.get("player_region_code"),
                        "summaryOverallPoints": data.get("summary_overall_points"),
                        "summaryOverallRank": data.get("summary_overall_rank"),
                        "summaryEventPoints": data.get("summary_event_points"),
                        "summaryEventRank": data.get("summary_event_rank"),
                        "joinedTime": data.get("joined_time"),
                        "startedEvent": data.get("started_event"),
                        "favouriteTeam": data.get("favourite_team")
                    }
                    return {"managers": [manager_data]}
            except Exception as e:
                print(f"❌ Error fetching manager {manager_id}: {e}")
        
        # Search by name in database (if we have stored manager data)
        return {"managers": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/managers/{manager_id}")
async def get_manager_details(manager_id: int):
    """Get detailed manager information"""
    try:
        response = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "id": data.get("id"),
                "playerName": data.get("player_name"),
                "playerFirstName": data.get("player_first_name"),
                "playerLastName": data.get("player_last_name"),
                "playerRegionName": data.get("player_region_name"),
                "playerRegionCode": data.get("player_region_code"),
                "summaryOverallPoints": data.get("summary_overall_points"),
                "summaryOverallRank": data.get("summary_overall_rank"),
                "summaryEventPoints": data.get("summary_event_points"),
                "summaryEventRank": data.get("summary_event_rank"),
                "joinedTime": data.get("joined_time"),
                "startedEvent": data.get("started_event"),
                "favouriteTeam": data.get("favourite_team")
            }
        else:
            raise HTTPException(status_code=404, detail="Manager not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/managers/{manager_id}/leagues")
async def get_manager_leagues(manager_id: int):
    """Get manager's leagues"""
    try:
        response = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Get leagues from the manager's data
            leagues = data.get("leagues", {}).get("classic", [])
            return {
                "manager_id": manager_id,
                "leagues": leagues,
                "total_leagues": len(leagues)
            }
        else:
            raise HTTPException(status_code=404, detail="Manager not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Supabase connection
        test_data = get_supabase_data("players", {"limit": 1})
        return {
            "status": "healthy",
            "supabase_connected": True,
            "players_count": len(test_data) if test_data else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "supabase_connected": False,
            "error": str(e)
        }

@app.get("/monitoring/status")
async def monitoring_status():
    """Get monitoring services status"""
    try:
        from backend.services.simple_monitoring_logger import SimpleMonitoringLogger
        logger = SimpleMonitoringLogger("api_check")
        services = logger.get_all_services_status()
        
        return {
            "status": "success",
            "services": services,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
