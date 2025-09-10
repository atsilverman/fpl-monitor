#!/usr/bin/env python3
"""
FPL MOBILE MONITORING SERVICE
============================

Scalable version of the FPL monitoring system for mobile app backend.
Deployed to DigitalOcean App Platform with Supabase integration.

Features:
- Real-time FPL data monitoring
- User-specific notification generation
- REST API for mobile app
- WebSocket support for live updates
- Supabase integration
- Scalable architecture

Usage:
    python fpl_monitor_service.py
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
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
from collections.abc import MutableSet
from dataclasses import dataclass
from contextlib import asynccontextmanager

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# Supabase client
from supabase import create_client, Client

# ========================================
# CONFIGURATION
# ========================================

@dataclass
class Config:
    # Supabase configuration
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    
    # FPL API configuration
    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    
    # Monitoring configuration
    min_points_change: int = 1
    mini_league_id: int = int(os.getenv("FPL_MINI_LEAGUE_ID", "814685"))
    
    # Database configuration
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # Push notification configuration
    apns_key_id: str = os.getenv("APNS_KEY_ID", "")
    apns_team_id: str = os.getenv("APNS_TEAM_ID", "")
    apns_bundle_id: str = os.getenv("APNS_BUNDLE_ID", "")

config = Config()

# ========================================
# DATA MODELS
# ========================================

class NotificationRequest(BaseModel):
    user_id: str
    notification_type: str
    player_id: int
    player_name: str
    team_name: str
    fixture_id: Optional[int] = None
    gameweek: int
    old_value: int
    new_value: int
    points_change: int
    message: str

class UserPreferences(BaseModel):
    fpl_manager_id: Optional[int] = None
    notification_preferences: Dict[str, bool]
    owned_players: List[int]
    mini_league_ids: List[int]
    timezone: str = "America/Los_Angeles"

# ========================================
# FPL MONITORING SERVICE
# ========================================

class FPLMonitoringService:
    def __init__(self):
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)
        self.db_conn = None
        self.monitoring_active = False
        self.websocket_connections: Set[WebSocket] = set()
        
        # FPL scoring multipliers
        self.goal_multipliers = {1: 10, 2: 6, 3: 5, 4: 4}  # GK, DEF, MID, FWD
        self.cs_multipliers = {1: 4, 2: 4, 3: 1, 4: 0}     # GK, DEF, MID, FWD
        
        # Team emoji mapping
        self.team_emojis = {
            'Arsenal': '🔴', 'Aston Villa': '🟣', 'Bournemouth': '🔴',
            'Brentford': '🔴⚫', 'Brighton': '🔵⚪', 'Burnley': '🟤',
            'Chelsea': '🔵', 'Crystal Palace': '🔴🔵', 'Everton': '🔵',
            'Fulham': '⚪⚫', 'Leeds': '⚪🟡', 'Liverpool': '🔴',
            'Man City': '🔵', 'Man Utd': '🔴', 'Newcastle': '⚫⚪',
            'Nott\'m Forest': '🔴', 'Sunderland': '🔴⚪', 'Spurs': '⚪',
            'West Ham': '🔴⚪', 'Wolves': '🟡⚫'
        }
        
        # Notification categories
        self.notification_categories = {
            'goals': {'emoji': '⚽', 'points_impact': True},
            'assists': {'emoji': '🎯', 'points_impact': True},
            'clean_sheets': {'emoji': '🛡️', 'points_impact': True},
            'bonus': {'emoji': '⭐', 'points_impact': True},
            'red_cards': {'emoji': '🟥', 'points_impact': True},
            'yellow_cards': {'emoji': '🟨', 'points_impact': True},
            'penalties_saved': {'emoji': '🧤', 'points_impact': True},
            'penalties_missed': {'emoji': '❌', 'points_impact': True},
            'own_goals': {'emoji': '😱', 'points_impact': True},
            'saves': {'emoji': '💾', 'points_impact': True},
            'goals_conceded': {'emoji': '🥅', 'points_impact': True},
            'defensive_contribution': {'emoji': '🔄', 'points_impact': True},
            'price_changes': {'emoji': '💰', 'points_impact': False},
            'status_changes': {'emoji': '🏥', 'points_impact': False}
        }
        
        # Monitoring configuration
        self.monitoring_config = {
            'live_performance': {
                'refresh_seconds': 60,
                'active_during': ['live_matches', 'upcoming_matches'],
                'priority': 'high'
            },
            'status_changes': {
                'refresh_seconds': 3600,
                'active_during': ['always'],
                'priority': 'medium'
            },
            'price_changes': {
                'refresh_seconds': 300,
                'active_during': ['price_update_windows'],
                'priority': 'high'
            }
        }
        
        self.setup_logging()
        self.connect_database()

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('fpl_monitor.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def connect_database(self):
        """Connect to Supabase database"""
        try:
            self.db_conn = psycopg2.connect(config.database_url)
            self.logger.info("Connected to Supabase database")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    async def start_monitoring(self):
        """Start the monitoring service"""
        self.monitoring_active = True
        self.logger.info("Starting FPL monitoring service")
        
        # Start monitoring tasks
        asyncio.create_task(self.monitor_fpl_data())
        asyncio.create_task(self.process_notifications())

    async def stop_monitoring(self):
        """Stop the monitoring service"""
        self.monitoring_active = False
        self.logger.info("Stopping FPL monitoring service")

    async def monitor_fpl_data(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Determine current game state
                game_state = await self.detect_game_state()
                
                # Monitor based on game state
                if game_state == 'live_matches':
                    await self.monitor_live_performance()
                elif game_state == 'price_update_window':
                    await self.monitor_price_changes()
                else:
                    await self.monitor_status_changes()
                
                # Wait before next cycle
                await asyncio.sleep(60)  # Base refresh rate
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(30)  # Wait before retry

    async def detect_game_state(self) -> str:
        """Detect current FPL game state"""
        try:
            # Check for live matches
            fixtures = self.supabase.table('fixtures').select('*').eq('started', True).eq('finished', False).execute()
            
            if fixtures.data:
                return 'live_matches'
            
            # Check for price update window (1:00-3:00 AM GMT / 6:00-8:00 PM PST)
            now = datetime.now(pytz.timezone('America/Los_Angeles'))
            if 18 <= now.hour < 20:  # 6:00-8:00 PM PST
                return 'price_update_window'
            
            return 'between_matches'
            
        except Exception as e:
            self.logger.error(f"Game state detection error: {e}")
            return 'unknown'

    async def monitor_live_performance(self):
        """Monitor live performance stats"""
        try:
            # Fetch live data from FPL API
            live_data = await self.fetch_fpl_data('live')
            
            if live_data:
                # Process live data and detect changes
                await self.process_live_data(live_data)
                
        except Exception as e:
            self.logger.error(f"Live performance monitoring error: {e}")

    async def monitor_price_changes(self):
        """Monitor price changes during update windows"""
        try:
            # Fetch bootstrap data for price changes
            bootstrap_data = await self.fetch_fpl_data('bootstrap-static')
            
            if bootstrap_data:
                await self.process_price_changes(bootstrap_data)
                
        except Exception as e:
            self.logger.error(f"Price change monitoring error: {e}")

    async def monitor_status_changes(self):
        """Monitor player status changes"""
        try:
            # Fetch bootstrap data for status changes
            bootstrap_data = await self.fetch_fpl_data('bootstrap-static')
            
            if bootstrap_data:
                await self.process_status_changes(bootstrap_data)
                
        except Exception as e:
            self.logger.error(f"Status change monitoring error: {e}")

    async def fetch_fpl_data(self, endpoint: str) -> Optional[Dict]:
        """Fetch data from FPL API"""
        try:
            url = f"{config.fpl_base_url}/{endpoint}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"FPL API fetch error: {e}")
            return None

    async def process_live_data(self, live_data: Dict):
        """Process live match data and detect changes"""
        # Implementation similar to your existing monitor.py
        # This would include the sophisticated change detection logic
        pass

    async def process_price_changes(self, bootstrap_data: Dict):
        """Process price changes and generate notifications"""
        # Implementation for price change detection
        pass

    async def process_status_changes(self, bootstrap_data: Dict):
        """Process status changes and generate notifications"""
        # Implementation for status change detection
        pass

    async def process_notifications(self):
        """Process and send notifications to users"""
        while self.monitoring_active:
            try:
                # Get pending notifications from database
                notifications = self.supabase.table('user_notifications').select('*').eq('is_read', False).limit(100).execute()
                
                for notification in notifications.data:
                    # Send push notification
                    await self.send_push_notification(notification)
                    
                    # Broadcast to WebSocket connections
                    await self.broadcast_notification(notification)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Notification processing error: {e}")
                await asyncio.sleep(30)

    async def send_push_notification(self, notification: Dict):
        """Send push notification to user's device"""
        # Implementation for APNS push notifications
        pass

    async def broadcast_notification(self, notification: Dict):
        """Broadcast notification to WebSocket connections"""
        if self.websocket_connections:
            message = json.dumps(notification)
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(message)
                except:
                    # Remove disconnected websockets
                    self.websocket_connections.discard(websocket)

    async def add_websocket_connection(self, websocket: WebSocket):
        """Add new WebSocket connection"""
        self.websocket_connections.add(websocket)

    async def remove_websocket_connection(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.websocket_connections.discard(websocket)

# ========================================
# FASTAPI APPLICATION
# ========================================

# Global monitoring service instance
monitoring_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global monitoring_service
    monitoring_service = FPLMonitoringService()
    await monitoring_service.start_monitoring()
    yield
    await monitoring_service.stop_monitoring()

# Create FastAPI app
app = FastAPI(
    title="FPL Mobile Monitor API",
    description="API for FPL mobile monitoring and notifications",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
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
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "FPL Mobile Monitor"}

@app.get("/api/v1/notifications/timeline")
async def get_notification_timeline(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get user's notification timeline"""
    try:
        result = monitoring_service.supabase.rpc(
            'get_user_notifications',
            {
                'p_user_id': user_id,
                'p_limit': limit,
                'p_offset': offset
            }
        ).execute()
        
        return {"notifications": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/notifications/mark-read")
async def mark_notifications_read(
    user_id: str,
    notification_ids: List[str],
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Mark notifications as read"""
    try:
        result = monitoring_service.supabase.rpc(
            'mark_notifications_read',
            {
                'p_user_id': user_id,
                'p_notification_ids': notification_ids
            }
        ).execute()
        
        return {"updated_count": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/notifications/unread-count")
async def get_unread_count(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get unread notification count"""
    try:
        result = monitoring_service.supabase.rpc(
            'get_unread_count',
            {'p_user_id': user_id}
        ).execute()
        
        return {"unread_count": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/players/search")
async def search_players(query: str, limit: int = 20):
    """Search for players"""
    try:
        result = monitoring_service.supabase.table('players').select('*').ilike('web_name', f'%{query}%').limit(limit).execute()
        return {"players": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/players/{player_id}/stats")
async def get_player_stats(player_id: int, gameweek: Optional[int] = None):
    """Get player statistics"""
    try:
        query = monitoring_service.supabase.table('gameweek_stats').select('*').eq('player_id', player_id)
        
        if gameweek:
            query = query.eq('gameweek', gameweek)
        
        result = query.execute()
        return {"stats": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/monitoring/status")
async def get_monitoring_status():
    """Get monitoring service status"""
    return {
        "monitoring_active": monitoring_service.monitoring_active if monitoring_service else False,
        "websocket_connections": len(monitoring_service.websocket_connections) if monitoring_service else 0,
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    await monitoring_service.add_websocket_connection(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await monitoring_service.remove_websocket_connection(websocket)

# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    uvicorn.run(
        "fpl_monitor_service:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
