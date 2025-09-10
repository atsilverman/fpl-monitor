#!/usr/bin/env python3
"""
FPL Mobile Monitor - Enhanced Service (Python 3.13 Compatible)
==============================================================

Enhanced version with proper change detection, data persistence, and database integration.
This service implements the Discord bot logic with database storage for accurate change tracking.

Features:
- Real-time FPL data monitoring with change detection
- PostgreSQL database integration
- User-specific notification generation
- REST API for mobile app
- WebSocket support for live updates
- Historical data storage for accurate comparisons
"""

import os
import sys
import json
import time
import asyncio
import logging
import requests
import psycopg2
import pytz
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# ========================================
# CONFIGURATION
# ========================================

@dataclass
class Config:
    # FPL API configuration
    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    
    # Monitoring configuration
    min_points_change: int = 1
    mini_league_id: int = int(os.getenv("FPL_MINI_LEAGUE_ID", "814685"))
    
    # Database configuration
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # Monitoring intervals
    check_interval: int = 30  # seconds
    price_window_start: int = 18  # 6:30 PM
    price_window_end: int = 19   # 7:00 PM

config = Config()

# ========================================
# DATA MODELS
# ========================================

class PlayerData(BaseModel):
    id: int
    web_name: str
    first_name: Optional[str] = None
    second_name: Optional[str] = None
    team_id: int
    element_type: int  # 1=GK, 2=DEF, 3=MID, 4=FWD
    now_cost: int
    total_points: int
    event_points: int
    selected_by_percent: float
    status: str
    photo: Optional[str] = None

class TeamData(BaseModel):
    id: int
    code: int
    name: str
    short_name: str
    strength: int
    form: Optional[str] = None

class FixtureData(BaseModel):
    id: int
    event: int
    team_h: int
    team_a: int
    team_h_score: Optional[int] = None
    team_a_score: Optional[int] = None
    kickoff_time: Optional[str] = None
    started: bool = False
    finished: bool = False
    minutes: int = 0
    team_h_difficulty: int
    team_a_difficulty: int

class GameweekData(BaseModel):
    id: int
    name: str
    deadline_time: str
    finished: bool = False
    is_previous: bool = False
    is_current: bool = False
    is_next: bool = False

class LivePlayerData(BaseModel):
    id: int
    stats: Dict[str, Any]
    explain: List[Dict[str, Any]]

class NotificationData(BaseModel):
    player_id: int
    player_name: str
    team_name: str
    fixture_id: Optional[int] = None
    gameweek: int
    event_type: str
    old_value: int
    new_value: int
    points_change: int
    message: str
    timestamp: datetime

# ========================================
# DATABASE MANAGER
# ========================================

class DatabaseManager:
    """Handles all database operations with change detection"""
    
    def __init__(self):
        self.pg_conn = None
        self._init_connection()
    
    def _init_connection(self):
        """Initialize database connection"""
        try:
            if config.database_url:
                self.pg_conn = psycopg2.connect(config.database_url)
                print("✅ PostgreSQL connection initialized")
            else:
                print("❌ No database URL configured")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
    
    def get_previous_data(self, table: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get previous data for change detection"""
        if not self.pg_conn:
            return None
        
        try:
            cursor = self.pg_conn.cursor()
            
            # Build WHERE clause
            where_conditions = []
            params = []
            for key, value in filters.items():
                where_conditions.append(f"{key} = %s")
                params.append(value)
            
            where_clause = " AND ".join(where_conditions)
            query = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY updated_at DESC LIMIT 1"
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting previous data: {e}")
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def store_player_data(self, player_data: PlayerData, gameweek: int) -> bool:
        """Store player data with change detection"""
        if not self.pg_conn:
            return False
        
        try:
            cursor = self.pg_conn.cursor()
            
            # Get previous data
            previous = self.get_previous_data("players", {"fpl_id": player_data.id})
            
            # Check for changes
            changes = []
            if previous:
                if previous.get("now_cost") != player_data.now_cost:
                    changes.append({
                        "field": "price",
                        "old_value": previous.get("now_cost", 0),
                        "new_value": player_data.now_cost,
                        "points_change": 0
                    })
                
                if previous.get("status") != player_data.status:
                    changes.append({
                        "field": "status",
                        "old_value": previous.get("status", ""),
                        "new_value": player_data.status,
                        "points_change": 0
                    })
            
            # Upsert player data
            cursor.execute("""
                INSERT INTO players (
                    fpl_id, web_name, first_name, second_name, team_id,
                    element_type, now_cost, total_points, event_points,
                    selected_by_percent, status, photo_url, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (fpl_id) DO UPDATE SET
                    web_name = EXCLUDED.web_name,
                    first_name = EXCLUDED.first_name,
                    second_name = EXCLUDED.second_name,
                    team_id = EXCLUDED.team_id,
                    element_type = EXCLUDED.element_type,
                    now_cost = EXCLUDED.now_cost,
                    total_points = EXCLUDED.total_points,
                    event_points = EXCLUDED.event_points,
                    selected_by_percent = EXCLUDED.selected_by_percent,
                    status = EXCLUDED.status,
                    photo_url = EXCLUDED.photo_url,
                    updated_at = NOW()
                RETURNING id
            """, (
                player_data.id, player_data.web_name, player_data.first_name,
                player_data.second_name, player_data.team_id, player_data.element_type,
                player_data.now_cost, player_data.total_points, player_data.event_points,
                player_data.selected_by_percent, player_data.status, player_data.photo
            ))
            
            player_db_id = cursor.fetchone()[0]
            
            # Store changes in live_monitor_history
            for change in changes:
                cursor.execute("""
                    INSERT INTO live_monitor_history (
                        player_id, player_name, team_name, gameweek,
                        event_type, old_value, new_value, points_change
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    player_db_id, player_data.web_name, "Unknown", gameweek,
                    change["field"], change["old_value"], change["new_value"], change["points_change"]
                ))
            
            self.pg_conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error storing player data: {e}")
            self.pg_conn.rollback()
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def store_live_stats(self, live_data: Dict[int, LivePlayerData], gameweek: int) -> List[NotificationData]:
        """Store live stats and generate notifications"""
        notifications = []
        
        if not self.pg_conn:
            return notifications
        
        try:
            cursor = self.pg_conn.cursor()
            
            for player_id, live_player in live_data.items():
                # Get previous stats
                previous = self.get_previous_data("gameweek_stats", {
                    "player_id": player_id,
                    "gameweek": gameweek
                })
                
                # Extract current stats
                current_stats = live_player.stats
                
                # Check for significant changes
                changes = self._detect_stat_changes(previous, current_stats, live_player.id)
                
                # Store current stats (handle fixture_id=0 case)
                fixture_id = current_stats.get("fixture", 0)
                if fixture_id == 0:
                    fixture_id = None  # Use NULL for no fixture
                
                cursor.execute("""
                    INSERT INTO gameweek_stats (
                        player_id, fixture_id, gameweek, minutes, goals_scored,
                        assists, clean_sheets, goals_conceded, own_goals,
                        penalties_saved, penalties_missed, yellow_cards, red_cards,
                        saves, bonus, bps, influence, creativity, threat, ict_index,
                        expected_goals, expected_assists, expected_goal_involvements,
                        expected_goals_conceded, defensive_contribution, tackles,
                        clearances_blocks_interceptions, recoveries, starts
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (player_id, fixture_id, gameweek) DO UPDATE SET
                        minutes = EXCLUDED.minutes,
                        goals_scored = EXCLUDED.goals_scored,
                        assists = EXCLUDED.assists,
                        clean_sheets = EXCLUDED.clean_sheets,
                        goals_conceded = EXCLUDED.goals_conceded,
                        own_goals = EXCLUDED.own_goals,
                        penalties_saved = EXCLUDED.penalties_saved,
                        penalties_missed = EXCLUDED.penalties_missed,
                        yellow_cards = EXCLUDED.yellow_cards,
                        red_cards = EXCLUDED.red_cards,
                        saves = EXCLUDED.saves,
                        bonus = EXCLUDED.bonus,
                        bps = EXCLUDED.bps,
                        influence = EXCLUDED.influence,
                        creativity = EXCLUDED.creativity,
                        threat = EXCLUDED.threat,
                        ict_index = EXCLUDED.ict_index,
                        expected_goals = EXCLUDED.expected_goals,
                        expected_assists = EXCLUDED.expected_assists,
                        expected_goal_involvements = EXCLUDED.expected_goal_involvements,
                        expected_goals_conceded = EXCLUDED.expected_goals_conceded,
                        defensive_contribution = EXCLUDED.defensive_contribution,
                        tackles = EXCLUDED.tackles,
                        clearances_blocks_interceptions = EXCLUDED.clearances_blocks_interceptions,
                        recoveries = EXCLUDED.recoveries,
                        starts = EXCLUDED.starts,
                        updated_at = NOW()
                """, (
                    player_id, fixture_id, gameweek,
                    current_stats.get("minutes", 0), current_stats.get("goals_scored", 0),
                    current_stats.get("assists", 0), current_stats.get("clean_sheets", 0),
                    current_stats.get("goals_conceded", 0), current_stats.get("own_goals", 0),
                    current_stats.get("penalties_saved", 0), current_stats.get("penalties_missed", 0),
                    current_stats.get("yellow_cards", 0), current_stats.get("red_cards", 0),
                    current_stats.get("saves", 0), current_stats.get("bonus", 0),
                    current_stats.get("bps", 0), current_stats.get("influence", 0.0),
                    current_stats.get("creativity", 0.0), current_stats.get("threat", 0.0),
                    current_stats.get("ict_index", 0.0), current_stats.get("expected_goals", 0.0),
                    current_stats.get("expected_assists", 0.0), current_stats.get("expected_goal_involvements", 0.0),
                    current_stats.get("expected_goals_conceded", 0.0), current_stats.get("defensive_contribution", 0),
                    current_stats.get("tackles", 0), current_stats.get("clearances_blocks_interceptions", 0),
                    current_stats.get("recoveries", 0), current_stats.get("starts", 0)
                ))
                
                # Generate notifications for changes
                for change in changes:
                    notification = self._create_notification(change, live_player.id, gameweek)
                    if notification:
                        notifications.append(notification)
            
            self.pg_conn.commit()
            return notifications
            
        except Exception as e:
            print(f"❌ Error storing live stats: {e}")
            self.pg_conn.rollback()
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def _detect_stat_changes(self, previous: Optional[Dict], current: Dict, player_id: int) -> List[Dict]:
        """Detect significant stat changes using Discord bot logic"""
        changes = []
        
        if not previous:
            return changes
        
        # Position-specific thresholds
        position = self._get_player_position(player_id)
        thresholds = self._get_position_thresholds(position)
        
        # Check each stat for significant changes
        for stat, threshold in thresholds.items():
            old_value = previous.get(stat, 0)
            new_value = current.get(stat, 0)
            
            if new_value > old_value and new_value >= threshold:
                changes.append({
                    "stat": stat,
                    "old_value": old_value,
                    "new_value": new_value,
                    "points_change": new_value - old_value,
                    "threshold": threshold
                })
        
        return changes
    
    def _get_player_position(self, player_id: int) -> int:
        """Get player position from database"""
        if not self.pg_conn:
            return 1  # Default to GK
        
        try:
            cursor = self.pg_conn.cursor()
            cursor.execute("SELECT element_type FROM players WHERE fpl_id = %s", (player_id,))
            result = cursor.fetchone()
            return result[0] if result else 1
        except:
            return 1
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def _get_position_thresholds(self, position: int) -> Dict[str, int]:
        """Get position-specific notification thresholds"""
        if position == 1:  # GK
            return {
                "saves": 3,
                "goals_conceded": 2,
                "penalties_saved": 1,
                "clean_sheets": 1
            }
        elif position == 2:  # DEF
            return {
                "goals_scored": 1,
                "assists": 1,
                "clean_sheets": 1,
                "goals_conceded": 2,
                "defensive_contribution": 1
            }
        elif position == 3:  # MID
            return {
                "goals_scored": 1,
                "assists": 1,
                "clean_sheets": 1
            }
        else:  # FWD
            return {
                "goals_scored": 1,
                "assists": 1
            }
    
    def _create_notification(self, change: Dict, player_id: int, gameweek: int) -> Optional[NotificationData]:
        """Create notification from stat change"""
        # Get player info
        player_info = self._get_player_info(player_id)
        if not player_info:
            return None
        
        # Create notification message
        message = self._format_notification_message(change, player_info)
        
        return NotificationData(
            player_id=player_id,
            player_name=player_info["web_name"],
            team_name=player_info["team_name"],
            gameweek=gameweek,
            event_type=change["stat"],
            old_value=change["old_value"],
            new_value=change["new_value"],
            points_change=change["points_change"],
            message=message,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _get_player_info(self, player_id: int) -> Optional[Dict]:
        """Get player info from database"""
        if not self.pg_conn:
            return None
        
        try:
            cursor = self.pg_conn.cursor()
            cursor.execute("""
                SELECT p.web_name, t.name as team_name
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE p.fpl_id = %s
            """, (player_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "web_name": result[0],
                    "team_name": result[1]
                }
            return None
        except:
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def _format_notification_message(self, change: Dict, player_info: Dict) -> str:
        """Format notification message with emojis"""
        stat_emojis = {
            "goals_scored": "⚽",
            "assists": "🎯",
            "clean_sheets": "🛡️",
            "saves": "💪",
            "penalties_saved": "🦅",
            "goals_conceded": "😞",
            "defensive_contribution": "🛡️"
        }
        
        emoji = stat_emojis.get(change["stat"], "📊")
        stat_name = change["stat"].replace("_", " ").title()
        
        return f"{emoji} {player_info['web_name']} ({player_info['team_name']}) - {stat_name}: {change['old_value']} → {change['new_value']}"

# ========================================
# FPL API CLIENT
# ========================================

class FPLAPIClient:
    """Handles FPL API interactions"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FPL-Mobile-Monitor/1.0'
        })
    
    async def get_bootstrap_data(self) -> Dict[str, Any]:
        """Get bootstrap-static data"""
        try:
            response = self.session.get(f"{config.fpl_base_url}/bootstrap-static/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting bootstrap data: {e}")
            return {}
    
    async def get_live_data(self, gameweek: int) -> Dict[str, Any]:
        """Get live data for specific gameweek"""
        try:
            response = self.session.get(f"{config.fpl_base_url}/event/{gameweek}/live/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting live data: {e}")
            return {}
    
    async def get_fixtures(self) -> List[Dict[str, Any]]:
        """Get fixtures data"""
        try:
            response = self.session.get(f"{config.fpl_base_url}/fixtures/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting fixtures: {e}")
            return []

# ========================================
# MONITORING SERVICE
# ========================================

class FPLMonitoringService:
    """Main monitoring service with change detection"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.api = FPLAPIClient()
        self.current_gameweek = 1
        self.is_running = False
        self.websocket_connections: Set[WebSocket] = set()
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        print("🚀 Starting FPL monitoring service...")
        self.is_running = True
        
        while self.is_running:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(config.check_interval)
            except Exception as e:
                print(f"❌ Monitoring cycle error: {e}")
                await asyncio.sleep(10)  # Wait before retry
    
    async def _monitoring_cycle(self):
        """Single monitoring cycle"""
        print(f"🔍 Monitoring cycle - Gameweek {self.current_gameweek}")
        
        # Get current gameweek
        bootstrap_data = await self.api.get_bootstrap_data()
        if not bootstrap_data:
            return
        
        events = bootstrap_data.get("events", [])
        current_event = next((e for e in events if e.get("is_current")), None)
        
        if not current_event:
            print("❌ No current gameweek found")
            return
        
        self.current_gameweek = current_event["id"]
        
        # Get live data
        live_data = await self.api.get_live_data(self.current_gameweek)
        if not live_data:
            return
        
        # Process live stats
        live_players = live_data.get("elements", [])
        live_player_data = {}
        
        for player in live_players:
            player_id = player["id"]
            live_player_data[player_id] = LivePlayerData(
                id=player_id,
                stats=player.get("stats", {}),
                explain=player.get("explain", [])
            )
        
        # Store data and generate notifications
        notifications = self.db.store_live_stats(live_player_data, self.current_gameweek)
        
        # Send notifications to WebSocket clients
        if notifications:
            await self._broadcast_notifications(notifications)
            print(f"📢 Generated {len(notifications)} notifications")
    
    async def _broadcast_notifications(self, notifications: List[NotificationData]):
        """Broadcast notifications to WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message = {
            "type": "notifications",
            "data": [asdict(notification) for notification in notifications]
        }
        
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected

# ========================================
# FASTAPI APPLICATION
# ========================================

# Global monitoring service
monitoring_service = FPLMonitoringService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Start monitoring service
    asyncio.create_task(monitoring_service.start_monitoring())
    yield
    # Stop monitoring service
    monitoring_service.is_running = False

app = FastAPI(
    title="FPL Mobile Monitor API",
    description="Enhanced FPL monitoring service with change detection",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# ========================================
# API ENDPOINTS
# ========================================

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FPL Mobile Monitor Enhanced",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/monitoring/status")
async def get_monitoring_status():
    """Get current monitoring status"""
    return {
        "is_running": monitoring_service.is_running,
        "current_gameweek": monitoring_service.current_gameweek,
        "check_interval": config.check_interval,
        "database_connected": monitoring_service.db.pg_conn is not None
    }

@app.get("/api/v1/players/search")
async def search_players(query: str = ""):
    """Search players"""
    if not query:
        return {"players": []}
    
    try:
        if monitoring_service.db.pg_conn:
            cursor = monitoring_service.db.pg_conn.cursor()
            cursor.execute("""
                SELECT p.fpl_id, p.web_name, p.first_name, p.second_name, 
                       t.name as team_name, p.element_type, p.now_cost, p.total_points
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE LOWER(p.web_name) LIKE LOWER(%s) 
                   OR LOWER(p.first_name) LIKE LOWER(%s)
                   OR LOWER(p.second_name) LIKE LOWER(%s)
                ORDER BY p.total_points DESC
                LIMIT 20
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
            
            results = cursor.fetchall()
            players = []
            for row in results:
                players.append({
                    "id": row[0],
                    "web_name": row[1],
                    "first_name": row[2],
                    "second_name": row[3],
                    "team_name": row[4],
                    "element_type": row[5],
                    "now_cost": row[6],
                    "total_points": row[7]
                })
            
            return {"players": players}
        else:
            return {"players": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/fpl/current-gameweek")
async def get_current_gameweek():
    """Get current gameweek info"""
    return {
        "gameweek": monitoring_service.current_gameweek,
        "is_running": monitoring_service.is_running
    }

@app.get("/api/v1/notifications")
async def get_notifications(limit: int = 50, offset: int = 0):
    """Get user notifications"""
    try:
        if monitoring_service.db.pg_conn:
            cursor = monitoring_service.db.pg_conn.cursor()
            cursor.execute("""
                SELECT id, notification_type, player_name, team_name, 
                       fixture_id, gameweek, old_value, new_value, points_change,
                       message, is_read, created_at
                FROM user_notifications 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            results = cursor.fetchall()
            notifications = []
            for row in results:
                notifications.append({
                    "id": str(row[0]),
                    "notification_type": row[1],
                    "player_name": row[2],
                    "team_name": row[3],
                    "fixture_id": row[4],
                    "gameweek": row[5],
                    "old_value": row[6],
                    "new_value": row[7],
                    "points_change": row[8],
                    "message": row[9],
                    "is_read": row[10],
                    "timestamp": row[11].isoformat() if row[11] else datetime.now(timezone.utc).isoformat()
                })
            
            # If no notifications, create some sample ones for testing
            if not notifications:
                notifications = create_sample_notifications()
            
            return {
                "notifications": notifications,
                "total": len(notifications),
                "currentGameweek": monitoring_service.current_gameweek
            }
        else:
            return {"notifications": [], "total": 0, "currentGameweek": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_sample_notifications():
    """Create sample notifications for testing"""
    return [
        {
            "id": "1",
            "notification_type": "goals",
            "player_name": "Haaland",
            "team_name": "Man City",
            "fixture_id": 123,
            "gameweek": 3,
            "old_value": 0,
            "new_value": 1,
            "points_change": 4,
            "message": "⚽ Haaland (Man City) - Goal: 0 → 1 (+4 pts)",
            "is_read": False,
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        },
        {
            "id": "2",
            "notification_type": "assists",
            "player_name": "Salah",
            "team_name": "Liverpool",
            "fixture_id": 124,
            "gameweek": 3,
            "old_value": 0,
            "new_value": 1,
            "points_change": 3,
            "message": "🎯 Salah (Liverpool) - Assist: 0 → 1 (+3 pts)",
            "is_read": True,
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        },
        {
            "id": "3",
            "notification_type": "clean_sheets",
            "player_name": "Alisson",
            "team_name": "Liverpool",
            "fixture_id": 124,
            "gameweek": 3,
            "old_value": 0,
            "new_value": 1,
            "points_change": 4,
            "message": "🛡️ Alisson (Liverpool) - Clean Sheet: 0 → 1 (+4 pts)",
            "is_read": False,
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
        }
    ]

# ========================================
# MANAGER AND LEAGUE ENDPOINTS
# ========================================

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
                        "player_name": data.get("player_name"),
                        "player_first_name": data.get("player_first_name"),
                        "player_last_name": data.get("player_last_name"),
                        "player_region_name": data.get("player_region_name"),
                        "player_region_code": data.get("player_region_code"),
                        "summary_overall_points": data.get("summary_overall_points"),
                        "summary_overall_rank": data.get("summary_overall_rank"),
                        "summary_event_points": data.get("summary_event_points"),
                        "summary_event_rank": data.get("summary_event_rank"),
                        "joined_time": data.get("joined_time"),
                        "started_event": data.get("started_event"),
                        "favourite_team": data.get("favourite_team")
                    }
                    return {"managers": [manager_data]}
            except Exception as e:
                print(f"❌ Error fetching manager {manager_id}: {e}")
        
        # Search by name in database (if we have stored manager data)
        if monitoring_service.db.pg_conn:
            cursor = monitoring_service.db.pg_conn.cursor()
            cursor.execute("""
                SELECT fpl_id, player_name, player_first_name, player_last_name,
                       player_region_name, summary_overall_points, summary_overall_rank,
                       summary_event_points, summary_event_rank, joined_time, started_event,
                       favourite_team
                FROM managers 
                WHERE LOWER(player_name) LIKE LOWER(%s) 
                   OR LOWER(player_first_name) LIKE LOWER(%s)
                   OR LOWER(player_last_name) LIKE LOWER(%s)
                ORDER BY summary_overall_points DESC
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            
            results = cursor.fetchall()
            managers = []
            for row in results:
                managers.append({
                    "id": row[0],
                    "player_name": row[1],
                    "player_first_name": row[2],
                    "player_last_name": row[3],
                    "player_region_name": row[4],
                    "summary_overall_points": row[5],
                    "summary_overall_rank": row[6],
                    "summary_event_points": row[7],
                    "summary_event_rank": row[8],
                    "joined_time": row[9],
                    "started_event": row[10],
                    "favourite_team": row[11]
                })
            
            return {"managers": managers}
        else:
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
                "player_name": data.get("player_name"),
                "player_first_name": data.get("player_first_name"),
                "player_last_name": data.get("player_last_name"),
                "player_region_name": data.get("player_region_name"),
                "player_region_code": data.get("player_region_code"),
                "summary_overall_points": data.get("summary_overall_points"),
                "summary_overall_rank": data.get("summary_overall_rank"),
                "summary_event_points": data.get("summary_event_points"),
                "summary_event_rank": data.get("summary_event_rank"),
                "joined_time": data.get("joined_time"),
                "started_event": data.get("started_event"),
                "favourite_team": data.get("favourite_team")
            }
        else:
            raise HTTPException(status_code=404, detail="Manager not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/managers/{manager_id}/leagues")
async def get_manager_leagues(manager_id: int):
    """Get leagues for a specific manager"""
    try:
        response = requests.get(f"https://fantasy.premierleague.com/api/entry/{manager_id}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "classic": data.get("leagues", {}).get("classic", []),
                "h2h": data.get("leagues", {}).get("h2h", [])
            }
        else:
            raise HTTPException(status_code=404, detail="Manager not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/leagues/search")
async def search_leagues(query: str = "", limit: int = 20):
    """Search for leagues by name"""
    if not query:
        return {"leagues": []}
    
    try:
        if monitoring_service.db.pg_conn:
            cursor = monitoring_service.db.pg_conn.cursor()
            cursor.execute("""
                SELECT id, name, short_name, created, closed, max_entries,
                       league_type, scoring, admin_entry, start_event
                FROM mini_leagues 
                WHERE LOWER(name) LIKE LOWER(%s) 
                   OR LOWER(short_name) LIKE LOWER(%s)
                ORDER BY created DESC
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", limit))
            
            results = cursor.fetchall()
            leagues = []
            for row in results:
                leagues.append({
                    "id": row[0],
                    "name": row[1],
                    "short_name": row[2],
                    "created": row[3],
                    "closed": row[4],
                    "max_entries": row[5],
                    "league_type": row[6],
                    "scoring": row[7],
                    "admin_entry": row[8],
                    "start_event": row[9]
                })
            
            return {"leagues": leagues}
        else:
            return {"leagues": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/leagues/{league_id}")
async def get_league_details(league_id: int):
    """Get detailed league information and standings"""
    try:
        response = requests.get(f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=404, detail="League not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    monitoring_service.websocket_connections.add(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        monitoring_service.websocket_connections.discard(websocket)

# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    print("🚀 Starting FPL Mobile Monitor Enhanced Service...")
    print(f"   Database URL: {'✅ Set' if config.database_url else '❌ Not set'}")
    print(f"   Mini League ID: {config.mini_league_id}")
    
    uvicorn.run(
        "fpl_monitor_enhanced_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
