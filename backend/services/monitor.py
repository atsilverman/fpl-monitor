#!/usr/bin/env python3
"""
FPL MONITOR SCRIPT
==================

This script:
1. Populates the database with fresh FPL data
2. Detects changes in performance stats and prices
3. Sends Discord notifications for changes
4. Simple, reliable data collection with change monitoring

TIMEZONE HANDLING:
- FPL API uses UK time (GMT in winter, BST in summer)
- Your location: Southern California (PST in winter, PDT in summer)
- All local time references use 'America/Los_Angeles' timezone
- This automatically handles daylight saving transitions
- Price update window: 6:00-7:00 PM Pacific Time (when FPL typically updates)
- Ownership snapshots: 9:00 PM Pacific Time daily

Usage:
    python3 monitor.py          # Start persistent monitoring
"""

# Suppress OpenSSL hash warnings by redirecting stderr
import os
import sys

# Redirect stderr to /dev/null to suppress hash warnings
stderr_fd = sys.stderr.fileno()
with open(os.devnull, 'w') as devnull:
    os.dup2(devnull.fileno(), stderr_fd)

import json
import os
import sys
import time
import requests
import psycopg2
import pytz
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

class FPLRefresh:
    def __init__(self):
        load_dotenv()  # Load environment variables
        self.db_conn = None
        self.fpl_base_url = "https://fantasy.premierleague.com/api"
        # Discord configuration
        self.webhook_url = "https://discord.com/api/webhooks/1412838792229814392/ApMUHzHi1sAKRs1UwXFFRo3xQpkj0DLd43uFt6qVbbjomoHR-j5-lT_uUCtAkqNCT6x5"
        self.bot_username = "FPL Live Monitor"
        self.min_points_change = 1
        
        # Team emoji mapping for Discord notifications
        self.team_emojis = {
            'Arsenal': '🔴',
            'Aston Villa': '🟣',
            'Bournemouth': '🔴',
            'Brentford': '🔴⚫',
            'Brighton': '🔵⚪',
            'Burnley': '🟤',
            'Chelsea': '🔵',
            'Crystal Palace': '🔴🔵',
            'Everton': '🔵',
            'Fulham': '⚪⚫',
            'Leeds': '⚪🟡',
            'Liverpool': '🔴',
            'Man City': '🔵',
            'Man Utd': '🔴',
            'Newcastle': '⚫⚪',
            'Nott\'m Forest': '🔴',
            'Sunderland': '🔴⚪',
            'Spurs': '⚪',
            'West Ham': '🔴⚪',
            'Wolves': '🟡⚫'
        }
        
        # FPL scoring multipliers
        self.goal_multipliers = {1: 10, 2: 6, 3: 5, 4: 4}  # GK, DEF, MID, FWD
        self.cs_multipliers = {1: 4, 2: 4, 3: 1, 4: 0}     # GK, DEF, MID, FWD
        
        # Mini league configuration
        self.mini_league_id = 814685  # Your mini league ID
        
        # Mini league ownership caching
        self.ownership_cache = {}  # Cache ownership data to avoid repeated API calls
        self.starting_cache = {}   # Cache starting XI data to avoid repeated API calls
        self.last_ownership_refresh = 0  # Track when ownership data was last refreshed
        
        # Temp table management
        self.temp_tables = {}  # Store temp table names for versioning
        self.temp_table_prefix = "temp_refresh_"
        # Simple diff tracking
        self.previous_state = {}  # Store previous database state for comparison
        
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
                'refresh_seconds': 300,  # 5 minutes during price windows (6:30-6:40 PM Pacific Time)
                'active_during': ['price_update_windows'],
                'priority': 'high',
                'fixture_dependent': False,
                'description': 'Player price movements (6:30-6:40 PM Pacific Time - 10 minutes only)'
            },
            'final_bonus': {
                'refresh_seconds': 3600,  # 1 hour during between matches phase
                'active_during': ['between_matches'],
                'priority': 'medium',
                'fixture_dependent': False,
                'description': 'Final bonus points from FPL API'
            }
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.last_refresh_times = {}
        self.current_game_state = 'unknown'
        self.last_ownership_snapshot = None  # Track last ownership snapshot date
        self.price_change_detected = False  # Track if price changes have been detected in current window
        self.notifications_sent_this_cycle = 0  # Track actual notifications sent
        self.price_window_notification_sent = False  # Track if we've notified about price window start
        
        # Logging setup - will be set dynamically per gameweek
        self.log_file = None
        self.setup_logging()
        
        # Define notification categories with clear rules
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
                'position_relevant': [2, 3, 4],  # DEF, MID, FWD (corrected from [2, 3])
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
        


    def get_threshold_points(self, stat_name: str, value: int, element_type: int) -> int:
        """Centralized threshold-based points calculation"""
        if stat_name == 'saves' and element_type == 1:  # GK saves
            return value // 3
        elif stat_name == 'goals_conceded' and element_type in [1, 2]:  # GK/DEF goals conceded
            return (value // 2) * -1
        elif stat_name == 'defensive_contribution':
            return self.calculate_derived_stat_points(stat_name, element_type, 0, value)
        return 0

    def get_stat_mapping(self) -> Dict[str, str]:
        """Generate stat mapping from notification categories"""
        return {
            'goals': 'goals_scored',
            'assists': 'assists',
            'clean_sheets': 'clean_sheets',
            'bonus': 'bonus',
            'red_cards': 'red_cards',
            'yellow_cards': 'yellow_cards',
            'penalties_saved': 'penalties_saved',
            'penalties_missed': 'penalties_missed',
            'own_goals': 'own_goals',
            'saves': 'saves',
            'goals_conceded': 'goals_conceded',
            'defensive_contribution': 'defensive_contribution',
            'bps': 'bps'
        }

    def compute_stat_diff(self, stat_name: str, old_value: int, new_value: int, 
                         element_type: int, minutes: int) -> Optional[Dict]:
        """Single method to compute stat diffs and notifications - eliminates redundancy"""
        if not self.should_notify_for_stat(stat_name, element_type, minutes, old_value, new_value):
            return None
            
        points_change = self.calculate_points_change_for_stat(stat_name, old_value, new_value, element_type, minutes)
        if points_change == 0:
            return None
            
        # Check minimum points change threshold
        if abs(points_change) < self.min_points_change:
            return None
            
        return {
            'stat_name': stat_name,
            'old_value': old_value,
            'new_value': new_value,
            'points_change': points_change,
            'change': new_value - old_value
        }

    def should_notify_for_stat(self, stat_name: str, element_type: int, minutes: int, 
                              old_value: int, new_value: int) -> bool:
        """Determine if we should send a notification for a stat change - now uses centralized logic"""
        if stat_name not in self.notification_categories:
            return False
            
        category = self.notification_categories[stat_name]
        
        # Check if position is relevant
        if element_type not in category['position_relevant']:
            return False
            
        # Check minutes requirement
        if minutes < category['minutes_required']:
            return False
            
        # Check if there's actually a change
        if old_value == new_value:
            return False
            
        # For threshold-based stats, only notify when crossing thresholds
        if category.get('threshold_based'):
            old_points = self.get_threshold_points(stat_name, old_value, element_type)
            new_points = self.get_threshold_points(stat_name, new_value, element_type)
            return old_points != new_points
            
        # For derived stats like defensive contribution, check if points status changes
        if category.get('derived_stat'):
            old_points = self.calculate_derived_stat_points(stat_name, element_type, minutes, old_value)
            new_points = self.calculate_derived_stat_points(stat_name, element_type, minutes, new_value)
            return old_points != new_points
            
        # For regular stats, any change is significant
        return True

    def calculate_derived_stat_points(self, stat_name: str, element_type: int, minutes: int, value: int) -> int:
        """Calculate points for derived stats like defensive contribution"""
        if stat_name == 'defensive_contribution':
            if element_type == 2:  # Defender
                return 2 if value >= 10 else 0
            elif element_type == 3:  # Midfielder
                return 2 if value >= 12 else 0
            elif element_type == 4:  # Forward
                return 2 if value >= 12 else 0
                
        return 0

    def calculate_points_change_for_stat(self, stat_name: str, old_value: int, new_value: int, 
                                       element_type: int, minutes: int) -> int:
        """Calculate FPL points change for a specific stat change - now uses centralized logic"""
        if old_value == new_value:
            return 0
            
        # Use centralized threshold logic for threshold-based stats
        if stat_name in ['saves', 'goals_conceded', 'defensive_contribution']:
            old_points = self.get_threshold_points(stat_name, old_value, element_type)
            new_points = self.get_threshold_points(stat_name, new_value, element_type)
            return new_points - old_points
        
        # Direct calculation for non-threshold stats
        if stat_name == 'goals':
            return (new_value - old_value) * self.goal_multipliers[element_type]
        elif stat_name == 'assists':
            return (new_value - old_value) * 3
        elif stat_name == 'clean_sheets':
            # FPL API already validates 60+ minutes and position eligibility
            return (new_value - old_value) * self.cs_multipliers[element_type]
        elif stat_name == 'bonus':
            return new_value - old_value
        elif stat_name == 'red_cards':
            return (new_value - old_value) * -3
        elif stat_name == 'yellow_cards':
            return (new_value - old_value) * -1
        elif stat_name == 'penalties_saved':
            return (new_value - old_value) * 5
        elif stat_name == 'penalties_missed':
            return (new_value - old_value) * -2
        elif stat_name == 'own_goals':
            return (new_value - old_value) * -2
        else:
            return 0

    def is_stat_relevant_for_position(self, stat_name: str, element_type: int) -> bool:
        """Check if a stat is relevant for a player's position (affects FPL points)"""
        if stat_name == 'goals' or stat_name == 'assists':
            return True  # All positions can score/assist
        elif stat_name == 'clean_sheets':
            return element_type in [1, 2, 3]  # GK, DEF, MID get clean sheet points (GK/DEF: +4, MID: +1)
        elif stat_name == 'goals_conceded':
            return element_type in [1, 2]  # Only GK/DEF lose points for goals conceded
        elif stat_name == 'saves':
            return element_type == 1  # Only GK get save points
        elif stat_name == 'penalties_saved':
            return element_type == 1  # Only GK get penalty save points
        elif stat_name == 'defensive_contribution':
            return element_type in [2, 3, 4]  # DEF, MID, FWD get defensive contribution points
        elif stat_name in ['bonus', 'red_cards', 'yellow_cards', 'penalties_missed', 'own_goals']:
            return True  # All positions can get these
        else:
            return False

    def is_stat_change_significant(self, stat_name: str, old_value: int, new_value: int, 
                                  element_type: int, minutes: int) -> bool:
        """Check if a stat change is significant enough to warrant a notification"""
        if old_value == new_value:
            return False
            
        # Minutes validation for certain stats
        if stat_name in ['clean_sheets'] and minutes < 60:
            return False
            
        # Threshold-based stats need special handling
        if stat_name == 'saves' and element_type == 1:  # GK saves
            # Only notify when crossing threshold boundaries
            old_threshold = old_value // 3
            new_threshold = new_value // 3
            return old_threshold != new_threshold
            
        elif stat_name == 'goals_conceded' and element_type in [1, 2]:  # GK/DEF goals conceded
            # Only notify when crossing threshold boundaries
            old_threshold = old_value // 2
            new_threshold = new_value // 2
            return old_threshold != new_threshold
            
        elif stat_name == 'defensive_contribution':
            # Only notify when the contribution status changes (0 -> 2 or 2 -> 0)
            old_contribution = self.calculate_defensive_contribution_points(element_type, minutes, old_value)
            new_contribution = self.calculate_defensive_contribution_points(element_type, minutes, new_value)
            return old_contribution != new_contribution
            
        # For other stats, any change is significant
        return True

    def calculate_defensive_contribution_points(self, element_type: int, minutes: int, 
                                              defensive_contribution: int) -> int:
        """Calculate defensive contribution points for a given value"""
        if element_type == 2:  # Defender
            return 2 if defensive_contribution >= 10 else 0
        elif element_type == 3: # Midfielder
            return 2 if defensive_contribution >= 12 else 0
        elif element_type == 4: # Forward
            return 2 if defensive_contribution >= 12 else 0

    def setup_logging(self):
        """Setup logging for change detection"""
        import os
        import csv
        
        # Create archive directory if it doesn't exist
        os.makedirs('archive', exist_ok=True)
        
        # Don't create CSV files here - will be created when first change is logged
        # This avoids calling get_current_gameweek() before database connection is established
    
    def log_change(self, change_data: dict):
        """Log a change detection to CSV with detailed information"""
        from datetime import datetime
        import csv
        import os
        
        # Get current gameweek and set log file path
        current_gw = self.get_current_gameweek()
        self.log_file = f'archive/gw{current_gw}.csv'
        
        # Create archive directory if it doesn't exist
        os.makedirs('archive', exist_ok=True)
        
        # Create CSV file with headers if it doesn't exist
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'player_name', 
                    'team_name',
                    'position',
                    'stat_category',
                    'old_value',
                    'new_value',
                    'change',
                    'points_change',
                    'notification_sent'
                ])
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract data from change object
        player_name = change_data.get('player_name', 'Unknown')
        team_name = change_data.get('team_name', 'Unknown')
        position = self.get_position_name(change_data.get('element_type', 0))
        stat_category = change_data.get('stat_name', 'unknown')
        old_value = change_data.get('old_value', '')
        new_value = change_data.get('new_value', '')
        change = change_data.get('change', 0)
        points_change = change_data.get('points_change', 0)
        notification_sent = 'Yes' if change_data.get('notification_sent', False) else 'No'
        
        # Check for duplicate bonus notifications before logging
        if change_data.get('stat_category') in ['bonus', 'bonus_final']:
            if self.is_duplicate_bonus_notification(change_data):
                return  # Skip logging this duplicate
        
        try:
            # Write to CSV file
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    player_name,
                    team_name,
                    position,
                    stat_category,
                    old_value,
                    new_value,
                    change,
                    points_change,
                    notification_sent
                ])
            
            # Also log to live_monitor_history table for bonus tracking (both live and final)
            if stat_category in ['bonus', 'bonus_final']:
                try:
                    with self.db_conn.cursor() as cur:
                        # For regular bonus events, we need the player_id
                        if stat_category == 'bonus':
                            # Get player_id from fpl_id
                            cur.execute("SELECT id FROM players WHERE fpl_id = %s", (change_data.get('fpl_id'),))
                            player_result = cur.fetchone()
                            player_id = player_result[0] if player_result else None
                        else:
                            # For bonus_final, no specific player
                            player_id = None
                        
                        cur.execute("""
                            INSERT INTO live_monitor_history (
                                player_id, player_name, team_name, fixture_id, gameweek, 
                                event_type, old_value, new_value, points_change
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            player_id,
                            player_name,
                            team_name,
                            change_data.get('fixture_id'),
                            self.get_current_gameweek(),
                            stat_category,
                            old_value,
                            new_value,
                            points_change
                        ))
                        self.db_conn.commit()
                except Exception as e:
                    pass  # Silent error handling
                    
        except Exception as e:
            pass  # Silent error handling
    
    def should_capture_ownership_snapshot(self) -> bool:
        """Check if we should capture ownership snapshot (daily at 9:00 PM Pacific Time)"""
        from datetime import datetime, timezone
        import pytz
        
        # Get current time in Pacific Time (automatically handles PST/PDT)
        utc_now = datetime.now(timezone.utc)
        pacific_time = utc_now.astimezone(pytz.timezone('America/Los_Angeles'))
        
        # Check if it's 9:00 PM Pacific Time (21:00)
        if pacific_time.hour == 21 and pacific_time.minute < 5:  # Within 5 minutes of 9:00 PM
            # Check if we haven't already captured today
            today = pacific_time.date()
            if self.last_ownership_snapshot != today:
                return True
        
        return False
    
    def capture_ownership_snapshot(self):
        """Capture daily ownership snapshot and send summary notifications"""
        from datetime import datetime, timezone
        import pytz
        

        
        try:
            # Get current time in Pacific Time (automatically handles PST/PDT)
            utc_now = datetime.now(timezone.utc)
            pacific_time = utc_now.astimezone(pytz.timezone('America/Los_Angeles'))
            today = pacific_time.date()
            
            # Capture current ownership data
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO player_history (
                        fpl_id, snapshot_date, snapshot_window, snapshot_timestamp,
                        now_cost, selected_by_percent, status, news
                    )
                    SELECT 
                        p.fpl_id, %s, 'daily_9pm_pdt', %s,
                        p.now_cost / 10, p.selected_by_percent, p.status, p.news
                    FROM players p
                    ON CONFLICT (fpl_id, snapshot_date, snapshot_window) DO NOTHING
                """, (today, pacific_time))
                
                self.db_conn.commit()
        
            
            # Send ownership change notifications
            self.send_ownership_summary_notifications()
            
            # Update last snapshot date
            self.last_ownership_snapshot = today
            
        except Exception as e:
            self.db_conn.rollback()
    
    def send_ownership_summary_notifications(self):
        """Send Discord notifications for top 10 ownership increases and decreases"""
        try:
            # Get ownership changes since last snapshot
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    WITH current_ownership AS (
                        SELECT fpl_id, selected_by_percent, web_name, t.short_name as team_name
                        FROM players p
                        JOIN teams t ON p.team_id = t.id
                    ),
                    previous_ownership AS (
                        SELECT fpl_id, selected_by_percent
                        FROM player_history ph
                        WHERE snapshot_window = 'daily_9pm_pdt'
                        AND snapshot_date = (
                            SELECT MAX(snapshot_date) 
                            FROM player_history 
                            WHERE snapshot_window = 'daily_9pm_pdt'
                            AND snapshot_date < CURRENT_DATE
                        )
                    )
                    SELECT 
                        c.web_name,
                        c.team_name,
                        c.selected_by_percent as current_ownership,
                        COALESCE(p.selected_by_percent, 0) as previous_ownership,
                        (c.selected_by_percent - COALESCE(p.selected_by_percent, 0)) as ownership_change
                    FROM current_ownership c
                    LEFT JOIN previous_ownership p ON c.fpl_id = p.fpl_id
                    WHERE p.selected_by_percent IS NOT NULL
                    ORDER BY ABS(c.selected_by_percent - p.selected_by_percent) DESC
                    LIMIT 20
                """)
                
                changes = cur.fetchall()
            
            if not changes:
                print("ℹ️ No ownership changes to report")
                return
            
            # Separate increases and decreases
            increases = [c for c in changes if c[4] > 0]  # ownership_change > 0
            decreases = [c for c in changes if c[4] < 0]  # ownership_change < 0
            
            # Send top 10 increases
            if increases:
                message = "📈 **TOP 10 OWNERSHIP INCREASES (Day over Day)**\n"
                for i, (web_name, team_name, current, previous, change) in enumerate(increases[:10], 1):
                    message += f"{i}. {web_name} ({team_name}) +{change:.1f}%\n"
                
                self.send_discord_notification(message, "FPL")  # Use generic badge for summary
            
            # Send top 10 decreases
            if decreases:
                message = "📉 **TOP 10 OWNERSHIP DECREASES (Day over Day)**\n"
                for i, (web_name, team_name, current, previous, change) in enumerate(decreases[:10], 1):
                    message += f"{i}. {web_name} ({team_name}) {change:.1f}%\n"
                
                self.send_discord_notification(message, "FPL")  # Use generic badge for summary
                
        except Exception as e:
            pass  # Silent error handling
    
    def get_position_name(self, element_type: int) -> str:
        """Convert element type to position name"""
        position_map = {
            1: 'GK',
            2: 'DEF', 
            3: 'MID',
            4: 'FWD'
        }
        return position_map.get(element_type, 'Unknown')

    def is_price_update_window(self) -> bool:
        """Check if current time is within FPL price update window (6:30-6:40 PM Pacific Time)"""
        from datetime import datetime, timezone
        import pytz
        
        # Get current time in Pacific Time (automatically handles PST/PDT)
        utc_now = datetime.now(timezone.utc)
        pacific_time = utc_now.astimezone(pytz.timezone('America/Los_Angeles'))
        
        # FPL price changes happen around 6:30 PM Pacific Time, monitor for 10 minutes only
        hour = pacific_time.hour
        minute = pacific_time.minute
        
        # Check if within the 6:30-6:40 PM Pacific Time window (10 minutes only)
        is_window = (hour == 18 and minute >= 30) and (hour == 18 and minute < 40)
        
        return is_window

    def detect_game_state(self) -> str:
        """Detect current game state using intelligent fixture monitoring"""
        try:
            # Ensure database connection
            if not self.db_conn:
                self.connect_db()
            
            current_time = int(time.time())
            
            with self.db_conn.cursor() as cur:
                # Check for currently live matches - use finished attribute, not minutes
                # Matches can go beyond 90 minutes (stoppage time, extra time, penalties)
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM fixtures 
                    WHERE started = TRUE 
                    AND finished = FALSE
                """)
                live_fixtures = cur.fetchone()[0]
                
                # Debug logging for live match detection
                if live_fixtures > 0:
                    cur.execute("""
                        SELECT f.id, th.short_name as home, ta.short_name as away, f.started, f.finished, f.minutes
                        FROM fixtures f 
                        JOIN teams th ON f.team_h = th.id 
                        JOIN teams ta ON f.team_a = ta.id
                        WHERE f.started = TRUE 
                        AND f.finished = FALSE
                    """)
                    live_details = cur.fetchall()
                    for fixture in live_details:
                        pass  # Silent processing
                
                if live_fixtures >= 1:
                    return 'live_matches'
                
                # Check for upcoming matches within the next 15 minutes
                # This prevents gaps between early morning fixtures
                upcoming_window = current_time + (15 * 60)  # 15 minutes ahead
                
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM fixtures 
                    WHERE kickoff_time IS NOT NULL 
                    AND EXTRACT(EPOCH FROM kickoff_time) BETWEEN %s AND %s
                    AND started = FALSE AND finished = FALSE
                """, (current_time, upcoming_window))
                
                upcoming_fixtures = cur.fetchone()[0]
                
                if upcoming_fixtures >= 1:
                    return 'upcoming_matches'
                
                # Check for price update windows
                elif self.is_price_update_window():
                    from datetime import datetime, timezone
                    import pytz
                    utc_now = datetime.now(timezone.utc)
                    pacific_time = utc_now.astimezone(pytz.timezone('America/Los_Angeles'))

                    
                    # Send Discord notification when price window starts
                    if not self.price_window_notification_sent:
                        price_start_message = f"💰 **FPL PRICE UPDATE WINDOW STARTED**\n\n⏰ **Current Time**: {pacific_time.strftime('%I:%M %p')} Pacific Time\n🔄 **Switching to 5-minute refresh rate**\n\n📊 **Monitoring for price changes** - Will notify on any player price movements"
                        self.send_discord_notification(price_start_message, "FPL")
                        self.price_window_notification_sent = True
                    
                    return 'price_update_windows'
                else:
                    # Reset price window notification flag when not in price window
                    if self.price_window_notification_sent:
                        from datetime import datetime, timezone
                        import pytz
                        utc_now = datetime.now(timezone.utc)
                        pacific_time = utc_now.astimezone(pytz.timezone('America/Los_Angeles'))
                        price_end_message = f"💰 **FPL PRICE UPDATE WINDOW ENDED**\n\n⏰ **Current Time**: {pacific_time.strftime('%I:%M %p')} Pacific Time\n🔄 **Switching back to normal refresh rate**\n\n📊 **Price monitoring deactivated**"
                        self.send_discord_notification(price_end_message, "FPL")
                        self.price_window_notification_sent = False
                    
                    return 'no_live_matches'
                
        except Exception as e:
            return 'unknown'

    def check_and_notify_new_fixture_starts(self):
        """Check for newly started fixtures and send start notifications with mini league start percentages"""
        try:
            with self.db_conn.cursor() as cur:
                # Find fixtures that just started (started = TRUE but we haven't notified about them yet)
                cur.execute("""
                    SELECT f.id, f.kickoff_time, th.short_name as home_team, ta.short_name as away_team,
                           f.team_h, f.team_a, th.name as home_team_full
                    FROM fixtures f 
                    JOIN teams th ON f.team_h = th.id 
                    JOIN teams ta ON f.team_a = ta.id
                    WHERE f.started = TRUE 
                    AND f.finished = FALSE
                    AND f.id NOT IN (
                        SELECT fixture_id FROM live_monitor_history 
                        WHERE event_type = 'fixture_started'
                    )
                    AND f.kickoff_time > NOW() - INTERVAL '5 minutes'  -- Only recent starts
                    ORDER BY f.kickoff_time DESC
                """)
                
                new_starts = cur.fetchall()
                
                for fixture in new_starts:
                    fixture_id, kickoff_time, home_team, away_team, team_h_id, team_a_id, home_team_full = fixture
                    
                    # Get mini league start percentages for players in this fixture
                    home_start_percent = self.get_team_mini_league_start_percentage(team_h_id)
                    away_start_percent = self.get_team_mini_league_start_percentage(team_a_id)
                    
                    # Convert kickoff time to local time (Pacific)
                    if kickoff_time:
                        from datetime import datetime, timezone
                        import pytz
                        
                        # Parse the kickoff time and convert to Pacific
                        if isinstance(kickoff_time, str):
                            if kickoff_time.endswith('Z'):
                                utc_time = datetime.fromisoformat(kickoff_time[:-1]).replace(tzinfo=timezone.utc)
                            else:
                                utc_time = datetime.fromisoformat(kickoff_time).replace(tzinfo=timezone.utc)
                        else:
                            utc_time = kickoff_time.replace(tzinfo=timezone.utc)
                        
                        pacific_time = utc_time.astimezone(pytz.timezone('America/Los_Angeles'))
                        local_time_str = pacific_time.strftime('%I:%M %p')
                    else:
                        local_time_str = "Unknown"
                    
                    # Create concise notification message
                    message = f"⚽ **{home_team} (H) vs {away_team}**\n\n"
                    message += f"⏰ **Kickoff**: {local_time_str} Pacific\n\n"
                    message += f"👥 **Mini League Start %**:\n"
                    message += f"🔴 **{home_team}**: {home_start_percent:.1f}%\n"
                    message += f"🔵 **{away_team}**: {away_start_percent:.1f}%"
                    
                    # Send notification
                    self.send_discord_notification(message, "FPL")
                    
                    # Record that we've notified about this fixture start
                    self.record_fixture_start_notification(fixture_id)
                    
        except Exception as e:
            # Silent error handling - don't break monitoring for notification issues
            pass

    def get_team_mini_league_start_percentage(self, team_id: int) -> float:
        """Get the average mini league start percentage for a team's players"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT AVG(COALESCE(p.selected_by_percent, 0)) as avg_start_percent
                    FROM players p
                    WHERE p.team_id = %s
                    AND p.selected_by_percent IS NOT NULL
                """, (team_id,))
                
                result = cur.fetchone()
                return result[0] if result and result[0] else 0.0
                
        except Exception as e:
            return 0.0

    def record_fixture_start_notification(self, fixture_id: int):
        """Record that we've sent a start notification for a fixture to avoid duplicates"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO live_monitor_history 
                    (fixture_id, gameweek, event_type, created_at)
                    VALUES (%s, (SELECT event_id FROM fixtures WHERE id = %s), 'fixture_started', NOW())
                """, (fixture_id, fixture_id))
                
        except Exception as e:
            # Silent error handling
            pass



    def check_fixture_data_consistency(self):
        """Check for and log inconsistent fixture data to help debug issues"""
        try:
            with self.db_conn.cursor() as cur:
                # Find fixtures with inconsistent data
                cur.execute("""
                    SELECT f.id, f.event_id, th.short_name as home, ta.short_name as away, 
                           f.started, f.finished, f.minutes, f.kickoff_time
                    FROM fixtures f 
                    JOIN teams th ON f.team_h = th.id 
                    JOIN teams ta ON f.team_a = ta.id
                    WHERE (
                        -- Started but kickoff is in the future (using UTC comparison)
                        (f.started = TRUE AND f.kickoff_time > NOW() AT TIME ZONE 'UTC')
                        OR
                        -- Finished but minutes < 90 (should be at least 90 for completed matches)
                        (f.finished = TRUE AND f.minutes < 90)
                        OR
                        -- Started but minutes = 0 (should have some minutes if started)
                        (f.started = TRUE AND f.finished = FALSE AND f.minutes = 0 AND f.kickoff_time <= NOW() AT TIME ZONE 'UTC')
                    )
                    AND f.kickoff_time > NOW() AT TIME ZONE 'UTC' - INTERVAL '24 hours'  -- Only check recent fixtures
                    ORDER BY f.kickoff_time DESC
                """)
                
                inconsistent_fixtures = cur.fetchall()
                
                if inconsistent_fixtures:
                    for fixture in inconsistent_fixtures:
                        (fixture_id, event_id, home, away, started, finished, minutes, 
                         kickoff_time) = fixture
                        
                        issues = []
                        if started and kickoff_time > datetime.now():
                            issues.append("STARTED but kickoff in FUTURE")
                        if finished and minutes < 90:
                            issues.append("FINISHED but minutes < 90")
                        if started and not finished and minutes == 0 and kickoff_time <= datetime.now():
                            issues.append("STARTED but minutes = 0")
                
                return len(inconsistent_fixtures) > 0
                
        except Exception as e:
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
            # If we've already detected price changes in this window, don't monitor anymore
            if category_name == 'price_changes' and self.price_change_detected:
                return False
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

    def start_monitoring(self):
        """Start the dynamic monitoring system"""
        self.monitoring_active = True
        
        # Establish persistent database connection for monitoring
        self.connect_db()
        
        # Initialize mini league ownership data
        self.refresh_mini_league_ownership()
        
        # Initialize refresh times to current time to prevent immediate refreshes
        current_time = int(time.time())
        for category_name in self.monitoring_config:
            self.last_refresh_times[category_name] = current_time
        
        try:
            while self.monitoring_active:
                try:
                    # Determine what needs refreshing
                    current_time = int(time.time())
                    categories_to_refresh = []
                    
                    for category_name in self.monitoring_config:
                        should_monitor = self.should_monitor_category(category_name)
                        if should_monitor:
                            next_refresh = self.get_next_refresh_time(category_name)
                            if current_time >= next_refresh:
                                categories_to_refresh.append(category_name)
                    
                    # Refresh active categories FIRST (including fixtures)
                    if categories_to_refresh:
                        self.refresh_categories_persistent(categories_to_refresh)
                        
                        # Update refresh times
                        for category_name in categories_to_refresh:
                            self.last_refresh_times[category_name] = current_time
                    
                    # Passively refresh fixtures every 15 minutes to catch new kickoff times
                    # This ensures we don't miss early morning fixtures or timing changes
                    if not hasattr(self, 'last_fixture_refresh') or (current_time - getattr(self, 'last_fixture_refresh', 0)) >= 900:  # 15 minutes
                        try:
                            self.populate_fixtures()
                            self.last_fixture_refresh = current_time
                        except Exception as e:
                            # If fixture refresh fails, continue monitoring
                            pass
                    
                    # NOW detect current game state AFTER refreshing fixtures
                    previous_game_state = self.current_game_state
                    self.current_game_state = self.detect_game_state()
                    
                    # Check for data consistency issues and log them
                    self.check_fixture_data_consistency()
                    
                    # If we're in live matches, refresh fixtures every cycle for accurate minutes
                    if self.current_game_state == 'live_matches':
                        try:
                            self.populate_fixtures()
                        except Exception as e:
                            pass  # Silent error handling
                    
                    # Log state transitions for debugging and send Discord notifications
                    if previous_game_state != self.current_game_state:
                        if self.current_game_state == 'upcoming_matches':
                            # Send Discord notification for upcoming matches
                            state_message = f"🔄 **FPL Monitor State Change**\n\n**{previous_game_state.upper()}** → **{self.current_game_state.upper()}**\n\n🎯 **Fixtures starting soon** - Switching to 2-minute refresh rate"
                            self.send_discord_notification(state_message, "FPL")
                        elif self.current_game_state == 'live_matches':
                            # Send Discord notification for live matches
                            state_message = f"🔄 **FPL Monitor State Change**\n\n**{previous_game_state.upper()}** → **{self.current_game_state.upper()}**\n\n⚽ **Matches are now LIVE** - Switching to 1-minute refresh rate"
                            self.send_discord_notification(state_message, "FPL")
                        elif self.current_game_state == 'price_update_windows':
                            # Send Discord notification for price update windows
                            state_message = f"🔄 **FPL Monitor State Change**\n\n**{previous_game_state.upper()}** → **{self.current_game_state.upper()}**\n\n💰 **Price update window active** - Switching to 5-minute refresh rate"
                            self.send_discord_notification(state_message, "FPL")
                        else:
                            # Send Discord notification for other state changes (no_live_matches, etc.)
                            state_message = f"🔄 **FPL Monitor State Change**\n\n**{previous_game_state.upper()}** → **{self.current_game_state.upper()}**\n\n⏰ **Switching to 1-hour refresh rate**"
                            self.send_discord_notification(state_message, "FPL")
                    
                    # Reset price change flag when exiting price window
                    if previous_game_state == 'price_update_windows' and self.current_game_state != 'price_update_windows':
                        self.price_change_detected = False
                    
                    # Calculate sleep time and display status
                    sleep_time = self.calculate_sleep_time()
                    
                    # Determine refresh rate for display
                    if 'price_changes' in categories_to_refresh or (self.current_game_state == 'price_update_windows' and not self.price_change_detected):
                        refresh_rate = "5min"
                    elif self.current_game_state == 'live_matches':
                        refresh_rate = "1min"  # Actual refresh rate from config
                    elif self.current_game_state == 'upcoming_matches':
                        refresh_rate = "2min"  # More frequent when matches are about to start
                    else:
                        refresh_rate = "1hour"
                    
                    # Display single-line status with timestamp
                    notifications_count = self.notifications_sent_this_cycle
                    current_time = datetime.now().strftime('%H:%M:%S')
                    print(f"🎮 {current_time} | {self.current_game_state} | {refresh_rate} | {notifications_count} notifications | Sleep: {sleep_time}s")
                    
                    # Reset notification counter for next cycle
                    self.notifications_sent_this_cycle = 0
                    
                    time.sleep(sleep_time)
                    
                except KeyboardInterrupt:
                    if self.confirm_shutdown():
                        self.monitoring_active = False
                except Exception as e:
                    time.sleep(60)  # Wait before retrying
        finally:
            print()  # Add newline for clean terminal output
            self.close_db()

    def calculate_sleep_time(self) -> int:
        """Calculate optimal sleep time based on next refresh needs and upcoming fixtures"""
        current_time = int(time.time())
        next_refresh_times = []
        
        # Check for upcoming fixtures that might need monitoring
        try:
            with self.db_conn.cursor() as cur:
                # Look for fixtures starting in the next 30 minutes
                upcoming_window = current_time + (30 * 60)  # 30 minutes ahead
                cur.execute("""
                    SELECT EXTRACT(EPOCH FROM kickoff_time) - %s as seconds_until_kickoff
                    FROM fixtures 
                    WHERE kickoff_time IS NOT NULL 
                    AND EXTRACT(EPOCH FROM kickoff_time) BETWEEN %s AND %s
                    AND started = FALSE AND finished = FALSE
                    ORDER BY kickoff_time
                    LIMIT 1
                """, (current_time, current_time, upcoming_window))
                
                result = cur.fetchone()
                if result and result[0] > 0:
                    # Wake up 2 minutes before kickoff to start monitoring
                    wake_up_time = max(60, result[0] - 120)  # At least 1 minute, but 2 min before kickoff
                    next_refresh_times.append(wake_up_time)
        except Exception as e:
            # If fixture check fails, continue with normal refresh timing
            pass
        
        # Add normal refresh timing
        for category_name in self.monitoring_config:
            if self.should_monitor_category(category_name):
                next_refresh = self.get_next_refresh_time(category_name)
                if next_refresh > current_time:
                    next_refresh_times.append(next_refresh - current_time)
        
        if not next_refresh_times:
            return 60  # Default to 1 minute if no active monitoring
        
        # Sleep until next refresh is needed or fixture is about to start
        return min(next_refresh_times)

    def refresh_categories(self, categories: List[str]):
        """Refresh specific monitoring categories"""
        
        # Connect to database
        self.connect_db()
        
        try:
            # Create temp versions for change detection
            self.initialize_temp_tables()
            
            # Refresh based on category needs
            if 'live_performance' in categories:
                self.populate_fixtures()  # Refresh fixtures to detect live matches
                self.populate_gameweek_stats()
            
            if 'status_changes' in categories or 'price_changes' in categories:
                self.populate_players()
            
            # Detect and process changes
            self.detect_and_process_changes()
            
        finally:
            self.close_db()

    def refresh_categories_persistent(self, categories: List[str]):
        """Refresh specific monitoring categories with persistent database connection"""
        
        # Refresh based on category needs
        if 'live_performance' in categories:
            self.populate_fixtures()  # Refresh fixtures to detect live matches
            self.populate_gameweek_stats()
        
        if 'status_changes' in categories or 'price_changes' in categories:
            self.populate_players()
        
        # Detect and process changes using comprehensive diff detection
        self.detect_and_process_changes_comprehensive()

    def detect_and_process_changes(self):
        """Detect and process changes using temp table versioning"""
        
        all_changes = []
        
        # Compute diffs for each table
        for table_name, temp_table in self.temp_tables.items():
            table_changes = self.compute_diffs_against_version(temp_table, table_name)
            all_changes.extend(table_changes)
        
        # Process all detected changes
        if all_changes:
            self.process_changes(all_changes)

    def detect_and_process_changes_comprehensive(self):
        """Detect and process changes using comprehensive detection for monitoring"""
        
        all_changes = []
        
        # 1. Get current gameweek stats (performance stats)
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT gs.player_id, gs.fixture_id, gs.bps, gs.goals_scored, gs.assists, gs.clean_sheets, gs.bonus,
                       gs.red_cards, gs.yellow_cards, gs.penalties_saved, gs.penalties_missed,
                       gs.own_goals, gs.saves, gs.goals_conceded, gs.defensive_contribution,
                       p.fpl_id, p.web_name, p.element_type, p.team_id
                FROM gameweek_stats gs 
                JOIN players p ON gs.player_id = p.id
                WHERE gs.gameweek = (SELECT id FROM gameweeks WHERE is_current = TRUE)
                AND gs.minutes > 0
            """)
            
            current_data = cur.fetchall()
        
        # 2. Validate previous state integrity before processing
        self.validate_previous_state_integrity()
        
        # 3. Compare with previous state and build new state
        changes = []
        new_state = {}
        
        for row in current_data:
            (player_id, fixture_id, bps, goals, assists, clean_sheets, bonus, red_cards, yellow_cards, 
             penalties_saved, penalties_missed, own_goals, saves, goals_conceded, 
             defensive_contribution, fpl_id, web_name, element_type, team_id) = row
            
            key = f"player_{fpl_id}"
            
            # Build current state for this player
            current_player_state = {
                'goals': goals,
                'assists': assists,
                'clean_sheets': clean_sheets,
                'bonus': bonus,
                'bps': bps,
                'red_cards': red_cards,
                'yellow_cards': yellow_cards,
                'penalties_saved': penalties_saved,
                'penalties_missed': penalties_missed,
                'own_goals': own_goals,
                'saves': saves,
                'goals_conceded': goals_conceded,
                'defensive_contribution': defensive_contribution
            }
            
            # Store in new state
            new_state[key] = current_player_state
            
            # Compare with previous state if it exists
            if key in self.previous_state:
                prev = self.previous_state[key]
                
                # Check for BPS changes to calculate bonus points
                if bps != prev.get('bps', 0):
                    bps_changes = self.detect_bps_bonus_changes(fpl_id, bps, prev.get('bps', 0), fixture_id)
                    if bps_changes:
                        changes.extend(bps_changes)
                
                # Check for stat changes
                stats_to_check = [
                    ('goals', goals, prev.get('goals', 0)),
                    ('assists', assists, prev.get('assists', 0)),
                    ('clean_sheets', clean_sheets, prev.get('clean_sheets', 0)),
                    ('red_cards', red_cards, prev.get('red_cards', 0)),
                    ('yellow_cards', yellow_cards, prev.get('yellow_cards', 0)),
                    ('penalties_saved', penalties_saved, prev.get('penalties_saved', 0)),
                    ('penalties_missed', penalties_missed, prev.get('penalties_missed', 0)),
                    ('own_goals', own_goals, prev.get('own_goals', 0)),
                    ('saves', saves, prev.get('saves', 0)),
                    ('goals_conceded', goals_conceded, prev.get('goals_conceded', 0)),
                    ('defensive_contribution', defensive_contribution, prev.get('defensive_contribution', 0))
                ]
                
                for stat_name, new_val, old_val in stats_to_check:
                    if new_val != old_val:
                        # Check if this stat is relevant for this player's position
                        if not self.is_stat_relevant_for_position(stat_name, element_type):
                            continue
                        
                        # Special handling for threshold-based stats
                        if stat_name == 'defensive_contribution':
                            old_points = self.calculate_derived_stat_points(stat_name, element_type, 90, old_val)
                            new_points = self.calculate_derived_stat_points(stat_name, element_type, 90, new_val)
                            if old_points == new_points:
                                continue
                        elif stat_name == 'saves' and element_type == 1:  # GK saves
                            old_points = old_val // 3
                            new_points = new_val // 3
                            if old_points == new_points:
                                continue
                        elif stat_name == 'goals_conceded':
                            old_points = (old_val // 2) * -1
                            new_points = (new_val // 2) * -1
                            if old_points == new_points:
                                continue
                        
                        # Calculate points change for this stat
                        points_change = self.calculate_points_change_for_stat(stat_name, old_val, new_val, element_type, 90)
                        
                        changes.append({
                            'type': 'performance',
                            'fpl_id': fpl_id,
                            'stat_name': stat_name,
                            'db_column': stat_name,
                            'old_value': old_val,
                            'new_value': new_val,
                            'change': new_val - old_val,
                            'points_change': points_change,
                            'element_type': element_type,
                            'minutes': 90,
                            'web_name': web_name,
                            'team_id': team_id,
                            'player_name': web_name,
                            'team_name': self.get_team_short_name(team_id)
                        })
        
        # 3. Update previous state with new state (this preserves state between runs)
        self.previous_state.update(new_state)
        
        all_changes.extend(changes)
        
        
        # 4. Check for live BPS changes and bonus point updates
        live_bps_changes = self.detect_live_bps_changes()
        all_changes.extend(live_bps_changes)
        
        # 5. Check for final bonus changes (FPL API population)
        final_bonus_changes = self.detect_final_bonus_changes()
        all_changes.extend(final_bonus_changes)
        
        # 6. Clean up old final bonus notifications
        self.cleanup_old_final_bonus_notifications()
        
        # 6. Check for price changes
        price_changes = self.detect_price_changes_simple()
        all_changes.extend(price_changes)
        
        # 7. Check for other player changes
        player_changes = self.detect_player_changes_simple()
        all_changes.extend(player_changes)
        
        # 6. Process all detected changes
        if all_changes:
            self.process_changes(all_changes)

    def detect_price_changes_simple(self):
        """Detect price changes using simple state comparison"""
        changes = []
        total_players = 0
        players_with_previous_state = 0
        price_changes_found = 0
        
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT p.fpl_id, p.now_cost, p.web_name, p.element_type, t.short_name as team_name
                FROM players p
                JOIN teams t ON p.team_id = t.id
            """)
            
            current_players = cur.fetchall()
            total_players = len(current_players)
        
        for row in current_players:
            fpl_id, now_cost, web_name, element_type, team_name = row
            key = f"player_price_{fpl_id}"
            
            if key in self.previous_state:
                players_with_previous_state += 1
                old_cost = self.previous_state[key]['now_cost']
                
                # Convert to float for comparison (FPL stores as pence)
                old_cost_float = float(old_cost) / 10 if old_cost else 0
                now_cost_float = float(now_cost) / 10 if now_cost else 0
                
                if old_cost_float != now_cost_float:
                    price_changes_found += 1
                    
                    # Mark that we've detected price changes in this window
                    self.price_change_detected = True
                    
                    changes.append({
                        'type': 'price',
                        'fpl_id': fpl_id,
                        'stat_name': 'now_cost',
                        'old_value': old_cost_float,
                        'new_value': now_cost_float,
                        'change': now_cost_float - old_cost_float,
                        'player_name': web_name,
                        'team_name': team_name
                    })
            # Update previous state
            if key not in self.previous_state:
                self.previous_state[key] = {}
            self.previous_state[key]['now_cost'] = now_cost
        
        return changes

    def detect_player_changes_simple(self):
        """Detect form, selection, and status changes using simple state comparison"""
        changes = []
        
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT p.fpl_id, p.form, p.selected_by_percent, p.status, p.web_name, t.short_name as team_name
                FROM players p
                JOIN teams t ON p.team_id = t.id
            """)
            
            current_players = cur.fetchall()
        
        for row in current_players:
            fpl_id, form, selected_by_percent, status, web_name, team_name = row
            key = f"player_other_{fpl_id}"
            
            if key in self.previous_state:
                prev = self.previous_state[key]
                
                # Note: form and selected_by_percent are refreshed but not monitored for notifications
                # They can be added back to monitoring later if needed
                
                # Check status changes
                if prev.get('status') != status:
                    changes.append({
                        'type': 'status',
                        'fpl_id': fpl_id,
                        'stat_name': 'status',
                        'old_value': prev.get('status', ''),
                        'new_value': status,
                        'change': 0,
                        'player_name': web_name,
                        'team_name': team_name
                    })
            
            # Update previous state
            if key not in self.previous_state:
                self.previous_state[key] = {}
            self.previous_state[key].update({
                'form': form,
                'selected_by_percent': selected_by_percent,
                'status': status
            })
        
        return changes

    def initialize_previous_state(self):
        """Initialize previous state with current database values on first run"""
        price_entries = 0
        other_entries = 0
        
        with self.db_conn.cursor() as cur:
            # Load current prices
            cur.execute("""
                SELECT p.fpl_id, p.now_cost, p.web_name, p.element_type, t.short_name as team_name
                FROM players p
                JOIN teams t ON p.team_id = t.id
            """)
            
            current_players = cur.fetchall()
        
        for i, row in enumerate(current_players):
            fpl_id, now_cost, web_name, element_type, team_name = row
            price_key = f"player_price_{fpl_id}"
            other_key = f"player_other_{fpl_id}"
            
            # Initialize price state
            if price_key not in self.previous_state:
                self.previous_state[price_key] = {}
            self.previous_state[price_key]['now_cost'] = now_cost
            price_entries += 1
            
            # Initialize other state
            if other_key not in self.previous_state:
                self.previous_state[other_key] = {}
            
            # Get other player data in a separate query to avoid cursor conflicts
            with self.db_conn.cursor() as other_cur:
                other_cur.execute("""
                    SELECT form, selected_by_percent, status
                    FROM players WHERE fpl_id = %s
                """, (fpl_id,))
                
                other_data = other_cur.fetchone()
                if other_data:
                    form, selected_by_percent, status = other_data
                    self.previous_state[other_key].update({
                        'form': form,
                        'selected_by_percent': selected_by_percent,
                        'status': status
                    })
                    other_entries += 1
        
        # Initialize gameweek stats state for BPS tracking
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT gs.player_id, gs.fixture_id, gs.bps, gs.goals_scored, gs.assists, 
                       gs.clean_sheets, gs.bonus, gs.red_cards, gs.yellow_cards,
                       gs.penalties_saved, gs.penalties_missed, gs.own_goals,
                       gs.saves, gs.goals_conceded, gs.defensive_contribution
                FROM gameweek_stats gs
                WHERE gs.bps IS NOT NULL
            """)
            
            current_stats = cur.fetchall()
        
        gameweek_entries = 0
        for row in current_stats:
            player_id, fixture_id, bps, goals_scored, assists, clean_sheets, bonus, red_cards, yellow_cards, penalties_saved, penalties_missed, own_goals, saves, goals_conceded, defensive_contribution = row
            
            # Get the fpl_id for this player
            with self.db_conn.cursor() as fpl_cur:
                fpl_cur.execute("SELECT fpl_id FROM players WHERE id = %s", (player_id,))
                fpl_result = fpl_cur.fetchone()
                if fpl_result:
                    fpl_id = fpl_result[0]
                    key = f"player_{fpl_id}"
                    
                    if key not in self.previous_state:
                        self.previous_state[key] = {}
                    
                    self.previous_state[key].update({
                        'goals': goals_scored,
                        'assists': assists,
                        'clean_sheets': clean_sheets,
                        'bonus': bonus,
                        'bps': bps,
                        'red_cards': red_cards,
                        'yellow_cards': yellow_cards,
                        'penalties_saved': penalties_saved,
                        'penalties_missed': penalties_missed,
                        'own_goals': own_goals,
                        'saves': saves,
                        'goals_conceded': goals_conceded,
                        'defensive_contribution': defensive_contribution
                    })
                    gameweek_entries += 1
        


    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False

    def test_diff_detection(self):
        """Test diff detection without API refresh (for manual changes)"""
        
        try:
            # Connect to database
            self.connect_db()
            
            # Clear any existing temp tables
            self.temp_tables = {}
            
            # Create fresh temp versions for change detection
            self.initialize_temp_tables()
            self.create_temp_version('gameweek_stats')
            self.create_temp_version('players')
            
        except Exception as e:
            pass  # Silent error handling
        finally:
            self.close_db()

    def test_diff_detection_detect(self):
        """Detect changes against previously created temp tables"""
        
        try:
            # Connect to database
            self.connect_db()
            
            # Initialize temp tables (should already exist)
            self.initialize_temp_tables()
            
            # Detect and process changes
            self.detect_and_process_changes()
            
            # Clean up temp tables
            for temp_table in self.temp_tables.values():
                self.drop_temp_version(temp_table)
            
        except Exception as e:
            pass  # Silent error handling
        finally:
            self.close_db()

    def create_temp_version(self, table_name: str) -> str:
        """Create or reuse temporary table for versioning"""
        if table_name in self.temp_tables:
            temp_name = self.temp_tables[table_name]
        else:
            temp_name = f"{self.temp_table_prefix}{table_name}_{int(time.time())}"
            self.temp_tables[table_name] = temp_name
        
        # Populate temp table with current data
        with self.db_conn.cursor() as cur:
            if table_name == 'gameweek_stats':
                cur.execute(f"TRUNCATE {temp_name}")
                cur.execute(f"""
                    INSERT INTO {temp_name}
                    SELECT * FROM gameweek_stats 
                    WHERE gameweek = (SELECT id FROM gameweeks WHERE is_current = TRUE)
                """)
            elif table_name == 'players':
                cur.execute(f"TRUNCATE {temp_name}")
                cur.execute(f"INSERT INTO {temp_name} SELECT * FROM players")
            else:
                cur.execute(f"TRUNCATE {temp_name}")
                cur.execute(f"INSERT INTO {temp_name} SELECT * FROM {table_name}")
        
        return temp_name

    def initialize_temp_tables(self):
        """Initialize temp tables once for reuse"""
        if not self.temp_tables:
            with self.db_conn.cursor() as cur:
                # Create temp tables with proper schemas
                cur.execute("""
                    CREATE TEMP TABLE IF NOT EXISTS temp_refresh_gameweek_stats (
                        LIKE gameweek_stats INCLUDING ALL
                    )
                """)
                cur.execute("""
                    CREATE TEMP TABLE IF NOT EXISTS temp_refresh_players (
                        LIKE players INCLUDING ALL
                    )
                """)
                
                self.temp_tables = {
                    'gameweek_stats': 'temp_refresh_gameweek_stats',
                    'players': 'temp_refresh_players'
                }

    def drop_temp_version(self, temp_table: str):
        """Drop temporary table to clean up"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {temp_table}")
        except Exception as e:
            print(f"⚠️ Warning: Could not drop temp table {temp_table}: {e}")

    def compute_diffs_against_version(self, temp_table: str, table_name: str) -> List[Dict]:
        """Compare new data against temporary version to detect real changes"""
        changes = []
        
        if table_name == 'gameweek_stats':
            changes = self.compute_gameweek_stats_diffs(temp_table)
        elif table_name == 'players':
            changes = self.compute_players_diffs(temp_table)
        
        return changes

    def compute_gameweek_stats_diffs(self, temp_table: str) -> List[Dict]:
        """Compute diffs for gameweek stats using temp table versioning - now uses centralized logic"""
        changes = []
        stat_mapping = self.get_stat_mapping()
        
        with self.db_conn.cursor() as cur:
            # Build dynamic SQL query based on stat mapping
            stat_columns = []
            stat_joins = []
            
            for category_name, db_column in stat_mapping.items():
                stat_columns.append(f"t.{db_column} as old_{db_column}, n.{db_column} as new_{db_column}")
                stat_joins.append(f"t.{db_column} != n.{db_column}")
            
            # Dynamic SQL construction
            select_clause = ", ".join([
                "t.player_id", "t.fixture_id", "t.gameweek",
                "p.fpl_id", "p.element_type",
                "t.minutes as old_minutes", "n.minutes as new_minutes"
            ] + stat_columns)
            
            where_clause = " OR ".join(stat_joins)
            
            cur.execute(f"""
                SELECT {select_clause}
                FROM {temp_table} t
                JOIN gameweek_stats n ON t.player_id = n.player_id 
                    AND t.fixture_id = n.fixture_id
                    AND t.gameweek = n.gameweek
                JOIN players p ON t.player_id = p.id
                WHERE {where_clause}
            """)
            
            for row in cur.fetchall():
                player_id, fixture_id, gameweek = row[0], row[1], row[2]
                fpl_id, element_type = row[3], row[4]
                old_minutes, new_minutes = row[5], row[6]
                
                # Process each stat using centralized diff computation
                stat_index = 7  # Start after the basic fields
                for category_name, db_column in stat_mapping.items():
                    old_value = row[stat_index] or 0
                    new_value = row[stat_index + 1] or 0
                    stat_index += 2
                    
                    # Use centralized diff computation
                    diff_result = self.compute_stat_diff(category_name, old_value, new_value, element_type, new_minutes)
                    if diff_result:
                        changes.append({
                            'type': 'performance',
                            'fpl_id': fpl_id,
                            'stat_name': category_name,
                            'db_column': db_column,
                            'old_value': old_value,
                            'new_value': new_value,
                            'change': diff_result['change'],
                            'points_change': diff_result['points_change'],
                            'element_type': element_type,
                            'minutes': new_minutes
                        })
        
        return changes

    def compute_players_diffs(self, temp_table: str) -> List[Dict]:
        """Compute diffs for players table using temp table versioning"""
        changes = []
        
        with self.db_conn.cursor() as cur:
            # Compare current player data against temp version
            cur.execute(f"""
                SELECT 
                    t.fpl_id,
                    t.now_cost as old_cost, n.now_cost as new_cost,
                    t.status as old_status, n.status as new_status
                FROM {temp_table} t
                JOIN players n ON t.fpl_id = n.fpl_id
                WHERE 
                    t.now_cost != n.now_cost OR
                    t.status != n.status
            """)
            
            for row in cur.fetchall():
                fpl_id = row[0]
                
                # Check price changes
                if row[1] != row[2]:
                    changes.append({
                        'type': 'price',
                        'fpl_id': fpl_id,
                        'stat_name': 'now_cost',
                        'old_value': row[1],
                        'new_value': row[2],
                        'change': row[2] - row[1]
                    })
                
                # Check status changes
                if row[3] != row[4]:
                    changes.append({
                        'type': 'status',
                        'fpl_id': fpl_id,
                        'stat_name': 'status',
                        'old_value': row[3],
                        'new_value': row[4],
                        'change': 0
                    })
        
        return changes

    def get_status_emoji(self, status: str) -> str:
        """Get appropriate emoji for FPL player status"""
        status_emojis = {
            'a': '✅',  # Available
            'u': '❌',  # Unavailable
            'i': '🏥',  # Injured
            's': '🟥',  # Suspended
            'n': '🚫',  # Not in squad
            'd': '⚠️',  # Doubtful
            'c': '🔄',  # Confirmed
            'r': '🔄',  # Return
            't': '⏰',  # Transfer
            'w': '🔄',  # Withdrawn
        }
        return status_emojis.get(status.lower(), '📊')

    def get_status_description(self, status: str) -> str:
        """Get user-friendly description for FPL player status"""
        status_descriptions = {
            'a': 'Available - Player is fit and available for selection',
            'u': 'Unavailable - Player is not available for selection',
            'i': 'Injured - Player is injured and unavailable',
            's': 'Suspended - Player is suspended and unavailable',
            'n': 'Not in Squad - Player not included in matchday squad',
            'd': 'Doubtful - Player has fitness concerns',
            'c': 'Confirmed - Player confirmed to start',
            'r': 'Return - Player returning from injury/suspension',
            't': 'Transfer - Player involved in transfer',
            'w': 'Withdrawn - Player withdrawn from squad',
        }
        return status_descriptions.get(status.lower(), f'Status: {status}')





    def get_player_info(self, fpl_id: int) -> Dict:
        """Get player and team info for notifications"""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT p.web_name, p.first_name, p.second_name, t.short_name, p.element_type
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE p.fpl_id = %s
            """, (fpl_id,))
            
            result = cur.fetchone()
            if result:
                return {
                    'web_name': result[0],
                    'full_name': f"{result[1] or ''} {result[2] or ''}".strip(),
                    'team': result[3],
                    'element_type': result[4],
                    'team_id': None  # We'll need to get this separately
                }
        return {}

    def get_team_short_name(self, team_id: int) -> str:
        """Get team short name for notifications"""
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT short_name FROM teams WHERE id = %s", (team_id,))
            result = cur.fetchone()
            return result[0] if result else "UNK"
    
    def get_fixture_minutes(self, player_id: int) -> int:
        """Get the current game time in minutes for a player's fixture"""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT f.minutes 
                FROM fixtures f
                JOIN gameweek_stats gs ON f.id = gs.fixture_id
                WHERE gs.player_id = %s
                LIMIT 1
            """, (player_id,))
            result = cur.fetchone()
            return result[0] if result else 0
    
    def get_player_total_points(self, fpl_id: int) -> int:
        """Get current total FPL points for a player"""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT total_points 
                FROM players 
                WHERE fpl_id = %s
            """, (fpl_id,))
            result = cur.fetchone()
            return result[0] if result else 0
    
    def get_current_gameweek_points(self, fpl_id: int) -> int:
        """Get current gameweek total points based on live gameweek_stats record"""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT gs.minutes, gs.goals_scored, gs.assists, gs.clean_sheets, 
                       gs.goals_conceded, gs.yellow_cards, gs.red_cards, gs.bonus,
                       gs.penalties_saved, gs.penalties_missed, gs.own_goals, gs.saves,
                       gs.defensive_contribution, p.element_type
                FROM gameweek_stats gs
                JOIN players p ON gs.player_id = p.id
                JOIN fixtures f ON gs.fixture_id = f.id
                WHERE p.fpl_id = %s 
                AND f.event_id = (SELECT id FROM gameweeks WHERE is_current = TRUE)
                LIMIT 1
            """, (fpl_id,))
            
            result = cur.fetchone()
            if not result:
                return 0
                
            minutes, goals, assists, clean_sheets, goals_conceded, yellow_cards, red_cards, bonus, \
            penalties_saved, penalties_missed, own_goals, saves, defensive_contribution, element_type = result
            
            # Calculate points based on FPL rules from rules.txt
            total_points = 0
            
            # Playing time points (only if player started)
            if minutes > 0:
                # Check if player started (has any minutes in the game)
                total_points += 1  # Base point for playing
                if minutes >= 60:
                    total_points += 1  # Extra point for 60+ minutes
            
            # Goals (position-based multipliers)
            if goals > 0:
                if element_type == 1:  # GK
                    total_points += goals * 10
                elif element_type == 2:  # DEF
                    total_points += goals * 6
                elif element_type == 3:  # MID
                    total_points += goals * 5
                elif element_type == 4:  # FWD
                    total_points += goals * 4
            
            # Assists (3 points for all positions)
            if assists > 0:
                total_points += assists * 3
            
            # Clean sheets (position-based, 60+ minutes required)
            if clean_sheets > 0 and minutes >= 60:
                if element_type == 1:  # GK
                    total_points += clean_sheets * 4
                elif element_type == 2:  # DEF
                    total_points += clean_sheets * 4
                elif element_type == 3:  # MID
                    total_points += clean_sheets * 1
                # FWD get 0 points for clean sheets
            
            # Goals conceded (only GK/DEF lose points)
            if goals_conceded > 0 and element_type in [1, 2]:
                total_points += (goals_conceded // 2) * -1  # -1 for every 2 goals
            
            # Cards
            if yellow_cards > 0:
                total_points += yellow_cards * -1
            if red_cards > 0:
                total_points += red_cards * -3
            
            # Penalties
            if penalties_saved > 0 and element_type == 1:  # GK only
                total_points += penalties_saved * 5
            if penalties_missed > 0:
                total_points += penalties_missed * -2
            
            # Own goals
            if own_goals > 0:
                total_points += own_goals * -2
            
            # Saves (GK only, every 3 saves = 1 point)
            if saves > 0 and element_type == 1:
                total_points += saves // 3
            
            # Defensive contribution
            if defensive_contribution > 0:
                if element_type == 2:  # Defender
                    if defensive_contribution >= 10:
                        total_points += 2
                elif element_type in [3, 4]:  # Midfielder or Forward
                    if defensive_contribution >= 12:
                        total_points += 2
            
            # Bonus points
            if bonus > 0:
                total_points += bonus
            
            return total_points
    
    def get_mini_league_ownership(self, fpl_id: int) -> float:
        """Get ownership percentage from specific mini league with caching"""
        current_time = int(time.time())
        
        # Check if we need to refresh ownership data (every 30 minutes)
        if current_time - self.last_ownership_refresh > 1800:  # 30 minutes
            self.refresh_mini_league_ownership()
        
        # Return cached ownership or 0.0 if not found
        return self.ownership_cache.get(fpl_id, 0.0)
    
    def get_mini_league_starting_percentage(self, fpl_id: int) -> float:
        """Get starting XI percentage from specific mini league with caching"""
        current_time = int(time.time())
        
        # Check if we need to refresh ownership data (every 30 minutes)
        if current_time - self.last_ownership_refresh > 1800:  # 30 minutes
            self.refresh_mini_league_ownership()
        
        # Return cached starting percentage or 0.0 if not found
        return self.starting_cache.get(fpl_id, 0.0)
    
    def get_overall_ownership_percentage(self, fpl_id: int) -> float:
        """Get overall FPL ownership percentage for a player"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT selected_by_percent 
                    FROM players 
                    WHERE fpl_id = %s
                """, (fpl_id,))
                result = cur.fetchone()
                return result[0] if result else 0.0
        except Exception as e:
            print(f"⚠️ Error getting overall ownership for player {fpl_id}: {e}")
            return 0.0
    
    def detect_bps_bonus_changes(self, player_id: int, new_bps: int, old_bps: int, fixture_id: int) -> List[Dict]:
        """Detect bonus point changes based on BPS ranking within a fixture"""
        changes = []
        
        if new_bps == old_bps:
            return changes  # No BPS change, no bonus change
        
        # Check fixture minutes - only process bonus after 60 minutes
        fixture_minutes = self.get_fixture_minutes(player_id)
        if fixture_minutes < 60:
            return changes  # Too early for bonus points
        
        # Get current BPS ranking for all players in this fixture
        current_rankings = self.get_bps_rankings_for_fixture(fixture_id)
        if not current_rankings:
            return changes  # Can't calculate rankings yet
        
        # Get previous rankings from previous_state for comparison
        previous_bps_key = f"fixture_{fixture_id}_bps_rankings"
        previous_rankings = self.previous_state.get(previous_bps_key, {})
        
        # Calculate bonus changes for ALL players in this fixture (not just the one who changed)
        # This handles cases where one player's BPS change affects others' bonus points
        all_bonus_changes = self.calculate_fixture_bonus_changes(
            fixture_id, current_rankings, previous_rankings
        )
        
        if all_bonus_changes:
            changes.extend(all_bonus_changes)
    
        
        # Store current rankings in previous_state for next comparison
        self.previous_state[previous_bps_key] = current_rankings
        
        return changes
    
    def calculate_fixture_bonus_changes(self, fixture_id: int, current_rankings: Dict[int, int], previous_rankings: Dict[int, int]) -> List[Dict]:
        """Calculate bonus changes for all players in a fixture, handling tiebreakers properly"""
        changes = []
        
        if not current_rankings:
            return changes
        
        # Convert rankings to list of (fpl_id, rank) tuples for easier processing
        current_rank_list = [(fpl_id, rank) for fpl_id, rank in current_rankings.items()]
        current_rank_list.sort(key=lambda x: x[1])  # Sort by rank
        
        # Calculate current bonus points for all players
        current_bonus = {}
        for fpl_id, rank in current_rank_list:
            current_bonus[fpl_id] = self.calculate_bonus_from_rank(rank)
        
        # Calculate previous bonus points for all players
        previous_bonus = {}
        if previous_rankings:
            for fpl_id, rank in previous_rankings.items():
                previous_bonus[fpl_id] = self.calculate_bonus_from_rank(rank)
        
        # Check for bonus changes and create notifications
        for fpl_id in current_rankings:
            current_bonus_points = current_bonus.get(fpl_id, 0)
            previous_bonus_points = previous_bonus.get(fpl_id, 0)
            
            if current_bonus_points != previous_bonus_points:
                player_info = self.get_player_info(fpl_id)
                if player_info:
                    # Get team_id separately since it's not in player_info
                    with self.db_conn.cursor() as cur:
                        cur.execute("SELECT team_id FROM players WHERE fpl_id = %s", (fpl_id,))
                        team_result = cur.fetchone()
                        team_id = team_result[0] if team_result else None
                    
                    if team_id:
                        changes.append({
                            'type': 'performance',
                            'fpl_id': fpl_id,
                            'stat_name': 'bonus',
                            'db_column': 'bonus',
                            'old_value': previous_bonus_points,
                            'new_value': current_bonus_points,
                            'change': current_bonus_points - previous_bonus_points,
                            'points_change': current_bonus_points - previous_bonus_points,
                            'element_type': player_info['element_type'],
                            'minutes': 90,
                            'web_name': player_info['web_name'],
                            'team_id': team_id,
                            'player_name': player_info['web_name'],
                            'team_name': self.get_team_short_name(team_id)
                        })
        
        return changes
    
    def detect_final_bonus_changes(self) -> List[Dict]:
        """Detect when FPL API populates the bonus column with final values"""
        changes = []
        
        try:
            with self.db_conn.cursor() as cur:
                # Look for fixtures that have finished and now have bonus values populated
                # Only check fixtures that are recent enough to potentially have new bonus data
                cur.execute("""
                    SELECT DISTINCT f.id, f.kickoff_time, f.finished
                    FROM fixtures f
                    JOIN gameweek_stats gs ON f.id = gs.fixture_id
                    WHERE f.finished = true 
                    AND gs.bonus IS NOT NULL 
                    AND gs.bonus > 0
                    AND f.kickoff_time > NOW() - INTERVAL '24 hours'  -- Only check recent fixtures
                    ORDER BY f.kickoff_time DESC
                    LIMIT 10
                """)
                
                finished_fixtures = cur.fetchall()
                
                for fixture_id, kickoff_time, finished in finished_fixtures:
                    # Check if this fixture was already processed in a previous run
                    # by looking for a persistent marker in the database
                    cur.execute("""
                        SELECT 1 FROM live_monitor_history 
                        WHERE fixture_id = %s AND event_type = 'bonus_final'
                        LIMIT 1
                    """, (fixture_id,))
                    
                    if cur.fetchone():
                        # Already processed this fixture, skip it
                        continue
                    
                    # Get all players with bonus points in this fixture
                    cur.execute("""
                        SELECT p.fpl_id, p.web_name, p.element_type, t.short_name, gs.bonus
                        FROM gameweek_stats gs
                        JOIN players p ON gs.player_id = p.id
                        JOIN teams t ON p.team_id = t.id
                        WHERE gs.fixture_id = %s 
                        AND gs.bonus IS NOT NULL 
                        AND gs.bonus > 0
                        ORDER BY gs.bonus DESC
                    """, (fixture_id,))
                    
                    bonus_players = cur.fetchall()
                    
                    if bonus_players:
                        # Create one consolidated notification for all bonus players in this fixture
                        changes.append({
                            'type': 'performance',
                            'fpl_id': bonus_players[0][0],  # Use first player's ID for the notification
                            'stat_name': 'bonus_final',
                            'db_column': 'bonus',
                            'old_value': 0,  # Previous state was 0 (not populated)
                            'new_value': len(bonus_players),  # Number of players with bonus
                            'change': len(bonus_players),
                            'points_change': sum(player[4] for player in bonus_players),  # Total bonus points
                            'element_type': bonus_players[0][2],
                            'minutes': 90,
                            'web_name': f"{len(bonus_players)} players",
                            'team_id': None,
                            'player_name': f"{len(bonus_players)} players",
                            'team_name': 'FINAL',
                            'fixture_id': fixture_id,
                            'bonus_players': bonus_players  # Store all players for detailed formatting
                        })
                        
                
        
        except Exception as e:
            print(f"⚠️ Error detecting final bonus changes: {e}")
        
        return changes
    
    def cleanup_old_final_bonus_notifications(self):
        """Clean up old final bonus notifications to prevent database bloat"""
        try:
            with self.db_conn.cursor() as cur:
                # Remove final bonus notifications older than 7 days
                cur.execute("""
                    DELETE FROM live_monitor_history 
                    WHERE event_type = 'bonus_final' 
                    AND created_at < NOW() - INTERVAL '7 days'
                """)
                
                deleted_count = cur.rowcount
                
                self.db_conn.commit()
                
        except Exception as e:
            print(f"⚠️ Error cleaning up old final bonus notifications: {e}")

    def is_duplicate_bonus_notification(self, change: Dict) -> bool:
        """Check if this bonus notification has already been sent to prevent duplicates"""
        if change.get('stat_name') not in ['bonus', 'bonus_final']:
            return False  # Not a bonus notification
        
        try:
            with self.db_conn.cursor() as cur:
                # For fixture-specific bonus (like final bonus)
                if 'fixture_id' in change:
                    cur.execute("""
                        SELECT 1 FROM live_monitor_history 
                        WHERE fixture_id = %s AND event_type = %s
                        LIMIT 1
                    """, (change['fixture_id'], change['stat_name']))
                    return cur.fetchone() is not None
                
                # For individual player bonus changes, check if we've already notified for this specific bonus value
                # This prevents duplicate notifications when the same bonus points are detected multiple times
                cur.execute("""
                    SELECT 1 FROM live_monitor_history 
                    WHERE player_id = (SELECT id FROM players WHERE fpl_id = %s)
                    AND event_type = %s AND new_value = %s
                    AND created_at > NOW() - INTERVAL '24 hours'  -- Only check recent notifications
                    LIMIT 1
                """, (change['fpl_id'], change['stat_name'], change['new_value']))
                
                return cur.fetchone() is not None
                
        except Exception as e:
            print(f"⚠️ Error checking for duplicate bonus notification: {e}")
            return False  # If we can't check, allow the notification to proceed

    def validate_previous_state_integrity(self):
        """Validate that previous_state is properly initialized to prevent spam notifications"""
        try:
            # Check if previous_state has sufficient data
            if not self.previous_state:
                print("⚠️ Previous state is empty - initializing...")
                self.initialize_previous_state()
                return
            
            # Count how many players have state data
            player_state_count = sum(1 for key in self.previous_state if key.startswith('player_'))
            
            # If we have very few players with state, something is wrong
            if player_state_count < 100:  # Should have hundreds of players
                print(f"⚠️ Previous state has only {player_state_count} players - reinitializing...")
                self.initialize_previous_state()
                return
            
            # Check for bonus state specifically
            bonus_state_count = 0
            for key, state in self.previous_state.items():
                if key.startswith('player_') and 'bonus' in state:
                    bonus_state_count += 1
            
            # If we have players but no bonus state, that's suspicious
            if player_state_count > 100 and bonus_state_count < 50:
                print(f"⚠️ Previous state missing bonus data ({bonus_state_count}/{player_state_count} players) - reinitializing...")
                self.initialize_previous_state()
                return
                
        except Exception as e:
            print(f"⚠️ Error validating previous state integrity: {e}")
            # Don't reinitialize on error, just log it

    def get_bps_rankings_for_fixture(self, fixture_id: int) -> Dict[int, int]:
        """Get BPS rankings for all players in a fixture, handling ties properly"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT gs.player_id, gs.bps, p.fpl_id
                    FROM gameweek_stats gs
                    JOIN players p ON gs.player_id = p.id
                    WHERE gs.fixture_id = %s AND gs.bps > 0
                    ORDER BY gs.bps DESC
                """, (fixture_id,))
                
                results = cur.fetchall()
                if not results:
                    return {}
                
                # Handle tiebreakers according to FPL rules:
                # - If tie for 1st: Players 1&2 get 3 points, Player 3 gets 1 point
                # - If tie for 2nd: Player 1 gets 3, Players 2&3 get 2 points each
                # - If tie for 3rd: Player 1 gets 3, Player 2 gets 2, Players 3&4 get 1 point each
                
                rankings = {}
                current_rank = 1
                current_bps = None
                tied_players = []
                
                for player_id, bps, fpl_id in results:
                    if bps != current_bps:
                        # Process any tied players from previous group
                        if tied_players:
                            self.assign_ranks_for_tied_group(rankings, tied_players, current_rank)
                            current_rank += len(tied_players)
                        
                        # Start new group
                        tied_players = [fpl_id]
                        current_bps = bps
                    else:
                        # Same BPS - add to tied group
                        tied_players.append(fpl_id)
                
                # Process final group
                if tied_players:
                    self.assign_ranks_for_tied_group(rankings, tied_players, current_rank)
                
                return rankings
                
        except Exception as e:
            print(f"⚠️ Error getting BPS rankings for fixture {fixture_id}: {e}")
            return {}
    
    def assign_ranks_for_tied_group(self, rankings: Dict[int, int], tied_players: List[int], start_rank: int) -> None:
        """Assign ranks for a group of tied players according to FPL tiebreaker rules"""
        if not tied_players:
            return
        
        # FPL tiebreaker rules:
        # - If tie for 1st: Players 1&2 get 3 points, Player 3 gets 1 point
        # - If tie for 2nd: Player 1 gets 3, Players 2&3 get 2 points each  
        # - If tie for 3rd: Player 1 gets 3, Player 2 gets 2, Players 3&4 get 1 point each
        
        if start_rank == 1:
            # Tie for 1st place
            if len(tied_players) == 1:
                rankings[tied_players[0]] = 1  # Solo 1st place
            elif len(tied_players) == 2:
                rankings[tied_players[0]] = 1  # Both get 3 points (rank 1)
                rankings[tied_players[1]] = 1
            else:
                # 3+ players tied for 1st
                for i, fpl_id in enumerate(tied_players):
                    if i < 2:
                        rankings[fpl_id] = 1  # First 2 get 3 points (rank 1)
                    else:
                        rankings[fpl_id] = 3  # Rest get 1 point (rank 3)
        
        elif start_rank == 2:
            # Tie for 2nd place
            if len(tied_players) == 1:
                rankings[tied_players[0]] = 2  # Solo 2nd place
            else:
                # Multiple players tied for 2nd
                for fpl_id in tied_players:
                    rankings[fpl_id] = 2  # All get 2 points (rank 2)
        
        elif start_rank == 3:
            # Tie for 3rd place
            for fpl_id in tied_players:
                rankings[fpl_id] = 3  # All get 1 point (rank 3)
        
        else:
            # 4th place and below - no bonus points
            for fpl_id in tied_players:
                rankings[fpl_id] = start_rank
    
    def calculate_bonus_from_rank(self, rank: int) -> int:
        """Calculate bonus points based on rank (1=3pts, 2=2pts, 3=1pt, 4+=0pts)"""
        if rank == 1:
            return 3
        elif rank == 2:
            return 2
        elif rank == 3:
            return 1
        else:
            return 0
    
    def detect_live_bps_changes(self) -> List[Dict]:
        """Actively monitor BPS changes and bonus point updates during live matches"""
        changes = []
        
        try:
            # Get current gameweek
            current_gameweek = self.get_current_gameweek()
            
            # Get all live fixtures for current gameweek
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT f.id, f.minutes
                    FROM fixtures f
                    JOIN gameweek_stats gs ON f.id = gs.fixture_id
                    WHERE f.event_id = %s 
                    AND f.started = TRUE 
                    AND f.finished = FALSE
                    AND f.minutes >= 60
                """, (current_gameweek,))
                
                live_fixtures = cur.fetchall()
            
            for fixture_id, minutes in live_fixtures:
                # Get current BPS rankings for this fixture
                current_rankings = self.get_bps_rankings_for_fixture(fixture_id)
                if not current_rankings:
                    continue
                
                # Get previous rankings from previous_state for comparison
                previous_bps_key = f"fixture_{fixture_id}_bps_rankings"
                previous_rankings = self.previous_state.get(previous_bps_key, {})
                
                # Calculate bonus changes for ALL players in this fixture
                fixture_bonus_changes = self.calculate_fixture_bonus_changes(
                    fixture_id, current_rankings, previous_rankings
                )
                
                if fixture_bonus_changes:
                    changes.extend(fixture_bonus_changes)
            
                
                # Store current rankings in previous_state for next comparison
                self.previous_state[previous_bps_key] = current_rankings
            
            if changes:
                pass  # Silent processing
            
        except Exception as e:
            print(f"⚠️ Error detecting live BPS changes: {e}")
        
        return changes
    
    def refresh_mini_league_ownership(self):
        """Refresh mini league ownership and starting XI data from FPL API"""
        try:
    
            
            # Fetch mini league data from FPL API
            url = f"{self.fpl_base_url}/leagues-classic/{self.mini_league_id}/standings/"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Clear old caches
            self.ownership_cache = {}
            self.starting_cache = {}
            
            # Get current gameweek
            current_gameweek = self.get_current_gameweek()
            
            # Search through all managers in the league
            total_managers = 0
            player_ownership_counts = {}  # Track how many managers own each player
            player_starting_counts = {}   # Track how many managers start each player
            
            for entry in data.get('standings', {}).get('results', []):
                manager_id = entry['entry']
                total_managers += 1
                
                try:
                    # Get this manager's team
                    team_url = f"{self.fpl_base_url}/entry/{manager_id}/event/{current_gameweek}/picks/"
                    team_response = requests.get(team_url, timeout=10)
                    if team_response.status_code == 200:
                        team_data = team_response.json()
                        
                        # Check if player is in starting XI or bench
                        for pick in team_data.get('picks', []):
                            player_id = pick['element']
                            position = pick['position']  # 1-11 = starting XI, 12-15 = bench
                            
                            # Track ownership (any position)
                            if player_id not in player_ownership_counts:
                                player_ownership_counts[player_id] = 0
                            player_ownership_counts[player_id] += 1
                            
                            # Track starting XI (positions 1-11)
                            if position <= 11:  # Starting XI
                                if player_id not in player_starting_counts:
                                    player_starting_counts[player_id] = 0
                                player_starting_counts[player_id] += 1
                except Exception as e:
                    # Skip this manager if there's an error
                    continue
            
            # Calculate ownership percentages
            for player_id, count in player_ownership_counts.items():
                if total_managers > 0:
                    ownership_percent = (count / total_managers) * 100
                    self.ownership_cache[player_id] = round(ownership_percent, 1)
            
            # Calculate starting XI percentages
            for player_id, count in player_starting_counts.items():
                if total_managers > 0:
                    starting_percent = (count / total_managers) * 100
                    self.starting_cache[player_id] = round(starting_percent, 1)
            
            # Update last refresh time
            self.last_ownership_refresh = int(time.time())
    
            
        except Exception as e:
            # Keep old cache if refresh fails
            pass

    def get_current_gameweek(self) -> int:
        """Get current gameweek ID"""
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT id FROM gameweeks WHERE is_current = TRUE")
            result = cur.fetchone()
            return result[0] if result else 1

    # BPS-related methods now actively monitor live bonus point changes

    def send_discord_notification(self, message: str, team_name: str = None):
        """Send notification to Discord webhook with team emoji"""
        if not self.webhook_url or "YOUR_WEBHOOK_HERE" in self.webhook_url:
            print(f"⚠️ No valid Discord webhook configured")
            return
        
        # Create Discord embed with team emoji
        embed = {
            "description": message,
            "color": 0x00ff00  # Green color for FPL
        }
        
        payload = {
            "embeds": [embed],
            "username": self.bot_username,
            "avatar_url": "https://fantasy.premierleague.com/dist/img/favicon.ico"
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Discord notification failed: {e}")

    def format_notification_message(self, change: Dict) -> str:
        """Format change into clean, effective Discord notification message"""
        # Use direct player and team names if available
        if 'player_name' in change and 'team_name' in change:
            web_name = change['player_name']
            team = change['team_name']
        else:
            # Fallback to database lookup
            player_info = self.get_player_info(change['fpl_id'])
            if not player_info:
                return f"Unknown player {change['fpl_id']}: {change['stat_name']} changed"
            web_name = player_info['web_name']
            team = player_info['team']
        stat_name = change['stat_name']
        old_value = change['old_value']
        new_value = change['new_value']
        
        # Get emoji from our notification categories
        if stat_name not in self.notification_categories:
            return f"**{web_name.upper()}** ({team.upper()})\n❌ **UNKNOWN CHANGE** {stat_name}: {old_value} → {new_value}\n---------------"
        
        emoji = self.notification_categories[stat_name]['emoji']
        
        # Price changes (always enabled)
        if change['type'] == 'price':
            change_text = f"+{change['change']/10:.1f}m" if change['change'] > 0 else f"{change['change']/10:.1f}m"
            new_price = f"{new_value/10:.1f}m"
            
            # Get additional player info for third row
            fpl_id = change.get('fpl_id')
            gameweek_points = self.get_current_gameweek_points(fpl_id) if fpl_id else 0
            starting_percent = self.get_mini_league_starting_percentage(fpl_id) if fpl_id else 0.0
            overall_ownership = self.get_overall_ownership_percentage(fpl_id) if fpl_id else 0.0
            third_row = f"📊 **{gameweek_points} pts** | 👥 **{starting_percent}%** | 🌍 **{overall_ownership:.1f}%**"
            
            return f"**{web_name.upper()}** ({team.upper()}) - {starting_percent}% start\n💰 **PRICE CHANGE** {change_text}\n{third_row}"
        
        # Status changes (injuries, suspensions, etc.)
        elif change['type'] == 'status':
            status_emoji = self.get_status_emoji(new_value)
            status_description = self.get_status_description(new_value)
            
            # Get additional player info for third row
            fpl_id = change.get('fpl_id')
            gameweek_points = self.get_current_gameweek_points(fpl_id) if fpl_id else 0
            starting_percent = self.get_mini_league_starting_percentage(fpl_id) if fpl_id else 0.0
            overall_ownership = self.get_overall_ownership_percentage(fpl_id) if fpl_id else 0.0
            third_row = f"📊 **{gameweek_points} pts** | 👥 **{starting_percent}%** | 🌍 **{overall_ownership:.1f}%**"
            
            return f"**{web_name.upper()}** ({team.upper()}) - {starting_percent}% start\n{status_emoji} **STATUS CHANGE** {old_value} → {new_value}\n📋 **{status_description}**\n{third_row}"
        
        # Performance stats (using our notification categories)
        else:
            # Enhanced FPL-focused formatting with points impact
            points_change = change.get('points_change', 0)
            
            # Format points change with proper sign
            points_text = f"+{points_change}" if points_change > 0 else f"{points_change}"
            
            # Get the description from our notification category
            description = self.notification_categories[stat_name]['description'].upper()
            
            # Special formatting for threshold-based stats
            if stat_name == 'clean_sheets':
                # Special handling for clean sheets - use negative emoji when lost
                if points_change < 0:
                    clean_sheet_emoji = self.notification_categories[stat_name]['negative_emoji']
                else:
                    clean_sheet_emoji = emoji
                
                # Get additional player info for third row
                fpl_id = change.get('fpl_id')
                gameweek_points = self.get_current_gameweek_points(fpl_id) if fpl_id else 0
                starting_percent = self.get_mini_league_starting_percentage(fpl_id) if fpl_id else 0.0
                overall_ownership = self.get_overall_ownership_percentage(fpl_id) if fpl_id else 0.0
                third_row = f"📊 **{gameweek_points} pts** | 👥 **{starting_percent}%** | 🌍 **{overall_ownership:.1f}%**"
                
                return f"**{web_name.upper()}** ({team.upper()}) - {starting_percent}% start\n{clean_sheet_emoji} **{description}** ({new_value}) {points_text} pts\n{third_row}"
            elif stat_name == 'saves':
                # Get additional player info for third row
                fpl_id = change.get('fpl_id')
                total_points = self.get_player_total_points(fpl_id) if fpl_id else 0
                starting_percent = self.get_mini_league_starting_percentage(fpl_id) if fpl_id else 0.0
                overall_ownership = self.get_overall_ownership_percentage(fpl_id) if fpl_id else 0.0
                third_row = f"📊 **{total_points} pts** | 👥 **{starting_percent}%** | 🌍 **{overall_ownership:.1f}%**"
                
                return f"**{web_name.upper()}** ({team.upper()}) - {starting_percent}% start\n{emoji} **{description}** ({new_value}) {points_text} pts\n{third_row}"
            elif stat_name == 'goals_conceded':
                # Get additional player info for third row
                fpl_id = change.get('fpl_id')
                gameweek_points = self.get_current_gameweek_points(fpl_id) if fpl_id else 0
                starting_percent = self.get_mini_league_starting_percentage(fpl_id) if fpl_id else 0.0
                overall_ownership = self.get_overall_ownership_percentage(fpl_id) if fpl_id else 0.0
                third_row = f"📊 **{gameweek_points} pts** | 👥 **{starting_percent}%** | 🌍 **{overall_ownership:.1f}%**"
                
                return f"**{web_name.upper()}** ({team.upper()}) - {starting_percent}% start\n{emoji} **{description}** ({new_value}) {points_text} pts\n{third_row}"
            elif stat_name == 'defensive_contribution':
                # Get additional player info for third row
                fpl_id = change.get('fpl_id')
                gameweek_points = self.get_current_gameweek_points(fpl_id) if fpl_id else 0
                starting_percent = self.get_mini_league_starting_percentage(fpl_id) if fpl_id else 0.0
                overall_ownership = self.get_overall_ownership_percentage(fpl_id) if fpl_id else 0.0
                third_row = f"📊 **{gameweek_points} pts** | 👥 **{starting_percent}%** | 🌍 **{overall_ownership:.1f}%**"
                
                return f"**{web_name.upper()}** ({team.upper()}) - {starting_percent}% start\n{emoji} **{description}** ({new_value}) {points_text} pts\n{third_row}"

            else:
                # Get additional player info for third row
                fpl_id = change.get('fpl_id')
                gameweek_points = self.get_current_gameweek_points(fpl_id) if fpl_id else 0
                starting_percent = self.get_mini_league_starting_percentage(fpl_id) if fpl_id else 0.0
                
                # Special formatting for final bonus notifications
                if stat_name == 'bonus_final':
                    bonus_players = change.get('bonus_players', [])
                    if bonus_players:
                        # Create detailed bonus breakdown with medal emojis
                        bonus_details = []
                        for fpl_id, web_name, element_type, team_short, bonus_points in bonus_players:
                            if bonus_points == 3:
                                medal = "🥇"  # Gold for 3 points
                            elif bonus_points == 2:
                                medal = "🥈"  # Silver for 2 points
                            elif bonus_points == 1:
                                medal = "🥉"  # Bronze for 1 point
                            else:
                                medal = "⚪"  # White circle for 0 points
                            
                            bonus_details.append(f"{medal} {web_name} ({team_short}) {bonus_points}pts")
                        
                        bonus_text = "\n".join(bonus_details)
                        return f"**BONUS (FINAL)**\n{bonus_text}"
                
                # Format third row with current gameweek points, mini league starting percentage, and overall ownership
                overall_ownership = self.get_overall_ownership_percentage(fpl_id) if fpl_id else 0.0
                third_row = f"📊 **{gameweek_points} pts** | 👥 **{starting_percent}%** | 🌍 **{overall_ownership:.1f}%**"
                
                return f"**{web_name.upper()}** ({team.upper()})\n{emoji} **{description}** {points_text} pts\n{third_row}"

    def enrich_change_with_player_info(self, change: Dict) -> Dict:
        """Add player and team names to change object"""
        if 'player_name' not in change or 'team_name' not in change:
            player_info = self.get_player_info(change['fpl_id'])
            if player_info:
                change['player_name'] = player_info['web_name']
                change['team_name'] = player_info['team']
            else:
                change['player_name'] = f"Player {change['fpl_id']}"
                change['team_name'] = "UNK"
        return change

    def process_changes(self, changes: List[Dict]):
        """Process detected changes and send notifications with grouping"""
        if not changes:
            return
        
        # Enrich changes with player/team information
        enriched_changes = []
        for change in changes:
            enriched_change = self.enrich_change_with_player_info(change)
            enriched_changes.append(enriched_change)
        
        # Separate different types of notifications
        bonus_changes = []
        bonus_final_changes = []
        price_changes = []
        live_changes = []
        
        for change in enriched_changes:
            # Check for duplicate bonus notifications
            if self.is_duplicate_bonus_notification(change):
                continue
            
            # Separate different types of changes
            if change.get('stat_name') == 'bonus':
                bonus_changes.append(change)
            elif change.get('stat_name') == 'bonus_final':
                bonus_final_changes.append(change)
            elif change.get('type') == 'price':
                price_changes.append(change)
            else:
                live_changes.append(change)
        
        # Send consolidated price change notifications
        if price_changes:
            self.send_consolidated_price_notifications(price_changes)
            self.notifications_sent_this_cycle += 1
        
        # Send grouped live match notifications (sorted by start % descending)
        if live_changes:
            self.send_grouped_live_notifications(live_changes)
            self.notifications_sent_this_cycle += 1
        
        # Send separate bonus notifications (always grouped) with spam protection
        if bonus_changes:
            # Limit bonus notifications to prevent spam (max 10 per cycle)
            if len(bonus_changes) > 10:
                print(f"⚠️ Limiting bonus notifications from {len(bonus_changes)} to 10 to prevent spam")
                bonus_changes = bonus_changes[:10]  # Take only the first 10 (highest ownership)
            
            self.send_grouped_bonus_notifications(bonus_changes)
            self.notifications_sent_this_cycle += 1
        
        # Send official bonus notifications individually (one per fixture)
        for bonus_final_change in bonus_final_changes:
            self.send_individual_notification(bonus_final_change)
            self.notifications_sent_this_cycle += 1
        
        # Log all changes to CSV
        for change in enriched_changes:
            try:
                change['notification_sent'] = True
                self.log_change(change)
            except Exception as e:
                pass  # Silent error handling

    def send_grouped_live_notifications(self, changes: List[Dict]):
        """Send grouped live match notifications sorted by start % descending"""
        if not changes:
            return
        
        # Sort changes by mini league starting percentage (descending)
        changes.sort(key=lambda x: self.get_mini_league_starting_percentage(x.get('fpl_id', 0)), reverse=True)
        
        # Get fixture info for header
        fixture_header = self.get_fixture_header(changes[0]) if changes else ""
        
        # Build grouped message
        message_parts = []
        if fixture_header:
            message_parts.append(f"**{fixture_header}**")
            message_parts.append("")  # Empty line after header
        
        for change in changes:
            # Format individual player notification
            player_message = self.format_notification_message(change)
            message_parts.append(player_message)
        
        # Join all notifications with dividers
        grouped_message = "\n\n".join(message_parts)
        
        # Send as single Discord notification
        self.send_discord_notification(grouped_message, "FPL")

    def send_grouped_bonus_notifications(self, changes: List[Dict]):
        """Send grouped bonus notifications sorted by start % descending"""
        if not changes:
            return
        
        # Sort changes by mini league starting percentage (descending)
        changes.sort(key=lambda x: self.get_mini_league_starting_percentage(x.get('fpl_id', 0)), reverse=True)
        
        # Get fixture info for header
        fixture_header = self.get_fixture_header(changes[0]) if changes else ""
        
        # Build grouped message
        message_parts = []
        if fixture_header:
            message_parts.append(f"**{fixture_header}**")
            message_parts.append("")  # Empty line after header
        
        for change in changes:
            # Format individual player notification
            player_message = self.format_notification_message(change)
            message_parts.append(player_message)
        
        # Join all notifications with dividers
        grouped_message = "\n\n".join(message_parts)
        
        # Send as single Discord notification
        self.send_discord_notification(grouped_message, "FPL")

    def send_consolidated_price_notifications(self, changes: List[Dict]):
        """Send consolidated price change notifications - one for increases, one for decreases"""
        if not changes:
            return
        
        # Separate price increases and decreases
        price_increases = []
        price_decreases = []
        
        for change in changes:
            if change.get('change', 0) > 0:
                price_increases.append(change)
            else:
                price_decreases.append(change)
        
        # Send price increase notification
        if price_increases:
            self.send_price_increase_notification(price_increases)
        
        # Send price decrease notification
        if price_decreases:
            self.send_price_decrease_notification(price_decreases)

    def send_price_increase_notification(self, changes: List[Dict]):
        """Send consolidated price increase notification"""
        if not changes:
            return
        
        # Sort by mini league ownership percentage (descending)
        changes.sort(key=lambda x: self.get_mini_league_starting_percentage(x.get('fpl_id', 0)), reverse=True)
        
        # Build message
        message_parts = ["📈 **PRICE INCREASES**", "---------------"]
        
        for change in changes:
            player_name = change.get('player_name', '').upper()
            team_abbr = change.get('team_name', '').upper()
            new_price = f"{change.get('new_value', 0):.1f}m"
            ownership = self.get_mini_league_starting_percentage(change.get('fpl_id', 0))
            
            player_line = f"**{player_name}** ({team_abbr}) | {new_price} | {ownership:.1f}%"
            message_parts.append(player_line)
        
        message_parts.append("---------------")
        
        # Send notification
        grouped_message = "\n".join(message_parts)
        self.send_discord_notification(grouped_message, "FPL")

    def send_price_decrease_notification(self, changes: List[Dict]):
        """Send consolidated price decrease notification"""
        if not changes:
            return
        
        # Sort by mini league ownership percentage (descending)
        changes.sort(key=lambda x: self.get_mini_league_starting_percentage(x.get('fpl_id', 0)), reverse=True)
        
        # Build message
        message_parts = ["📉 **PRICE DECREASES**", "---------------"]
        
        for change in changes:
            player_name = change.get('player_name', '').upper()
            team_abbr = change.get('team_name', '').upper()
            new_price = f"{change.get('new_value', 0):.1f}m"
            ownership = self.get_mini_league_starting_percentage(change.get('fpl_id', 0))
            
            player_line = f"**{player_name}** ({team_abbr}) | {new_price} | {ownership:.1f}%"
            message_parts.append(player_line)
        
        message_parts.append("---------------")
        
        # Send notification
        grouped_message = "\n".join(message_parts)
        self.send_discord_notification(grouped_message, "FPL")

    def send_individual_notification(self, change: Dict):
        """Send individual notification for changes that don't meet grouping criteria"""
        message = self.format_notification_message(change)
        team_name = change.get('team_name')
        self.send_discord_notification(message, team_name)

    def get_fixture_header(self, change: Dict) -> str:
        """Get fixture header (home team vs away team) for a change"""
        try:
            fixture_id = change.get('fixture_id')
            if not fixture_id:
                return ""
            
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT th.short_name as home_team, ta.short_name as away_team
                    FROM fixtures f
                    JOIN teams th ON f.team_h = th.id
                    JOIN teams ta ON f.team_a = ta.id
                    WHERE f.id = %s
                """, (fixture_id,))
                
                result = cur.fetchone()
                if result:
                    home_team, away_team = result
                    return f"{home_team} vs {away_team}"
            
            return ""
        except Exception as e:
            return ""

    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            # Use DATABASE_URL from environment (Supabase)
            db_url = os.getenv('DATABASE_URL')
            if db_url:
                self.db_conn = psycopg2.connect(db_url)
            else:
                # Fallback to local database
                self.db_conn = psycopg2.connect(
                    dbname="fpl",
                    user="silverman",
                    host="localhost",
                    port="5432"
                )
    
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            sys.exit(1)

    def close_db(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()

    def fetch_fpl_data(self, endpoint: str) -> Dict:
        """Fetch data from FPL API with error handling"""
        url = f"{self.fpl_base_url}/{endpoint}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching {endpoint}: {e}")
            return {}



    def populate_teams(self):
        """Populate teams table from bootstrap-static"""
        data = self.fetch_fpl_data("bootstrap-static")
        if not data or 'teams' not in data:
            print("❌ No teams data found")
            return

        with self.db_conn.cursor() as cur:
            for team in data['teams']:
                cur.execute("""
                    INSERT INTO teams (
                        fpl_id, code, name, short_name, position, played, win, draw, loss, 
                        points, strength, form
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (fpl_id) DO UPDATE SET
                        name = EXCLUDED.name, short_name = EXCLUDED.short_name,
                        position = EXCLUDED.position, played = EXCLUDED.played,
                        win = EXCLUDED.win, draw = EXCLUDED.draw, loss = EXCLUDED.loss,
                        points = EXCLUDED.points, strength = EXCLUDED.strength,
                        form = EXCLUDED.form, updated_at = CURRENT_TIMESTAMP
                """, (
                    team['id'], team['code'], team['name'], team['short_name'],
                    team.get('position', 0), team.get('played', 0), team.get('win', 0),
                    team.get('draw', 0), team.get('loss', 0), team.get('points', 0),
                    team.get('strength', 0), team.get('form', '')
                ))
            self.db_conn.commit()

    def populate_players(self):
        """Populate players table from bootstrap-static"""
        data = self.fetch_fpl_data("bootstrap-static")
        if not data or 'elements' not in data:
            print("❌ No players data found")
            return

        with self.db_conn.cursor() as cur:
            for player in data['elements']:
                # Get the database team_id from FPL team ID
                cur.execute("SELECT id FROM teams WHERE fpl_id = %s", (player['team'],))
                team_result = cur.fetchone()
                if not team_result:
                    print(f"⚠️ Team ID {player['team']} not found for player {player['web_name']}")
                    continue
                
                team_id = team_result[0]
                
                # Extract all available player data
                try:
                    cur.execute("""
                    INSERT INTO players (
                        fpl_id, web_name, first_name, second_name, team_id, element_type, 
                        now_cost, total_points, event_points, points_per_game, form, 
                        selected_by_percent, status, cost_change_event, cost_change_start,
                        cost_change_event_fall, cost_change_start_fall
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (fpl_id) DO UPDATE SET
                        web_name = EXCLUDED.web_name, first_name = EXCLUDED.first_name,
                        second_name = EXCLUDED.second_name, now_cost = EXCLUDED.now_cost,
                        total_points = EXCLUDED.total_points, event_points = EXCLUDED.event_points,
                        points_per_game = EXCLUDED.points_per_game, form = EXCLUDED.form,
                        selected_by_percent = EXCLUDED.selected_by_percent, status = EXCLUDED.status,
                        cost_change_event = EXCLUDED.cost_change_event, cost_change_start = EXCLUDED.cost_change_start,
                        cost_change_event_fall = EXCLUDED.cost_change_event_fall, cost_change_start_fall = EXCLUDED.cost_change_start_fall,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    player['id'], player['web_name'], 
                    player.get('first_name'), player.get('second_name'),
                    team_id, player['element_type'], player['now_cost'], 
                    player.get('total_points', 0), player.get('event_points', 0),
                    player.get('points_per_game'), player.get('form'),
                    player.get('selected_by_percent'), player.get('status'),
                    player.get('cost_change_event', 0), player.get('cost_change_start', 0),
                    player.get('cost_change_event_fall', 0), player.get('cost_change_start_fall', 0)
                ))
                except Exception as e:
                    print(f"❌ Error inserting player {player['web_name']}: {e}")
                    continue
            self.db_conn.commit()

    def populate_gameweeks(self):
        """Populate gameweeks table from bootstrap-static"""
        data = self.fetch_fpl_data("bootstrap-static")
        if not data or 'events' not in data:
            print("❌ No gameweeks data found")
            return

        with self.db_conn.cursor() as cur:
            for event in data['events']:
                cur.execute("""
                    INSERT INTO gameweeks (
                        id, name, deadline_time, finished, is_previous, is_current, is_next
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name, deadline_time = EXCLUDED.deadline_time,
                        finished = EXCLUDED.finished, is_previous = EXCLUDED.is_previous,
                        is_current = EXCLUDED.is_current, is_next = EXCLUDED.is_next,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    event['id'], event['name'], event.get('deadline_time'),
                    event.get('finished', False), event.get('is_previous', False),
                    event.get('is_current', False), event.get('is_next', False)
                ))
            self.db_conn.commit()

    def populate_fixtures(self):
        """Populate fixtures table from fixtures endpoint"""
        data = self.fetch_fpl_data("fixtures")
        if not data:
            print("❌ No fixtures data found")
            return

        with self.db_conn.cursor() as cur:
            for fixture in data:
                # Get database team IDs from FPL team IDs
                cur.execute("SELECT id FROM teams WHERE fpl_id = %s", (fixture['team_h'],))
                team_h_result = cur.fetchone()
                if not team_h_result:
                    print(f"⚠️ Home team ID {fixture['team_h']} not found for fixture {fixture['id']}")
                    continue
                
                cur.execute("SELECT id FROM teams WHERE fpl_id = %s", (fixture['team_a'],))
                team_a_result = cur.fetchone()
                if not team_a_result:
                    print(f"⚠️ Away team ID {fixture['team_a']} not found for fixture {fixture['id']}")
                    continue
                
                team_h_id = team_h_result[0]
                team_a_id = team_a_result[0]
                
                # Convert FPL API UTC time to proper UTC timestamp
                kickoff_time = fixture.get('kickoff_time')
                if kickoff_time:
                    # FPL API provides time in format "2025-08-31T18:00:00Z" (UTC)
                    # Convert to UTC timestamp for database storage
                    from datetime import datetime
                    import pytz
                    
                    # Parse the UTC time string and ensure it's treated as UTC
                    if kickoff_time.endswith('Z'):
                        # Remove 'Z' and parse as UTC
                        utc_time_str = kickoff_time[:-1]
                        utc_time = datetime.fromisoformat(utc_time_str)
                        utc_time = utc_time.replace(tzinfo=pytz.UTC)
                        kickoff_time = utc_time
                    else:
                        # If no 'Z', assume it's already UTC
                        kickoff_time = datetime.fromisoformat(kickoff_time)
                        kickoff_time = kickoff_time.replace(tzinfo=pytz.UTC)
                
                cur.execute("""
                    INSERT INTO fixtures (
                        id, event_id, team_h, team_a, team_h_score, team_a_score,
                        kickoff_time, started, finished, minutes,
                        team_h_difficulty, team_a_difficulty
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        team_h_score = EXCLUDED.team_h_score, team_a_score = EXCLUDED.team_a_score,
                        started = EXCLUDED.started, finished = EXCLUDED.finished,
                        minutes = EXCLUDED.minutes, updated_at = CURRENT_TIMESTAMP
                """, (
                    fixture['id'], fixture['event'], team_h_id, team_a_id,
                    fixture.get('team_h_score'), fixture.get('team_a_score'),
                    kickoff_time, fixture.get('started', False),
                    fixture.get('finished', False), fixture.get('minutes', 0),
                    fixture.get('team_h_difficulty'), fixture.get('team_a_difficulty')
                ))
            self.db_conn.commit()

    def populate_gameweek_stats(self):
        """Populate ONLY current gameweek stats (ignore historical data)"""

        
        # Get current gameweek
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT id, name FROM gameweeks WHERE is_current = TRUE")
            result = cur.fetchone()
            if not result:
                print("❌ No current gameweek found")
                return
            current_gameweek_id, current_gameweek_name = result

        # Only populate current gameweek stats
        
        # Only populate current gameweek stats
        self.populate_specific_gameweek_stats(current_gameweek_id)

    def populate_specific_gameweek_stats(self, gameweek: int):
        """Populate stats for ONLY the current gameweek (safety check)"""
        # Safety check: Only allow updates to current gameweek
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT is_current FROM gameweeks WHERE id = %s", (gameweek,))
            result = cur.fetchone()
            if not result or not result[0]:
                print(f"❌ Safety check failed: Gameweek {gameweek} is not current")
                print("🔒 Only current gameweek stats can be updated")
                return
        

        
        # Fetch live data for the gameweek
        live_data = self.fetch_fpl_data(f"event/{gameweek}/live")
        if not live_data or 'elements' not in live_data:
            print(f"❌ No live data found for gameweek {gameweek}")
            return

        with self.db_conn.cursor() as cur:
            # Handle both dict and list formats from FPL API
            elements = live_data['elements']
            if isinstance(elements, list):
                # If it's a list, convert to dict format
                elements_dict = {}
                for element in elements:
                    if 'id' in element:
                        elements_dict[str(element['id'])] = element
                elements = elements_dict
            
            for player_id, player_data in elements.items():
                # Get player info
                cur.execute("SELECT id, element_type FROM players WHERE fpl_id = %s", (int(player_id),))
                player_result = cur.fetchone()
                if not player_result:
                    continue
                
                player_db_id, element_type = player_result
                
                # Get fixture info for this player
                cur.execute("""
                    SELECT f.id FROM fixtures f 
                    JOIN players p ON p.team_id = f.team_h OR p.team_id = f.team_a
                    WHERE p.id = %s AND f.event_id = %s
                """, (player_db_id, gameweek))
                fixture_result = cur.fetchone()
                if not fixture_result:
                    continue
                
                fixture_id = fixture_result[0]
                stats = player_data.get('stats', {})
                
                # Now let's populate all the rich data we actually get from FPL API
                try:
                    cur.execute("""
                        INSERT INTO gameweek_stats (
                            player_id, fixture_id, gameweek, minutes,
                            goals_scored, assists, clean_sheets, goals_conceded,
                            own_goals, penalties_saved, penalties_missed,
                            yellow_cards, red_cards, saves, bonus, bps,
                            influence, creativity, threat, ict_index,
                            expected_goals, expected_assists, defensive_contribution,
                            tackles, clearances_blocks_interceptions, recoveries, starts
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (player_id, fixture_id, gameweek) DO UPDATE SET
                            minutes = EXCLUDED.minutes, goals_scored = EXCLUDED.goals_scored,
                            assists = EXCLUDED.assists, clean_sheets = EXCLUDED.clean_sheets,
                            goals_conceded = EXCLUDED.goals_conceded, own_goals = EXCLUDED.own_goals,
                            penalties_saved = EXCLUDED.penalties_saved, penalties_missed = EXCLUDED.penalties_missed,
                            yellow_cards = EXCLUDED.yellow_cards, red_cards = EXCLUDED.red_cards,
                            saves = EXCLUDED.saves, bonus = EXCLUDED.bonus, bps = EXCLUDED.bps,
                            influence = EXCLUDED.influence, creativity = EXCLUDED.creativity,
                            threat = EXCLUDED.threat, ict_index = EXCLUDED.ict_index,
                            expected_goals = EXCLUDED.expected_goals, expected_assists = EXCLUDED.expected_assists,
                            defensive_contribution = EXCLUDED.defensive_contribution,
                            tackles = EXCLUDED.tackles, clearances_blocks_interceptions = EXCLUDED.clearances_blocks_interceptions,
                            recoveries = EXCLUDED.recoveries, starts = EXCLUDED.starts,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        player_db_id, fixture_id, gameweek,
                        stats.get('minutes', 0), stats.get('goals_scored', 0),
                        stats.get('assists', 0), stats.get('clean_sheets', 0),
                        stats.get('goals_conceded', 0), stats.get('own_goals', 0),
                        stats.get('penalties_saved', 0), stats.get('penalties_missed', 0),
                        stats.get('yellow_cards', 0), stats.get('red_cards', 0),
                        stats.get('saves', 0), stats.get('bonus', 0), stats.get('bps', 0),
                        stats.get('influence', 0), stats.get('creativity', 0),
                        stats.get('threat', 0), stats.get('ict_index', 0),
                        stats.get('expected_goals', 0), stats.get('expected_assists', 0),
                        stats.get('defensive_contribution', 0), stats.get('tackles', 0),
                        stats.get('clearances_blocks_interceptions', 0), stats.get('recoveries', 0),
                        stats.get('starts', 0)
                    ))
                except Exception as e:
                    print(f"❌ Error inserting stats for player {player_db_id}: {e}")
                    continue
            
            self.db_conn.commit()

    def get_fixture_minutes(self, player_id: int) -> int:
        """Get the current minutes played for a player's fixture"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT gs.minutes
                    FROM gameweek_stats gs
                    WHERE gs.player_id = %s
                    LIMIT 1
                """, (player_id,))
                
                result = cur.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            return 0

    def run_refresh(self, monitor_changes: bool = True):
        """Main refresh function with temp table versioning for accurate change detection"""
        
        try:
            # Connect to database
            self.connect_db()
            
            # Create temp versions BEFORE refresh (to avoid false positives)
            if monitor_changes:
                self.initialize_temp_tables()
                self.create_temp_version('gameweek_stats')
                self.create_temp_version('players')
            
            # Populate all tables with fresh data
            self.populate_teams()
            self.populate_players()
            self.populate_gameweeks()
            self.populate_fixtures()
            self.populate_gameweek_stats()
            
            # Detect and process changes using comprehensive detection (includes BPS bonus tracking)
            if monitor_changes:
                self.detect_and_process_changes_comprehensive()
            
        except Exception as e:
            # Clean up temp tables on error
            if self.temp_tables:
                for temp_table in self.temp_tables.values():
                    self.drop_temp_version(temp_table)
        finally:
            self.close_db()

    def confirm_shutdown(self) -> bool:
        """Simple confirmation prompt"""
        print()  # Add newline before prompt
        print("Stop monitoring? (y/n): ", end='', flush=True)
        
        while True:
            try:
                response = input().lower().strip()
                if response in ['y', 'yes']:
                    return True
                elif response in ['n', 'no']:
                    return False
                else:
                    print("Please enter 'y' or 'n': ", end='', flush=True)
            except (EOFError, KeyboardInterrupt):
                return False

def main():
    # Create refresh instance and start persistent monitoring
    refresh = FPLRefresh()
    
    try:
        print("🚀 Starting FPL Live Monitor...")
        print("Press Ctrl+C to stop monitoring")
        refresh.start_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Stopping FPL Monitor...")
        refresh.stop_monitoring()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    finally:
        print()  # Ensure clean terminal output on exit
