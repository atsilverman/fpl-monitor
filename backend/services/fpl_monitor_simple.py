#!/usr/bin/env python3
"""
FPL Mobile Monitor - Simplified Service for Testing
==================================================

Simplified version without Supabase dependencies for local testing.
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
from dataclasses import dataclass
from contextlib import asynccontextmanager

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
    
    # Database configuration (optional for testing)
    database_url: str = os.getenv("DATABASE_URL", "")

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
        self.db_conn = None
        self.monitoring_active = False
        self.websocket_connections: Set[WebSocket] = set()
        
        # FPL scoring multipliers - copied from Discord bot
        self.goal_multipliers = {1: 10, 2: 6, 3: 5, 4: 4}  # GK, DEF, MID, FWD
        self.cs_multipliers = {1: 4, 2: 4, 3: 1, 4: 0}     # GK, DEF, MID, FWD
        self.assist_multipliers = {1: 3, 2: 3, 3: 3, 4: 3}  # All positions get 3 points for assist
        self.red_card_multipliers = {1: -3, 2: -3, 3: -3, 4: -3}  # All positions lose 3 points for red card
        self.yellow_card_multipliers = {1: -1, 2: -1, 3: -1, 4: -1}  # All positions lose 1 point for yellow card
        
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
        
        # Notification categories - copied from Discord bot with mobile adaptations
        self.notification_categories = {
            'goals': {
                'description': 'Goal',
                'emoji': '⚽',
                'points_impact': True,
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0
            },
            'assists': {
                'description': 'Assist',
                'emoji': '🎯', 
                'points_impact': True,
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0
            },
            'clean_sheets': {
                'description': 'Clean sheet',
                'emoji': '🛡️',
                'negative_emoji': '🛡️❌',  # Shield with red X for clean sheet loss
                'points_impact': True,
                'position_relevant': [1, 2, 3],  # GK, DEF, MID get clean sheet points (GK/DEF: +4, MID: +1, FWD: +0)
                'minutes_required': 0  # FPL API already validates 60+ minutes
            },
            'bonus': {
                'description': 'BONUS*',
                'emoji': '⭐',
                'points_impact': True,
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 60  # Only notify after fixture exceeds 60 minutes
            },
            'bonus_final': {
                'description': 'BONUS (FINAL)',
                'emoji': '🟡',
                'points_impact': True,
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0,  # No minutes requirement - based on FPL API population
                'final_bonus': True  # Special flag for final bonus detection
            },
            'red_cards': {
                'description': 'Red cards',
                'emoji': '🟥',
                'points_impact': True,
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0
            },
            'yellow_cards': {
                'description': 'Yellow cards',
                'emoji': '🟨',
                'points_impact': True,
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0
            },
            'penalties_saved': {
                'description': 'Penalties saved',
                'emoji': '🧤',
                'points_impact': True,
                'position_relevant': [1],  # Only GK
                'minutes_required': 0
            },
            'penalties_missed': {
                'description': 'Penalties missed',
                'emoji': '❌',
                'points_impact': True,
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0
            },
            'own_goals': {
                'description': 'Own goals',
                'emoji': '😱',
                'points_impact': True,
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0
            },
            'saves': {
                'description': 'Saves',
                'emoji': '💾',
                'points_impact': True,
                'position_relevant': [1],  # Only GK
                'minutes_required': 0,
                'threshold_based': True,
                'threshold': 3  # Every 3 saves = +1 pt
            },
            'goals_conceded': {
                'description': 'Goals conceded',
                'emoji': '🥅',
                'points_impact': True,
                'position_relevant': [1, 2],  # Only GK/DEF
                'minutes_required': 0,
                'threshold_based': True,
                'threshold': 2  # Every 2 goals = -1 pt
            },
            'defensive_contribution': {
                'description': 'Defcon',
                'emoji': '🔄',
                'points_impact': True,
                'position_relevant': [2, 3, 4],  # DEF, MID, FWD
                'minutes_required': 0,  # No minutes requirement in FPL rules
                'derived_stat': True,
                'defender_threshold': 10,  # Tackles + CBI >= 10
                'midfielder_threshold': 12,  # Tackles + CBI + Recoveries >= 12
                'forward_threshold': 12     # Tackles + CBI + Recoveries >= 12 (same as MID)
            },
            'now_cost': {
                'description': 'Price change',
                'emoji': '💰',
                'points_impact': False,  # Price doesn't directly affect FPL points
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0
            },
            'status': {
                'description': 'Player status change',
                'emoji': '🏥',
                'points_impact': False,  # Status doesn't directly affect FPL points
                'position_relevant': [1, 2, 3, 4],  # All positions
                'minutes_required': 0,
                'status_based': True  # Special handling for status changes
            },
        }
        
        # Dynamic monitoring configuration - updated with your specifications
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
        
        # User timezone (default to Pacific, will be configurable later)
        self.user_timezone = 'America/Los_Angeles'
        
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('temp/logs/fpl_monitor.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def start_monitoring(self):
        """Start the dynamic monitoring service"""
        self.monitoring_active = True
        self.logger.info("Starting FPL dynamic monitoring service")
        
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
                # Refresh live performance data
                await self.refresh_live_performance()
            elif category_name == 'status_changes':
                # Refresh status changes
                await self.refresh_status_changes()
            elif category_name == 'price_changes':
                # Refresh price changes
                await self.refresh_price_changes()
            elif category_name == 'final_bonus':
                # Refresh final bonus
                await self.refresh_final_bonus()
                
        except Exception as e:
            self.logger.error(f"Error refreshing category {category_name}: {e}")

    async def refresh_live_performance(self):
        """Refresh live performance data"""
        # This would fetch live data and generate notifications
        # For now, just log that we're refreshing
        self.logger.info("Refreshing live performance data")

    async def refresh_status_changes(self):
        """Refresh status changes"""
        self.logger.info("Refreshing status changes")

    async def refresh_price_changes(self):
        """Refresh price changes"""
        self.logger.info("Refreshing price changes")

    async def refresh_final_bonus(self):
        """Refresh final bonus points"""
        self.logger.info("Refreshing final bonus points")
        
        # Check if bonus has been awarded
        # This would check if any gameweek_stats bonus values have been updated
        # For now, just log
        self.logger.info("Checking for final bonus points")

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

    async def add_websocket_connection(self, websocket: WebSocket):
        """Add new WebSocket connection"""
        self.websocket_connections.add(websocket)

    async def remove_websocket_connection(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.websocket_connections.discard(websocket)

    def get_user_timezone(self) -> str:
        """Get user timezone (will be configurable later)"""
        return self.user_timezone

    def is_price_update_window(self) -> bool:
        """Check if current time is within price update window (6:30 PM user time + 10 min)"""
        try:
            from datetime import datetime, timezone
            import pytz
            
            # Get current time in user timezone
            utc_now = datetime.now(timezone.utc)
            user_tz = pytz.timezone(self.get_user_timezone())
            user_time = utc_now.astimezone(user_tz)
            
            # Check if it's between 6:30 PM and 6:40 PM user time (10 minutes only)
            current_hour = user_time.hour
            current_minute = user_time.minute
            
            # 6:30 PM = 18:30, 6:40 PM = 18:40 (10 minutes window)
            if current_hour == 18 and 30 <= current_minute < 40:
                return True
                
            return False
        except Exception as e:
            self.logger.error(f"Error checking price update window: {e}")
            return False

    async def detect_game_state(self) -> str:
        """Detect current game state using FPL API data"""
        try:
            # Get FPL bootstrap data
            bootstrap_data = await self.fetch_fpl_data('bootstrap-static')
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
            # In production, this would check actual fixture status
            return 'no_live_matches'
            
        except Exception as e:
            self.logger.error(f"Error detecting game state: {e}")
            return 'unknown'

    async def should_monitor_bonus(self) -> bool:
        """Check if we should monitor for final bonus points"""
        try:
            # Check if bonus has already been awarded
            if self.bonus_awarded:
                return False
            
            # Get current gameweek data
            bootstrap_data = await self.fetch_fpl_data('bootstrap-static')
            if not bootstrap_data:
                return False
            
            current_event = bootstrap_data.get('current-event')
            if not current_event:
                return False
            
            # Check if current gameweek is finished and data_checked
            events = bootstrap_data.get('events', [])
            current_gameweek = next((e for e in events if e['id'] == current_event), None)
            
            if not current_gameweek:
                return False
            
            # Only monitor bonus if:
            # 1. Gameweek is finished (all fixtures completed)
            # 2. Data is checked (bonus points have been calculated)
            # 3. We haven't already processed bonus for this gameweek
            is_finished = current_gameweek.get('finished', False)
            is_data_checked = current_gameweek.get('data_checked', False)
            
            if is_finished and is_data_checked:
                # Check if we've already processed bonus for this gameweek
                # In production, this would check database for processed gameweeks
                return True
            
            return False
            
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
            
            # Send WebSocket notification about state change
            await self.broadcast_state_change(old_state, self.current_game_state)

    async def broadcast_state_change(self, old_state: str, new_state: str):
        """Broadcast state change to all WebSocket connections"""
        if not self.websocket_connections:
            return
            
        message = {
            "type": "state_change",
            "old_state": old_state,
            "new_state": new_state,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.websocket_connections.discard(websocket)

    async def generate_notifications_from_live_data(self, bootstrap_data: Dict, live_data: Dict, gameweek: int) -> List[Dict]:
        """Generate notifications from live FPL data"""
        notifications = []
        
        try:
            # Get team data
            teams = {team['id']: team['name'] for team in bootstrap_data.get('teams', [])}
            
            # Get player data
            players = {player['id']: player for player in bootstrap_data.get('elements', [])}
            
            # Process live data
            live_elements = live_data.get('elements', [])
            
            for element in live_elements:
                player_id = element.get('id')
                if player_id not in players:
                    continue
                
                player = players[player_id]
                team_id = player.get('team')
                team_name = teams.get(team_id, 'Unknown')
                
                # Get live stats
                stats = element.get('stats', {})
                
                # Generate notifications for various events
                notifications.extend(self._generate_player_notifications(
                    player, team_name, stats, gameweek
                ))
            
            # Sort by timestamp (most recent first)
            notifications.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error generating notifications: {e}")
        
        return notifications

    def _generate_player_notifications(self, player: Dict, team_name: str, stats: Dict, gameweek: int) -> List[Dict]:
        """Generate notifications for a specific player using Discord bot logic"""
        notifications = []
        player_name = player.get('web_name', 'Unknown')
        player_id = player.get('id')
        element_type = player.get('element_type', 1)  # 1=GK, 2=DEF, 3=MID, 4=FWD
        
        # Goal notifications - position-specific points
        goals = stats.get('goals_scored', 0)
        if goals > 0:
            points_per_goal = self.goal_multipliers.get(element_type, 4)
            total_points = goals * points_per_goal
            notifications.append({
                'id': f"goal_{player_id}_{gameweek}",
                'notification_type': 'goals',
                'player_name': player_name,
                'team_name': team_name,
                'fixture_id': None,
                'gameweek': gameweek,
                'old_value': 0,
                'new_value': goals,
                'points_change': total_points,
                'message': f"⚽ **GOAL** +{total_points} pts",
                'is_read': False,
                'timestamp': datetime.now().isoformat()
            })
        
        # Assist notifications - all positions get 3 points
        assists = stats.get('assists', 0)
        if assists > 0:
            points_per_assist = self.assist_multipliers.get(element_type, 3)
            total_points = assists * points_per_assist
            notifications.append({
                'id': f"assist_{player_id}_{gameweek}",
                'notification_type': 'assists',
                'player_name': player_name,
                'team_name': team_name,
                'fixture_id': None,
                'gameweek': gameweek,
                'old_value': 0,
                'new_value': assists,
                'points_change': total_points,
                'message': f"🎯 **ASSIST** +{total_points} pts",
                'is_read': False,
                'timestamp': datetime.now().isoformat()
            })
        
        # Clean sheet notifications - position-specific (GK/DEF: +4, MID: +1, FWD: +0)
        clean_sheets = stats.get('clean_sheets', 0)
        if clean_sheets > 0 and element_type in [1, 2, 3]:  # Only GK, DEF, MID get clean sheet points
            points_per_cs = self.cs_multipliers.get(element_type, 0)
            total_points = clean_sheets * points_per_cs
            if total_points > 0:  # Only notify if points > 0
                notifications.append({
                    'id': f"cs_{player_id}_{gameweek}",
                    'notification_type': 'clean_sheets',
                    'player_name': player_name,
                    'team_name': team_name,
                    'fixture_id': None,
                    'gameweek': gameweek,
                    'old_value': 0,
                    'new_value': clean_sheets,
                    'points_change': total_points,
                    'message': f"🛡️ **CLEAN SHEET** +{total_points} pts",
                    'is_read': False,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Bonus points - all positions get same points
        bonus = stats.get('bonus', 0)
        if bonus > 0:
            notifications.append({
                'id': f"bonus_{player_id}_{gameweek}",
                'notification_type': 'bonus',
                'player_name': player_name,
                'team_name': team_name,
                'fixture_id': None,
                'gameweek': gameweek,
                'old_value': 0,
                'new_value': bonus,
                'points_change': bonus,
                'message': f"⭐ **BONUS** +{bonus} pts",
                'is_read': False,
                'timestamp': datetime.now().isoformat()
            })
        
        # Yellow cards - all positions lose 1 point
        yellow_cards = stats.get('yellow_cards', 0)
        if yellow_cards > 0:
            points_per_yellow = self.yellow_card_multipliers.get(element_type, -1)
            total_points = yellow_cards * points_per_yellow
            notifications.append({
                'id': f"yellow_{player_id}_{gameweek}",
                'notification_type': 'yellow_cards',
                'player_name': player_name,
                'team_name': team_name,
                'fixture_id': None,
                'gameweek': gameweek,
                'old_value': 0,
                'new_value': yellow_cards,
                'points_change': total_points,
                'message': f"🟨 **YELLOW CARD** {total_points} pts",
                'is_read': False,
                'timestamp': datetime.now().isoformat()
            })
        
        # Red cards - all positions lose 3 points
        red_cards = stats.get('red_cards', 0)
        if red_cards > 0:
            points_per_red = self.red_card_multipliers.get(element_type, -3)
            total_points = red_cards * points_per_red
            notifications.append({
                'id': f"red_{player_id}_{gameweek}",
                'notification_type': 'red_cards',
                'player_name': player_name,
                'team_name': team_name,
                'fixture_id': None,
                'gameweek': gameweek,
                'old_value': 0,
                'new_value': red_cards,
                'points_change': total_points,
                'message': f"🟥 **RED CARD** {total_points} pts",
                'is_read': False,
                'timestamp': datetime.now().isoformat()
            })
        
        # Saves - only GK, threshold-based (every 3 saves = +1 pt)
        saves = stats.get('saves', 0)
        if saves > 0 and element_type == 1:  # Only GK
            points_from_saves = saves // 3  # Every 3 saves = +1 pt
            if points_from_saves > 0:
                notifications.append({
                    'id': f"saves_{player_id}_{gameweek}",
                    'notification_type': 'saves',
                    'player_name': player_name,
                    'team_name': team_name,
                    'fixture_id': None,
                    'gameweek': gameweek,
                    'old_value': 0,
                    'new_value': saves,
                    'points_change': points_from_saves,
                    'message': f"💾 **SAVES** +{points_from_saves} pts ({saves} saves)",
                    'is_read': False,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Goals conceded - only GK/DEF, threshold-based (every 2 goals = -1 pt)
        goals_conceded = stats.get('goals_conceded', 0)
        if goals_conceded > 0 and element_type in [1, 2]:  # Only GK/DEF
            points_lost = goals_conceded // 2  # Every 2 goals = -1 pt
            if points_lost > 0:
                notifications.append({
                    'id': f"goals_conceded_{player_id}_{gameweek}",
                    'notification_type': 'goals_conceded',
                    'player_name': player_name,
                    'team_name': team_name,
                    'fixture_id': None,
                    'gameweek': gameweek,
                    'old_value': 0,
                    'new_value': goals_conceded,
                    'points_change': -points_lost,
                    'message': f"🥅 **GOALS CONCEDED** -{points_lost} pts ({goals_conceded} goals)",
                    'is_read': False,
                    'timestamp': datetime.now().isoformat()
                })
        
        return notifications

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
    title="FPL Mobile Monitor API (Simplified)",
    description="Simplified API for FPL mobile monitoring and notifications",
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
    return {"status": "healthy", "service": "FPL Mobile Monitor (Simplified)"}

@app.get("/api/v1/players/search")
async def search_players(query: str, limit: int = 20):
    """Search for players"""
    try:
        # Fetch players from FPL API
        bootstrap_data = await monitoring_service.fetch_fpl_data('bootstrap-static')
        
        if not bootstrap_data:
            raise HTTPException(status_code=500, detail="Failed to fetch FPL data")
        
        players = bootstrap_data.get('elements', [])
        
        # Filter by query
        filtered_players = [
            player for player in players 
            if query.lower() in player.get('web_name', '').lower()
        ][:limit]
        
        return {"players": filtered_players}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/notifications")
async def get_notifications(limit: int = 50, offset: int = 0):
    """Get FPL notifications"""
    try:
        # Fetch current gameweek data
        bootstrap_data = await monitoring_service.fetch_fpl_data('bootstrap-static')
        if not bootstrap_data:
            raise HTTPException(status_code=500, detail="Failed to fetch FPL data")
        
        # Get current gameweek
        current_event = bootstrap_data.get('current-event', 1)
        
        # Fetch live data for current gameweek
        live_data = await monitoring_service.fetch_fpl_data(f'event/{current_event}/live')
        if not live_data:
            raise HTTPException(status_code=500, detail="Failed to fetch live data")
        
        # Generate notifications from live data
        notifications = await monitoring_service.generate_notifications_from_live_data(
            bootstrap_data, live_data, current_event
        )
        
        # Apply pagination
        paginated_notifications = notifications[offset:offset + limit]
        
        return {
            "notifications": paginated_notifications,
            "total": len(notifications),
            "current_gameweek": current_event
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        "user_timezone": monitoring_service.get_user_timezone(),
        "price_window_active": monitoring_service.is_price_update_window()
    }

@app.get("/api/v1/fpl/current-gameweek")
async def get_current_gameweek():
    """Get current FPL gameweek info"""
    try:
        bootstrap_data = await monitoring_service.fetch_fpl_data('bootstrap-static')
        
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
        "fpl_monitor_simple:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
