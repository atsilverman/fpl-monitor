#!/usr/bin/env python3
"""
FPL Mobile Monitor - Production Service
=====================================

Production-ready monitoring service with Supabase integration and dynamic refresh intervals.
This replaces the basic production_monitor.py with sophisticated game state detection.
"""

import os
import sys
import json
import time
import asyncio
import logging
import requests
import pytz
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# Load environment variables
load_dotenv()

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
    
    # Supabase configuration
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # User timezone
    user_timezone: str = "America/Los_Angeles"

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
        self.monitoring_active = False
        self.websocket_connections: Set[WebSocket] = set()
        
        # Supabase configuration
        self.supabase_url = config.supabase_url
        self.supabase_key = config.supabase_key
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json'
        }
        
        # FPL scoring multipliers - copied from Discord bot
        self.goal_multipliers = {1: 10, 2: 6, 3: 5, 4: 4}  # GK, DEF, MID, FWD
        self.cs_multipliers = {1: 4, 2: 4, 3: 1, 4: 0}     # GK, DEF, MID, FWD
        self.assist_multipliers = {1: 3, 2: 3, 3: 3, 4: 3}  # All positions get 3 points for assist
        self.red_card_multipliers = {1: -3, 2: -3, 3: -3, 4: -3}  # All positions lose 3 points for red card
        self.yellow_card_multipliers = {1: -1, 2: -1, 3: -1, 4: -1}  # All positions lose 1 point for yellow card
        
        # Team mapping (no emojis for mobile app)
        self.team_names = {
            'Arsenal': 'Arsenal', 'Aston Villa': 'Aston Villa', 'Bournemouth': 'Bournemouth',
            'Brentford': 'Brentford', 'Brighton': 'Brighton', 'Burnley': 'Burnley',
            'Chelsea': 'Chelsea', 'Crystal Palace': 'Crystal Palace', 'Everton': 'Everton',
            'Fulham': 'Fulham', 'Leeds': 'Leeds', 'Liverpool': 'Liverpool',
            'Man City': 'Man City', 'Man Utd': 'Man Utd', 'Newcastle': 'Newcastle',
            'Nott\'m Forest': 'Nott\'m Forest', 'Sunderland': 'Sunderland', 'Spurs': 'Spurs',
            'West Ham': 'West Ham', 'Wolves': 'Wolves'
        }
        
        # Dynamic monitoring configuration
        self.monitoring_config = {
            'live_performance': {
                'refresh_seconds': 60,
                'active_during': ['live_matches', 'upcoming_matches'],
                'priority': 'high',
                'fixture_dependent': True,
                'description': 'Goals, assists, cards, clean sheets'
            },
            'status_changes': {
                'refresh_seconds': 3600,  # 1 hour
                'active_during': ['always'],
                'priority': 'medium',
                'fixture_dependent': False,
                'description': 'Injuries, suspensions, availability'
            },
            'price_changes': {
                'refresh_seconds': 300,  # 5 minutes during price windows
                'active_during': ['price_update_windows'],
                'priority': 'high',
                'fixture_dependent': False,
                'description': 'Player price movements (6:30-6:40 PM user time - 10 minutes only)'
            },
            'final_bonus': {
                'refresh_seconds': 300,  # 5 minutes until bonus awarded
                'active_during': ['bonus_monitoring'],
                'priority': 'high',
                'fixture_dependent': False,
                'description': 'Final bonus points from FPL API'
            }
        }
        
        # Monitoring state tracking
        self.current_game_state = 'no_live_matches'
        self.last_refresh_times = {}
        self.price_window_notification_sent = False
        self.bonus_awarded = False
        self.previous_prices = {}
        
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/opt/fpl-monitor/monitor.log')
            ]
        )
        self.logger = logging.getLogger('fpl_monitor')

    async def start_monitoring(self):
        """Start the dynamic monitoring service"""
        self.monitoring_active = True
        self.logger.info("Starting FPL Dynamic Monitoring Service")
        self.logger.info("Monitoring modes: Live Performance, Status Changes, Price Changes, Final Bonus")
        
        # Initialize monitoring state
        await self.update_monitoring_state()
        
        # Start background monitoring task
        asyncio.create_task(self.monitoring_loop())

    async def stop_monitoring(self):
        """Stop the monitoring service"""
        self.monitoring_active = False
        self.logger.info("Stopping FPL monitoring service")

    async def monitoring_loop(self):
        """Background monitoring loop that runs continuously"""
        while self.monitoring_active:
            try:
                # Update monitoring state
                await self.update_monitoring_state()
                
                # Check each monitoring category
                for category_name in self.monitoring_config:
                    if self.should_monitor_category(category_name):
                        current_time = int(time.time())
                        next_refresh = self.get_next_refresh_time(category_name)
                        
                        if current_time >= next_refresh:
                            await self.refresh_category(category_name)
                            self.last_refresh_times[category_name] = current_time
                
                # Sleep for 10 seconds before next check
                await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def refresh_category(self, category_name: str):
        """Refresh a specific monitoring category"""
        try:
            self.logger.info(f"Refreshing category: {category_name}")
            
            if category_name == 'live_performance':
                await self.refresh_live_performance()
            elif category_name == 'status_changes':
                await self.refresh_status_changes()
            elif category_name == 'price_changes':
                await self.refresh_price_changes()
            elif category_name == 'final_bonus':
                await self.refresh_final_bonus()
                
        except Exception as e:
            self.logger.error(f"Error refreshing category {category_name}: {e}")

    async def refresh_live_performance(self):
        """Refresh live performance data"""
        self.logger.info("Refreshing live performance data")
        # TODO: Implement live performance monitoring

    async def refresh_status_changes(self):
        """Refresh status changes"""
        self.logger.info("Refreshing status changes")
        # TODO: Implement status change monitoring

    async def refresh_price_changes(self):
        """Refresh price changes - Enhanced version with Supabase integration"""
        try:
            self.logger.info("Refreshing price changes")
            
            # Get FPL data
            fpl_data = await self.get_fpl_data()
            if not fpl_data:
                return
            
            # Get Supabase data
            supabase_data = await self.get_supabase_players()
            if not supabase_data:
                return
            
            # Detect changes
            changes = self.detect_price_changes(fpl_data, supabase_data)
            
            if changes:
                self.logger.info(f"Found {len(changes)} price changes")
                await self.update_supabase_prices(changes)
            else:
                self.logger.info("No price changes detected")
                
        except Exception as e:
            self.logger.error(f"Error refreshing price changes: {e}")

    async def refresh_final_bonus(self):
        """Refresh final bonus points"""
        self.logger.info("Refreshing final bonus points")
        # TODO: Implement final bonus monitoring

    async def get_fpl_data(self):
        """Get current FPL data from the API"""
        try:
            response = requests.get(f"{config.fpl_base_url}/bootstrap-static/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                players = data['elements']
                self.logger.info(f"Fetched {len(players)} players from FPL API")
                return data  # Return full data, not just players
            else:
                self.logger.error(f"FPL API error: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching FPL data: {e}")
            return None

    async def get_supabase_players(self):
        """Get current player data from Supabase"""
        try:
            response = requests.get(
                f'{self.supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost&limit=1000', 
                headers=self.headers, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Fetched {len(data)} players from Supabase")
                return data
            else:
                self.logger.error(f"Supabase error: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching Supabase data: {e}")
            return None

    def detect_price_changes(self, fpl_data, supabase_data):
        """Detect price changes between FPL API and Supabase"""
        if not fpl_data or not supabase_data:
            return []
        
        # Create lookup dictionaries
        fpl_prices = {player['id']: player['now_cost'] for player in fpl_data['elements']}
        supabase_prices = {player['fpl_id']: player['now_cost'] for player in supabase_data}
        
        changes = []
        for fpl_id, fpl_price in fpl_prices.items():
            if fpl_id in supabase_prices:
                supabase_price = supabase_prices[fpl_id]
                if fpl_price != supabase_price:
                    # Find player name
                    player_name = next((p['web_name'] for p in fpl_data['elements'] if p['id'] == fpl_id), 'Unknown')
                    changes.append({
                        'fpl_id': fpl_id,
                        'name': player_name,
                        'old_price': supabase_price,
                        'new_price': fpl_price,
                        'change': fpl_price - supabase_price
                    })
        
        return changes

    async def update_supabase_prices(self, changes):
        """Update Supabase with new prices"""
        if not changes:
            return True
        
        self.logger.info(f"Updating {len(changes)} players in Supabase...")
        
        success_count = 0
        for change in changes:
            try:
                response = requests.patch(
                    f'{self.supabase_url}/rest/v1/players?fpl_id=eq.{change["fpl_id"]}',
                    headers=self.headers,
                    json={'now_cost': change['new_price'], 'updated_at': 'now()'},
                    timeout=5
                )
                
                if response.status_code in [200, 204]:
                    success_count += 1
                    self.logger.info(f"  {change['name']}: {change['old_price']/10:.1f}m → {change['new_price']/10:.1f}m")
                else:
                    self.logger.error(f"  {change['name']}: Failed ({response.status_code})")
                    
            except Exception as e:
                self.logger.error(f"  {change['name']}: Error - {e}")
        
        self.logger.info(f"Updated {success_count}/{len(changes)} players successfully")
        return success_count == len(changes)

    def is_price_update_window(self) -> bool:
        """Check if current time is within price update window (6:30-6:40 PM Pacific)"""
        try:
            utc_now = datetime.now(timezone.utc)
            user_tz = pytz.timezone(config.user_timezone)
            user_time = utc_now.astimezone(user_tz)
            
            current_hour = user_time.hour
            current_minute = user_time.minute
            
            # 6:30 PM = 18:30, 6:40 PM = 18:40 (10 minutes window)
            return current_hour == 18 and 30 <= current_minute < 40
        except Exception as e:
            self.logger.error(f"Error checking price update window: {e}")
            return False

    async def detect_game_state(self) -> str:
        """Detect current game state using FPL API data"""
        try:
            # Get FPL bootstrap data
            bootstrap_data = await self.get_fpl_data()
            if not bootstrap_data:
                return 'unknown'
            
            current_event = bootstrap_data.get('current-event')
            
            # If no current event, we're between gameweeks
            if not current_event:
                return 'no_live_matches'
            
            # Check if we're in bonus monitoring phase
            if await self.should_monitor_bonus():
                return 'bonus_monitoring'
            
            # Check for price update window
            if self.is_price_update_window():
                return 'price_update_windows'
            
            # Check if current gameweek has live matches
            # For now, default to no_live_matches since we don't have live fixture data
            return 'no_live_matches'
            
        except Exception as e:
            self.logger.error(f"Error detecting game state: {e}")
            return 'unknown'

    async def should_monitor_bonus(self) -> bool:
        """Check if we should monitor for final bonus points"""
        try:
            if self.bonus_awarded:
                return False
            
            bootstrap_data = await self.get_fpl_data()
            if not bootstrap_data:
                return False
            
            current_event = bootstrap_data.get('current-event')
            if not current_event:
                return False
            
            events = bootstrap_data.get('events', [])
            current_gameweek = next((e for e in events if e['id'] == current_event), None)
            
            if not current_gameweek:
                return False
            
            is_finished = current_gameweek.get('finished', False)
            is_data_checked = current_gameweek.get('data_checked', False)
            
            return is_finished and is_data_checked
            
        except Exception as e:
            self.logger.error(f"Error checking bonus monitoring: {e}")
            return False

    def should_monitor_category(self, category_name: str) -> bool:
        """Determine if a monitoring category should be active based on game state"""
        if category_name not in self.monitoring_config:
            return False
            
        config = self.monitoring_config[category_name]
        game_state = self.current_game_state
        
        # Check if category is active during current game state
        if 'always' in config['active_during']:
            return True
            
        if game_state in config['active_during']:
            return True
            
        # Special handling for price update windows
        if 'price_update_windows' in config['active_during'] and self.is_price_update_window():
            return True
            
        return False

    def get_next_refresh_time(self, category_name: str) -> int:
        """Calculate when the next refresh should happen for a category"""
        if not self.should_monitor_category(category_name):
            return 0
            
        config = self.monitoring_config[category_name]
        last_refresh = self.last_refresh_times.get(category_name, 0)
        next_refresh = last_refresh + config['refresh_seconds']
        
        return next_refresh

    async def update_monitoring_state(self):
        """Update the current monitoring state"""
        old_state = self.current_game_state
        self.current_game_state = await self.detect_game_state()
        
        if old_state != self.current_game_state:
            self.logger.info(f"Game state changed: {old_state} -> {self.current_game_state}")
            
            # Log monitoring mode changes
            active_categories = [cat for cat in self.monitoring_config if self.should_monitor_category(cat)]
            self.logger.info(f"Active monitoring categories: {', '.join(active_categories)}")

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
    title="FPL Dynamic Monitoring Service",
    description="Production FPL monitoring with dynamic refresh intervals and game state detection",
    version="2.0.0",
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
    return {
        "status": "healthy", 
        "service": "FPL Dynamic Monitoring Service",
        "version": "2.0.0",
        "monitoring_active": monitoring_service.monitoring_active if monitoring_service else False
    }

@app.get("/api/v1/monitoring/status")
async def get_monitoring_status():
    """Get monitoring service status"""
    if not monitoring_service:
        return {
            "monitoring_active": False,
            "current_game_state": "unknown",
            "websocket_connections": 0,
            "timestamp": datetime.now().isoformat(),
            "fpl_api_connected": False
        }
    
    return {
        "monitoring_active": monitoring_service.monitoring_active,
        "current_game_state": monitoring_service.current_game_state,
        "websocket_connections": len(monitoring_service.websocket_connections),
        "timestamp": datetime.now().isoformat(),
        "fpl_api_connected": True,
        "monitoring_categories": {
            category: {
                "active": monitoring_service.should_monitor_category(category),
                "next_refresh": monitoring_service.get_next_refresh_time(category),
                "config": monitoring_service.monitoring_config[category]
            }
            for category in monitoring_service.monitoring_config
        },
        "user_timezone": config.user_timezone,
        "price_window_active": monitoring_service.is_price_update_window()
    }

@app.get("/api/v1/fpl/current-gameweek")
async def get_current_gameweek():
    """Get current FPL gameweek info"""
    try:
        bootstrap_data = await monitoring_service.get_fpl_data()
        
        if not bootstrap_data:
            raise HTTPException(status_code=500, detail="Failed to fetch FPL data")
        
        current_event = bootstrap_data.get('current-event')
        events = bootstrap_data.get('events', [])
        
        current_gameweek = None
        for event in events:
            if event.get('id') == current_event:
                current_gameweek = event
                break
        
        return {
            "current_event": current_event,
            "current_gameweek": current_gameweek,
            "total_events": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        "fpl_monitor_production:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False  # Set to False for production
    )
