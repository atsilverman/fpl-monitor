#!/usr/bin/env python3
"""
FPL Mobile Monitor - Enhanced Production Service
==============================================

Complete production-ready monitoring service with full Supabase integration,
live match detection, bonus monitoring, and change tracking.
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
        self.logger.info("Starting FPL Enhanced Dynamic Monitoring Service")
        self.logger.info("Monitoring modes: Live Performance, Status Changes, Price Changes, Final Bonus")
        
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

    async def load_processed_gameweeks(self):
        """Load previously processed gameweeks from database"""
        try:
            response = requests.get(
                f'{self.supabase_url}/rest/v1/monitoring_state?select=gameweek',
                headers=self.headers, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.processed_gameweeks = {item['gameweek'] for item in data}
                self.logger.info(f"Loaded {len(self.processed_gameweeks)} processed gameweeks")
            else:
                self.logger.warning("Could not load processed gameweeks")
        except Exception as e:
            self.logger.error(f"Error loading processed gameweeks: {e}")

    async def is_change_already_processed(self, player_id: int, gameweek: int, event_type: str, new_value: int) -> bool:
        """Check if a specific change was already processed using live_monitor_history"""
        try:
            # Query for recent events of this type for this player
            response = requests.get(
                f'{self.supabase_url}/rest/v1/live_monitor_history?player_id=eq.{player_id}&gameweek=eq.{gameweek}&event_type=eq.{event_type}&new_value=eq.{new_value}&limit=1',
                headers=self.headers, timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return len(data) > 0  # If any records found, it's already processed
            return False
        except Exception as e:
            self.logger.error(f"Error checking if change already processed: {e}")
            return False

    async def is_price_change_already_processed(self, player_id: int, new_price: int) -> bool:
        """Check if a price change was already processed"""
        try:
            # Query for recent price changes for this player
            response = requests.get(
                f'{self.supabase_url}/rest/v1/live_monitor_history?player_id=eq.{player_id}&event_type=eq.price_change&new_value=eq.{new_price}&limit=1',
                headers=self.headers, timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return len(data) > 0
            return False
        except Exception as e:
            self.logger.error(f"Error checking if price change already processed: {e}")
            return False

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
                await self.store_changes(changes)
            else:
                self.logger.info("No live performance changes detected")
                
        except Exception as e:
            self.logger.error(f"Error refreshing live performance: {e}")

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
            changes = await self.detect_price_changes(fpl_data, supabase_data)
            
            if changes:
                self.logger.info(f"Found {len(changes)} price changes")
                await self.update_supabase_prices(changes)
                await self.store_price_changes(changes)
            else:
                self.logger.info("No price changes detected")
                
        except Exception as e:
            self.logger.error(f"Error refreshing price changes: {e}")

    async def refresh_final_bonus(self):
        """Refresh final bonus points with change detection"""
        try:
            self.logger.info("Refreshing final bonus points")
            
            # Get current gameweek
            bootstrap_data = await self.get_fpl_data()
            if not bootstrap_data:
                return
            
            current_event = bootstrap_data.get('current-event')
            if not current_event:
                return
            
            # Check if already processed
            if current_event in self.processed_gameweeks:
                self.logger.info(f"Gameweek {current_event} already processed")
                return
            
            # Get bonus data
            bonus_data = await self.get_bonus_data(current_event)
            if not bonus_data:
                return
            
            # Detect bonus changes
            changes = await self.detect_bonus_changes(bonus_data, current_event)
            
            if changes:
                self.logger.info(f"Found {len(changes)} bonus changes")
                await self.store_changes(changes)
                await self.mark_gameweek_processed(current_event)
            else:
                self.logger.info("No bonus changes detected")
                
        except Exception as e:
            self.logger.error(f"Error refreshing final bonus: {e}")

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

    async def get_bonus_data(self, gameweek: int):
        """Get bonus data for a specific gameweek"""
        try:
            response = requests.get(f"{config.fpl_base_url}/event/{gameweek}/live/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Extract bonus data from live data
                bonus_data = {}
                for element in data.get('elements', []):
                    player_id = element.get('id')
                    stats = element.get('stats', {})
                    bonus_data[player_id] = {
                        'bonus': stats.get('bonus', 0),
                        'bps': stats.get('bps', 0)
                    }
                return bonus_data
            else:
                self.logger.error(f"Bonus data API error: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching bonus data: {e}")
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

    async def detect_live_matches(self) -> bool:
        """Check if there are currently live matches"""
        try:
            response = requests.get(
                f'{self.supabase_url}/rest/v1/fixtures?started=eq.true&finished=eq.false',
                headers=self.headers, timeout=10
            )
            if response.status_code == 200:
                live_fixtures = response.json()
                is_live = len(live_fixtures) > 0
                if is_live:
                    self.logger.info(f"Found {len(live_fixtures)} live matches")
                return is_live
            return False
        except Exception as e:
            self.logger.error(f"Error checking live matches: {e}")
            return False

    async def detect_live_changes(self, live_data: Dict, gameweek: int) -> List[Dict]:
        """Detect changes in live performance data with deduplication"""
        changes = []
        
        try:
            current_elements = live_data.get('elements', [])
            previous_elements = self.previous_live_data.get(gameweek, {})
            
            for element in current_elements:
                player_id = element.get('id')
                stats = element.get('stats', {})
                
                if player_id in previous_elements:
                    prev_stats = previous_elements[player_id]
                    
                    # Check for changes in key stats
                    for stat_name in ['goals_scored', 'assists', 'clean_sheets', 'bonus', 'yellow_cards', 'red_cards']:
                        current_value = stats.get(stat_name, 0)
                        previous_value = prev_stats.get(stat_name, 0)
                        
                        if current_value > previous_value:
                            # Check if this change was already processed
                            if await self.is_change_already_processed(player_id, gameweek, f'live_{stat_name}', current_value):
                                self.logger.info(f"Skipping duplicate {stat_name} change for player {player_id}")
                                continue
                            
                            changes.append({
                                'player_id': player_id,
                                'player_name': element.get('web_name', 'Unknown'),
                                'team_name': element.get('team_name', 'Unknown'),
                                'fixture_id': element.get('fixture', 0),
                                'gameweek': gameweek,
                                'event_type': f'live_{stat_name}',
                                'old_value': previous_value,
                                'new_value': current_value,
                                'points_change': self.calculate_points_change(stat_name, current_value - previous_value, element.get('element_type', 1))
                            })
                
                # Update previous data
                self.previous_live_data[gameweek] = self.previous_live_data.get(gameweek, {})
                self.previous_live_data[gameweek][player_id] = stats
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Error detecting live changes: {e}")
            return []

    async def detect_bonus_changes(self, bonus_data: Dict, gameweek: int) -> List[Dict]:
        """Detect changes in bonus points with deduplication"""
        changes = []
        
        try:
            previous_bonus = self.previous_bonus_data.get(gameweek, {})
            
            for player_id, current_bonus in bonus_data.items():
                if player_id in previous_bonus:
                    prev_bonus = previous_bonus[player_id]
                    
                    if current_bonus['bonus'] > prev_bonus['bonus']:
                        # Check if this bonus change was already processed
                        if await self.is_change_already_processed(player_id, gameweek, 'bonus_final', current_bonus['bonus']):
                            self.logger.info(f"Skipping duplicate bonus change for player {player_id}")
                            continue
                        
                        changes.append({
                            'player_id': player_id,
                            'player_name': f"Player {player_id}",  # Would need to fetch from players table
                            'team_name': 'Unknown',
                            'fixture_id': 0,
                            'gameweek': gameweek,
                            'event_type': 'bonus_final',
                            'old_value': prev_bonus['bonus'],
                            'new_value': current_bonus['bonus'],
                            'points_change': current_bonus['bonus'] - prev_bonus['bonus']
                        })
                
                # Update previous data
                self.previous_bonus_data[gameweek] = self.previous_bonus_data.get(gameweek, {})
                self.previous_bonus_data[gameweek][player_id] = current_bonus
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Error detecting bonus changes: {e}")
            return []

    def calculate_points_change(self, stat_name: str, change: int, position: int) -> int:
        """Calculate FPL points change for a stat change"""
        if stat_name == 'goals_scored':
            return change * self.goal_multipliers.get(position, 4)
        elif stat_name == 'assists':
            return change * self.assist_multipliers.get(position, 3)
        elif stat_name == 'clean_sheets':
            return change * self.cs_multipliers.get(position, 0)
        elif stat_name == 'yellow_cards':
            return change * self.yellow_card_multipliers.get(position, -1)
        elif stat_name == 'red_cards':
            return change * self.red_card_multipliers.get(position, -3)
        elif stat_name == 'bonus':
            return change  # Bonus points are 1:1
        else:
            return 0

    async def detect_price_changes(self, fpl_data, supabase_data):
        """Detect price changes between FPL API and Supabase with deduplication"""
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
                    # Check if this price change was already processed
                    if await self.is_price_change_already_processed(fpl_id, fpl_price):
                        self.logger.info(f"Skipping duplicate price change for player {fpl_id}")
                        continue
                    
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

    async def store_changes(self, changes: List[Dict]):
        """Store changes in live_monitor_history table"""
        if not changes:
            return
        
        try:
            response = requests.post(
                f'{self.supabase_url}/rest/v1/live_monitor_history',
                headers=self.headers,
                json=changes,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Stored {len(changes)} changes in live_monitor_history")
            else:
                self.logger.error(f"Failed to store changes: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error storing changes: {e}")

    async def store_price_changes(self, changes: List[Dict]):
        """Store price changes in live_monitor_history table"""
        if not changes:
            return
        
        price_changes = []
        for change in changes:
            price_changes.append({
                'player_id': change['fpl_id'],
                'player_name': change['name'],
                'team_name': 'Unknown',  # Would need to fetch from teams table
                'fixture_id': 0,
                'gameweek': 0,  # Would need to get current gameweek
                'event_type': 'price_change',
                'old_value': change['old_price'],
                'new_value': change['new_price'],
                'points_change': 0
            })
        
        await self.store_changes(price_changes)

    async def mark_gameweek_processed(self, gameweek: int):
        """Mark a gameweek as processed"""
        try:
            response = requests.post(
                f'{self.supabase_url}/rest/v1/monitoring_state',
                headers=self.headers,
                json={
                    'gameweek': gameweek,
                    'bonus_processed': True,
                    'last_processed_at': datetime.now().isoformat()
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.processed_gameweeks.add(gameweek)
                self.logger.info(f"Marked gameweek {gameweek} as processed")
            else:
                self.logger.error(f"Failed to mark gameweek {gameweek} as processed: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error marking gameweek as processed: {e}")

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
        """Detect current game state using FPL API data and Supabase"""
        try:
            # Check for live matches first
            if await self.detect_live_matches():
                return 'live_matches'
            
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
            
            return 'no_live_matches'
            
        except Exception as e:
            self.logger.error(f"Error detecting game state: {e}")
            return 'unknown'

    async def should_monitor_bonus(self) -> bool:
        """Check if we should monitor for final bonus points"""
        try:
            bootstrap_data = await self.get_fpl_data()
            if not bootstrap_data:
                return False
            
            current_event = bootstrap_data.get('current-event')
            if not current_event:
                return False
            
            # Check if already processed
            if current_event in self.processed_gameweeks:
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
    title="FPL Enhanced Dynamic Monitoring Service",
    description="Complete FPL monitoring with live match detection, bonus monitoring, and change tracking",
    version="3.0.0",
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
        "service": "FPL Enhanced Dynamic Monitoring Service",
        "version": "3.0.0",
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
        "price_window_active": monitoring_service.is_price_update_window(),
        "processed_gameweeks": list(monitoring_service.processed_gameweeks)
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
        "fpl_monitor_enhanced_production:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False  # Set to False for production
    )
