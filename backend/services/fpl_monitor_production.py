#!/usr/bin/env python3
"""
FPL Mobile Monitor - Event-Based Enhanced Production Service
==========================================================

Scalable event-based monitoring service that stores events once
and serves all users efficiently. Massive scalability improvement
over the previous per-user notification approach.
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

class EventData(BaseModel):
    event_type: str
    player_id: int
    player_name: str
    team_name: str
    team_abbreviation: Optional[str] = None
    points: int = 0
    points_change: int = 0
    points_category: Optional[str] = None
    total_points: Optional[int] = None
    gameweek_points: Optional[int] = None
    gameweek: int
    fixture_id: Optional[int] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    fixture: Optional[str] = None
    player_price: Optional[float] = None
    price_change: Optional[float] = None
    player_status: Optional[str] = None
    old_status: Optional[str] = None
    news_text: Optional[str] = None
    old_news: Optional[str] = None
    old_value: Optional[int] = None
    new_value: Optional[int] = None
    title: str
    message: str

class UserOwnershipUpdate(BaseModel):
    user_id: str
    fpl_manager_id: int
    owned_players: List[int]

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
        
        # State tracking
        self.previous_live_data = {}
        self.previous_bonus_data = {}
        self.processed_gameweeks = set()
        
        # FPL scoring multipliers
        self.goal_multipliers = {1: 10, 2: 6, 3: 5, 4: 4}  # GK, DEF, MID, FWD
        self.cs_multipliers = {1: 4, 2: 4, 3: 1, 4: 0}     # GK, DEF, MID, FWD
        self.assist_multipliers = {1: 3, 2: 3, 3: 3, 4: 3}  # All positions get 3 points for assist
        self.red_card_multipliers = {1: -3, 2: -3, 3: -3, 4: -3}  # All positions lose 3 points for red card
        self.yellow_card_multipliers = {1: -1, 2: -1, 3: -1, 4: -1}  # All positions lose 1 point for yellow card
        
        # Team mapping
        self.team_names = {
            'Arsenal': 'Arsenal', 'Aston Villa': 'Aston Villa', 'Bournemouth': 'Bournemouth',
            'Brentford': 'Brentford', 'Brighton': 'Brighton', 'Burnley': 'Burnley',
            'Chelsea': 'Chelsea', 'Crystal Palace': 'Crystal Palace', 'Everton': 'Everton',
            'Fulham': 'Fulham', 'Leeds': 'Leeds', 'Liverpool': 'Liverpool',
            'Man City': 'Man City', 'Man Utd': 'Man Utd', 'Newcastle': 'Newcastle',
            'Nott\'m Forest': 'Nott\'m Forest', 'Sunderland': 'Sunderland', 'Spurs': 'Spurs',
            'West Ham': 'West Ham', 'Wolves': 'Wolves'
        }
        
        # Team abbreviations
        self.team_abbreviations = {
            'Arsenal': 'ARS', 'Aston Villa': 'AVL', 'Bournemouth': 'BOU',
            'Brentford': 'BRE', 'Brighton': 'BHA', 'Burnley': 'BUR',
            'Chelsea': 'CHE', 'Crystal Palace': 'CRY', 'Everton': 'EVE',
            'Fulham': 'FUL', 'Leeds': 'LEE', 'Liverpool': 'LIV',
            'Man City': 'MCI', 'Man Utd': 'MUN', 'Newcastle': 'NEW',
            'Nott\'m Forest': 'NFO', 'Sunderland': 'SUN', 'Spurs': 'TOT',
            'West Ham': 'WHU', 'Wolves': 'WOL'
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
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'fpl_monitor_events.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file)
            ]
        )
        self.logger = logging.getLogger('fpl_monitor_events')

    async def start_monitoring(self):
        """Start the dynamic monitoring service"""
        self.monitoring_active = True
        self.logger.info("Starting FPL Event-Based Enhanced Monitoring Service")
        self.logger.info("Scalable architecture: 1 event = 1 record regardless of user count")
        
        # Load processed gameweeks
        await self.load_processed_gameweeks()
        
        # Initialize monitoring state
        await self.update_monitoring_state()
        
        # Start background monitoring task
        asyncio.create_task(self.monitoring_loop())

    async def stop_monitoring(self):
        """Stop the monitoring service"""
        self.monitoring_active = False
        self.logger.info("Stopping FPL monitoring service")

    async def store_event(self, event_data: EventData):
        """Store a single event in the events table (scalable approach)"""
        try:
            response = requests.post(
                f'{self.supabase_url}/rest/v1/events',
                headers=self.headers,
                json=event_data.dict(),
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.logger.info(f"✅ Stored event: {event_data.event_type} - {event_data.player_name}")
                return True
            else:
                self.logger.error(f"❌ Failed to store event: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error storing event: {e}")
            return False

    async def create_live_performance_event(self, change_data: Dict, gameweek: int) -> EventData:
        """Create a live performance event from change data"""
        event_type = change_data['event_type']
        player_id = change_data['player_id']
        player_name = change_data['player_name']
        team_name = change_data['team_name']
        old_value = change_data['old_value']
        new_value = change_data['new_value']
        points_change = change_data['points_change']
        
        # Create title and message based on event type
        if event_type == 'live_goals_scored':
            title = "⚽ Goal!"
            message = f"{player_name} scored for {team_name}"
            points_category = "Goal"
        elif event_type == 'live_assists':
            title = "🎯 Assist!"
            message = f"{player_name} provided an assist for {team_name}"
            points_category = "Assist"
        elif event_type == 'live_clean_sheets':
            title = "🛡️ Clean Sheet!"
            message = f"{player_name} kept a clean sheet for {team_name}"
            points_category = "Clean Sheet"
        elif event_type == 'live_bonus':
            title = "⭐ Bonus Points!"
            message = f"{player_name} earned {new_value - old_value} bonus points for {team_name}"
            points_category = "Bonus"
        elif event_type == 'live_yellow_cards':
            title = "🟡 Yellow Card"
            message = f"{player_name} received a yellow card for {team_name}"
            points_category = "Yellow Card"
        elif event_type == 'live_red_cards':
            title = "🔴 Red Card"
            message = f"{player_name} received a red card for {team_name}"
            points_category = "Red Card"
        else:
            title = "📢 FPL Update"
            message = f"{player_name} - {event_type} update"
            points_category = "Other"
        
        return EventData(
            event_type=event_type,
            player_id=player_id,
            player_name=player_name,
            team_name=team_name,
            team_abbreviation=self.team_abbreviations.get(team_name, team_name[:3].upper()),
            points=new_value,
            points_change=points_change,
            points_category=points_category,
            gameweek=gameweek,
            fixture_id=change_data.get('fixture_id'),
            old_value=old_value,
            new_value=new_value,
            title=title,
            message=message
        )

    async def create_price_change_event(self, change_data: Dict) -> EventData:
        """Create a price change event"""
        fpl_id = change_data['fpl_id']
        player_name = change_data['name']
        old_price = change_data['old_price']
        new_price = change_data['new_price']
        price_change = change_data['change']
        
        # Get team info
        team_name = await self.get_player_team_name(fpl_id)
        
        title = "💰 Price Change!"
        if price_change > 0:
            message = f"{player_name}'s price increased to £{new_price/10:.1f}m"
        else:
            message = f"{player_name}'s price decreased to £{new_price/10:.1f}m"
        
        return EventData(
            event_type='price_changes',
            player_id=fpl_id,
            player_name=player_name,
            team_name=team_name,
            team_abbreviation=self.team_abbreviations.get(team_name, team_name[:3].upper()),
            points=0,
            points_change=0,
            points_category="Price Rise" if price_change > 0 else "Price Fall",
            gameweek=await self.get_current_gameweek(),
            player_price=new_price/10,
            price_change=price_change/10,
            old_value=old_price,
            new_value=new_price,
            title=title,
            message=message
        )

    async def create_status_change_event(self, change_data: Dict) -> EventData:
        """Create a status change event"""
        fpl_id = change_data['fpl_id']
        player_name = change_data['name']
        change_type = change_data['change_type']
        old_status = change_data['old_value']
        new_status = change_data['new_value']
        old_news = change_data['old_news']
        new_news = change_data['new_news']
        
        # Get team info
        team_name = await self.get_player_team_name(fpl_id)
        
        if change_type == 'status':
            title = "📊 Status Change"
            message = self.create_status_change_message(player_name, old_status, new_status, new_news)
        else:  # news change
            title = "📊 News Update"
            message = self.create_news_change_message(player_name, new_status, old_news, new_news)
        
        return EventData(
            event_type='status_changes',
            player_id=fpl_id,
            player_name=player_name,
            team_name=team_name,
            team_abbreviation=self.team_abbreviations.get(team_name, team_name[:3].upper()),
            points=0,
            points_change=0,
            points_category=self.get_status_display_text(new_status),
            gameweek=await self.get_current_gameweek(),
            player_status=new_status,
            old_status=old_status,
            news_text=new_news,
            old_news=old_news,
            old_value=0,
            new_value=0,
            title=title,
            message=message
        )

    async def get_player_team_name(self, player_id: int) -> str:
        """Get team name for a player"""
        try:
            response = requests.get(
                f'{self.supabase_url}/rest/v1/players?fpl_id=eq.{player_id}&select=teams(name)',
                headers=self.headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data and data[0].get('teams'):
                    return data[0]['teams']['name']
            return 'Unknown'
        except Exception as e:
            self.logger.error(f"Error getting team name for player {player_id}: {e}")
            return 'Unknown'

    async def get_current_gameweek(self) -> int:
        """Get current gameweek"""
        try:
            response = requests.get(f"{config.fpl_base_url}/bootstrap-static/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('current-event', 1)
            return 1
        except Exception as e:
            self.logger.error(f"Error getting current gameweek: {e}")
            return 1

    def create_status_change_message(self, player_name, old_status, new_status, news):
        """Create a message for status changes"""
        old_text = self.get_status_display_text(old_status)
        new_text = self.get_status_display_text(new_status)
        
        if news and news.strip():
            return f"{player_name} status changed from {old_text} to {new_text}. {news}"
        else:
            return f"{player_name} status changed from {old_text} to {new_text}"

    def create_news_change_message(self, player_name, status, old_news, new_news):
        """Create a message for news changes"""
        status_text = self.get_status_display_text(status)
        
        if new_news and new_news.strip():
            return f"{player_name} ({status_text}) - {new_news}"
        else:
            return f"{player_name} ({status_text}) - News updated"

    def get_status_display_text(self, status):
        """Convert status code to display text"""
        status_map = {
            'a': 'Available',
            'd': 'Doubtful', 
            'i': 'Injured',
            's': 'Suspended',
            'u': 'Unavailable',
            'n': 'Not Eligible'
        }
        return status_map.get(status, 'Unknown')

    # ... (rest of the monitoring methods remain the same as the original)
    # The key difference is that instead of creating per-user notifications,
    # we now create single events and let the database function handle user-specific queries

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
        """Refresh live performance data with change detection"""
        try:
            self.logger.info("Refreshing live performance data")
            
            # Get current gameweek
            bootstrap_data = await self.get_fpl_data()
            if not bootstrap_data:
                return
            
            current_event = bootstrap_data.get('current-event')
            if not current_event:
                return
            
            # Fetch live data
            live_data = await self.get_live_data(current_event)
            if not live_data:
                return
            
            # Detect changes
            changes = await self.detect_live_changes(live_data, current_event)
            
            if changes:
                self.logger.info(f"Found {len(changes)} live performance changes")
                # Store each change as a single event
                for change in changes:
                    event_data = await self.create_live_performance_event(change, current_event)
                    await self.store_event(event_data)
            else:
                self.logger.info("No live performance changes detected")
                
        except Exception as e:
            self.logger.error(f"Error refreshing live performance: {e}")

    async def refresh_price_changes(self):
        """Refresh price changes - Enhanced version with event storage"""
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
            changes = await self.detect_price_changes(fpl_data, supabase_data)
            
            if changes:
                self.logger.info(f"Found {len(changes)} price changes")
                # Update Supabase prices
                await self.update_supabase_prices(changes)
                # Store each change as a single event
                for change in changes:
                    event_data = await self.create_price_change_event(change)
                    await self.store_event(event_data)
            else:
                self.logger.info("No price changes detected")
                
        except Exception as e:
            self.logger.error(f"Error refreshing price changes: {e}")

    async def refresh_status_changes(self):
        """Refresh status and news changes with event storage"""
        try:
            self.logger.info("Refreshing status and news changes")
            
            # Get FPL data
            fpl_data = await self.get_fpl_data()
            if not fpl_data:
                return
            
            # Get Supabase data
            supabase_data = await self.get_supabase_players_with_news()
            if not supabase_data:
                return
            
            # Detect changes
            changes = await self.detect_news_and_status_changes(fpl_data, supabase_data)
            
            if changes:
                self.logger.info(f"Found {len(changes)} status/news changes")
                # Update Supabase with new data
                await self.update_supabase_news_and_status(changes)
                # Store each change as a single event
                for change in changes:
                    event_data = await self.create_status_change_event(change)
                    await self.store_event(event_data)
            else:
                self.logger.info("No status/news changes detected")
                
        except Exception as e:
            self.logger.error(f"Error refreshing status changes: {e}")

    # ... (include all other methods from the original service)
    # The key change is replacing per-user notification creation with single event storage

    async def get_fpl_data(self):
        """Get current FPL data from the API"""
        try:
            response = requests.get(f"{config.fpl_base_url}/bootstrap-static/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                players = data['elements']
                self.logger.info(f"Fetched {len(players)} players from FPL API")
                return data
            else:
                self.logger.error(f"FPL API error: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching FPL data: {e}")
            return None

    async def get_live_data(self, gameweek: int):
        """Get live data for a specific gameweek"""
        try:
            response = requests.get(f"{config.fpl_base_url}/event/{gameweek}/live/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Fetched live data for gameweek {gameweek}")
                return data
            else:
                self.logger.error(f"Live data API error: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching live data: {e}")
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

    async def get_supabase_players_with_news(self):
        """Get current player data from Supabase including news and status"""
        try:
            response = requests.get(
                f'{self.supabase_url}/rest/v1/players?select=fpl_id,web_name,now_cost,status,news,news_added&limit=1000', 
                headers=self.headers, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Fetched {len(data)} players with news from Supabase")
                return data
            else:
                self.logger.error(f"Supabase error: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching Supabase data: {e}")
            return None

    # ... (include all other detection and update methods from the original service)

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
    title="FPL Event-Based Enhanced Monitoring Service",
    description="Scalable FPL monitoring with event-based architecture - 1 event = 1 record",
    version="4.0.0",
    lifespan=lifespan
)

# Add CORS middleware
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
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "FPL Event-Based Enhanced Monitoring Service",
        "version": "4.0.0",
        "monitoring_active": monitoring_service.monitoring_active if monitoring_service else False,
        "architecture": "Event-based (scalable)"
    }

@app.get("/api/v1/events/recent")
async def get_recent_events(limit: int = 50):
    """Get recent events (for testing)"""
    try:
        response = requests.get(
            f'{monitoring_service.supabase_url}/rest/v1/events?order=created_at.desc&limit={limit}',
            headers=monitoring_service.headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return {"events": response.json()}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch events")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/users/ownership")
async def update_user_ownership(ownership_data: UserOwnershipUpdate):
    """Update user ownership data"""
    try:
        response = requests.post(
            f'{monitoring_service.supabase_url}/rest/v1/rpc/update_user_ownership',
            headers=monitoring_service.headers,
            json={
                "p_user_id": ownership_data.user_id,
                "p_fpl_manager_id": ownership_data.fpl_manager_id,
                "p_owned_players": ownership_data.owned_players
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return {"status": "success", "message": "Ownership updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update ownership")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/{user_id}/notifications")
async def get_user_notifications(user_id: str, limit: int = 50, offset: int = 0):
    """Get user-specific notifications with ownership data"""
    try:
        response = requests.post(
            f'{monitoring_service.supabase_url}/rest/v1/rpc/get_user_notifications',
            headers=monitoring_service.headers,
            json={
                "p_user_id": user_id,
                "p_limit": limit,
                "p_offset": offset
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return {"notifications": response.json()}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch notifications")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    uvicorn.run(
        "fpl_monitor_events_enhanced:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False
    )
