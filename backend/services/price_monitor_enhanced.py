#!/usr/bin/env python3
"""
ENHANCED PRICE MONITORING SERVICE
================================

This service addresses the critical issues with price change detection:
1. Persistent state storage in database
2. More frequent monitoring during price windows
3. Backup detection methods
4. Proper time window detection
5. Comprehensive logging and alerting

Usage:
    python3 price_monitor_enhanced.py
"""

import os
import sys
import time
import json
import psycopg2
import requests
import pytz
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

class EnhancedPriceMonitor:
    def __init__(self):
        load_dotenv()
        self.db_conn = None
        self.fpl_base_url = "https://fantasy.premierleague.com/api"
        
        # Enhanced monitoring configuration
        self.config = {
            'price_window_start': 18,  # 6 PM
            'price_window_start_minute': 30,  # 6:30 PM
            'price_window_end_minute': 40,    # 6:40 PM
            'refresh_interval_normal': 3600,  # 1 hour
            'refresh_interval_price_window': 30,  # 30 seconds during price window
            'refresh_interval_high_alert': 10,    # 10 seconds when changes detected
        }
        
        self.setup_logging()
        self.connect_db()
        self.initialize_price_history()

    def setup_logging(self):
        """Setup comprehensive logging"""
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('price_monitor.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def connect_db(self):
        """Connect to database"""
        try:
            self.db_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            self.logger.info("Connected to database")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def initialize_price_history(self):
        """Initialize price history table for persistent state storage"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS price_history (
                        id SERIAL PRIMARY KEY,
                        fpl_id INTEGER NOT NULL,
                        price INTEGER NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        change_detected BOOLEAN DEFAULT FALSE,
                        UNIQUE(fpl_id, timestamp)
                    )
                """)
                self.db_conn.commit()
                self.logger.info("Price history table initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize price history: {e}")

    def is_price_window(self) -> bool:
        """Check if current time is within FPL price update window"""
        utc_now = datetime.now(timezone.utc)
        pacific_time = utc_now.astimezone(pytz.timezone('America/Los_Angeles'))
        
        hour = pacific_time.hour
        minute = pacific_time.minute
        
        # Correct logic: 6:30-6:40 PM Pacific Time
        is_window = (hour == self.config['price_window_start'] and 
                    minute >= self.config['price_window_start_minute'] and 
                    minute < self.config['price_window_end_minute'])
        
        return is_window

    def get_current_prices_from_api(self) -> Dict[int, int]:
        """Fetch current prices from FPL API"""
        try:
            response = requests.get(f"{self.fpl_base_url}/bootstrap-static/", timeout=30)
            response.raise_for_status()
            data = response.json()
            
            prices = {}
            for player in data.get('elements', []):
                prices[player['id']] = player['now_cost']
            
            return prices
        except Exception as e:
            self.logger.error(f"Failed to fetch FPL API data: {e}")
            return {}

    def get_latest_prices_from_db(self) -> Dict[int, int]:
        """Get latest prices from database"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ON (fpl_id) fpl_id, price
                    FROM price_history
                    ORDER BY fpl_id, timestamp DESC
                """)
                return dict(cur.fetchall())
        except Exception as e:
            self.logger.error(f"Failed to get latest prices from DB: {e}")
            return {}

    def store_price_snapshot(self, prices: Dict[int, int], change_detected: bool = False):
        """Store current price snapshot in database"""
        try:
            with self.db_conn.cursor() as cur:
                for fpl_id, price in prices.items():
                    cur.execute("""
                        INSERT INTO price_history (fpl_id, price, change_detected)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (fpl_id, timestamp) DO NOTHING
                    """, (fpl_id, price, change_detected))
                self.db_conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to store price snapshot: {e}")

    def detect_price_changes(self) -> List[Dict]:
        """Detect price changes using multiple methods"""
        changes = []
        
        # Method 1: Compare with previous database snapshot
        current_prices = self.get_current_prices_from_api()
        if not current_prices:
            return changes
            
        previous_prices = self.get_latest_prices_from_db()
        
        for fpl_id, current_price in current_prices.items():
            if fpl_id in previous_prices:
                previous_price = previous_prices[fpl_id]
                if current_price != previous_price:
                    change = current_price - previous_price
                    changes.append({
                        'fpl_id': fpl_id,
                        'old_price': previous_price,
                        'new_price': current_price,
                        'change': change,
                        'change_percent': (change / previous_price) * 100 if previous_price > 0 else 0
                    })
        
        # Method 2: Compare with database current state
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT p.fpl_id, p.now_cost, p.web_name, t.short_name as team_name
                    FROM players p
                    JOIN teams t ON p.team_id = t.id
                """)
                
                db_players = cur.fetchall()
                
                for fpl_id, db_price, web_name, team_name in db_players:
                    if fpl_id in current_prices:
                        api_price = current_prices[fpl_id]
                        if api_price != db_price:
                            # This is a change that wasn't caught by method 1
                            change = api_price - db_price
                            changes.append({
                                'fpl_id': fpl_id,
                                'player_name': web_name,
                                'team_name': team_name,
                                'old_price': db_price,
                                'new_price': api_price,
                                'change': change,
                                'change_percent': (change / db_price) * 100 if db_price > 0 else 0,
                                'detection_method': 'db_vs_api'
                            })
        except Exception as e:
            self.logger.error(f"Failed to compare with database: {e}")
        
        return changes

    def send_price_change_notification(self, changes: List[Dict]):
        """Send notification for price changes"""
        if not changes:
            return
            
        # Group changes by type
        increases = [c for c in changes if c['change'] > 0]
        decreases = [c for c in changes if c['change'] < 0]
        
        message = "💰 **FPL PRICE CHANGES DETECTED**\n\n"
        
        if increases:
            message += "📈 **PRICE INCREASES:**\n"
            for change in increases[:10]:  # Limit to top 10
                player_name = change.get('player_name', f'Player {change["fpl_id"]}')
                team_name = change.get('team_name', '')
                old_price = change['old_price'] / 10
                new_price = change['new_price'] / 10
                change_amount = change['change'] / 10
                message += f"• {player_name} ({team_name}): {old_price:.1f}m → {new_price:.1f}m (+{change_amount:.1f}m)\n"
            message += "\n"
        
        if decreases:
            message += "📉 **PRICE DECREASES:**\n"
            for change in decreases[:10]:  # Limit to top 10
                player_name = change.get('player_name', f'Player {change["fpl_id"]}')
                team_name = change.get('team_name', '')
                old_price = change['old_price'] / 10
                new_price = change['new_price'] / 10
                change_amount = change['change'] / 10
                message += f"• {player_name} ({team_name}): {old_price:.1f}m → {new_price:.1f}m ({change_amount:.1f}m)\n"
        
        # Send notification (implement your Discord/webhook logic here)
        self.logger.info(f"Price changes detected: {len(changes)} changes")
        print(message)  # For now, just print to console

    def update_database_prices(self, prices: Dict[int, int]):
        """Update database with current prices"""
        try:
            with self.db_conn.cursor() as cur:
                for fpl_id, price in prices.items():
                    cur.execute("""
                        UPDATE players 
                        SET now_cost = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE fpl_id = %s
                    """, (price, fpl_id))
                self.db_conn.commit()
                self.logger.info(f"Updated {len(prices)} player prices in database")
        except Exception as e:
            self.logger.error(f"Failed to update database prices: {e}")

    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        try:
            # Get current prices from API
            current_prices = self.get_current_prices_from_api()
            if not current_prices:
                self.logger.warning("No price data from API")
                return
            
            # Detect changes
            changes = self.detect_price_changes()
            
            if changes:
                self.logger.info(f"Detected {len(changes)} price changes")
                self.send_price_change_notification(changes)
                self.store_price_snapshot(current_prices, change_detected=True)
                self.update_database_prices(current_prices)
            else:
                self.logger.info("No price changes detected")
                self.store_price_snapshot(current_prices, change_detected=False)
                self.update_database_prices(current_prices)
                
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")

    def start_monitoring(self):
        """Start the enhanced price monitoring service"""
        self.logger.info("🚀 Starting Enhanced Price Monitor...")
        
        last_price_window = False
        changes_detected_this_window = False
        
        try:
            while True:
                current_time = datetime.now()
                pacific_time = current_time.astimezone(pytz.timezone('America/Los_Angeles'))
                
                is_price_window = self.is_price_window()
                
                # Log state changes
                if is_price_window != last_price_window:
                    if is_price_window:
                        self.logger.info("💰 PRICE WINDOW STARTED - Switching to high-frequency monitoring")
                        changes_detected_this_window = False
                    else:
                        self.logger.info("💰 PRICE WINDOW ENDED - Switching to normal monitoring")
                        changes_detected_this_window = False
                    last_price_window = is_price_window
                
                # Run monitoring cycle
                self.run_monitoring_cycle()
                
                # Determine sleep interval
                if is_price_window:
                    if changes_detected_this_window:
                        sleep_interval = self.config['refresh_interval_high_alert']
                        self.logger.info("High alert mode - checking every 10 seconds")
                    else:
                        sleep_interval = self.config['refresh_interval_price_window']
                        self.logger.info("Price window mode - checking every 30 seconds")
                else:
                    sleep_interval = self.config['refresh_interval_normal']
                    self.logger.info("Normal mode - checking every hour")
                
                # Display status
                status = "PRICE WINDOW" if is_price_window else "NORMAL"
                print(f"🎮 {pacific_time.strftime('%H:%M:%S')} | {status} | Sleep: {sleep_interval}s")
                
                time.sleep(sleep_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
        finally:
            if self.db_conn:
                self.db_conn.close()

def main():
    monitor = EnhancedPriceMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()

