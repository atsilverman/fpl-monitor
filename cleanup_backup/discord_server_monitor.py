#!/usr/bin/env python3
"""
Discord Server Monitor
======================

Monitors the FPL Monitor cloud server and sends Discord alerts when issues are detected.
This runs locally on your Mac to keep an eye on the cloud service.
"""

import requests
import json
import time
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

class DiscordServerMonitor:
    def __init__(self):
        self.server_url = "http://138.68.28.59:8000"
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.check_interval = 300  # 5 minutes
        self.last_alert_time = {}
        self.alert_cooldown = 1800  # 30 minutes between same alerts
        
        if not self.discord_webhook:
            print("❌ DISCORD_WEBHOOK_URL not found in .env file")
            print("   Add your Discord webhook URL to .env file")
            exit(1)
    
    def send_discord_alert(self, title, description, color=0xff0000, fields=None):
        """Send alert to Discord"""
        if not self.discord_webhook:
            return False
        
        # Check cooldown
        alert_key = f"{title}_{description}"
        now = datetime.now()
        if alert_key in self.last_alert_time:
            if (now - self.last_alert_time[alert_key]).seconds < self.alert_cooldown:
                return False  # Still in cooldown
        
        self.last_alert_time[alert_key] = now
        
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": now.isoformat(),
            "footer": {
                "text": "FPL Monitor Alert System"
            }
        }
        
        if fields:
            embed["fields"] = fields
        
        payload = {
            "username": "FPL Monitor Alert",
            "embeds": [embed]
        }
        
        try:
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            if response.status_code in [200, 204]:
                print(f"✅ Discord alert sent: {title}")
                return True
            else:
                print(f"❌ Discord alert failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Discord alert error: {e}")
            return False
    
    def check_server_health(self):
        """Check if server is responding"""
        try:
            response = requests.get(f"{self.server_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, data
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def check_monitoring_status(self):
        """Check monitoring service status"""
        try:
            response = requests.get(f"{self.server_url}/api/v1/monitoring/status", timeout=10)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def check_notifications_endpoint(self):
        """Check if notifications are being generated"""
        try:
            response = requests.get(f"{self.server_url}/api/v1/notifications?limit=1", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, data
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def check_fpl_api_connection(self):
        """Check if FPL API is accessible"""
        try:
            response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, len(data.get('elements', []))
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def run_health_check(self):
        """Run comprehensive health check"""
        print(f"\n🔍 Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        issues = []
        
        # Check 1: Server health
        print("1. Checking server health...")
        healthy, data = self.check_server_health()
        if healthy:
            print("   ✅ Server responding")
        else:
            print(f"   ❌ Server down: {data}")
            issues.append(f"Server down: {data}")
        
        # Check 2: Monitoring status
        print("2. Checking monitoring status...")
        monitoring_ok, status = self.check_monitoring_status()
        if monitoring_ok:
            print("   ✅ Monitoring status accessible")
            if not status.get('monitoring_active', False):
                print("   ⚠️  Monitoring not active")
                issues.append("Monitoring service not active")
            if not status.get('fpl_api_connected', False):
                print("   ⚠️  FPL API not connected")
                issues.append("FPL API connection lost")
        else:
            print(f"   ❌ Monitoring status failed: {status}")
            issues.append(f"Monitoring status failed: {status}")
        
        # Check 3: Notifications endpoint
        print("3. Checking notifications endpoint...")
        notif_ok, notif_data = self.check_notifications_endpoint()
        if notif_ok:
            print("   ✅ Notifications endpoint working")
            total = notif_data.get('total', 0)
            print(f"   📊 Total notifications: {total}")
        else:
            print(f"   ❌ Notifications endpoint failed: {notif_data}")
            issues.append(f"Notifications endpoint failed: {notif_data}")
        
        # Check 4: FPL API connection
        print("4. Checking FPL API connection...")
        fpl_ok, player_count = self.check_fpl_api_connection()
        if fpl_ok:
            print(f"   ✅ FPL API connected ({player_count} players)")
        else:
            print(f"   ❌ FPL API failed: {player_count}")
            issues.append(f"FPL API connection failed: {player_count}")
        
        # Send alerts if issues found
        if issues:
            print(f"\n🚨 Issues detected: {len(issues)}")
            for issue in issues:
                print(f"   - {issue}")
            
            # Send Discord alert
            fields = []
            for i, issue in enumerate(issues, 1):
                fields.append({
                    "name": f"Issue {i}",
                    "value": issue,
                    "inline": False
                })
            
            self.send_discord_alert(
                "🚨 FPL Monitor Alert",
                f"Detected {len(issues)} issue(s) with your FPL Monitor service:",
                color=0xff0000,
                fields=fields
            )
        else:
            print("\n✅ All systems healthy")
            
            # Send periodic "all good" message (once per hour)
            now = datetime.now()
            if "all_good" not in self.last_alert_time or \
               (now - self.last_alert_time["all_good"]).seconds > 3600:
                self.send_discord_alert(
                    "✅ FPL Monitor Status",
                    "All systems are running normally. No issues detected.",
                    color=0x00ff00
                )
                self.last_alert_time["all_good"] = now
        
        return len(issues) == 0
    
    async def start_monitoring(self):
        """Start continuous monitoring"""
        print("🚀 Starting Discord Server Monitor")
        print("=" * 40)
        print(f"Monitoring server: {self.server_url}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Discord webhook: {'✅ Set' if self.discord_webhook else '❌ Not set'}")
        print("\nPress Ctrl+C to stop monitoring")
        
        # Send startup alert
        self.send_discord_alert(
            "🚀 FPL Monitor Alert System Started",
            f"Now monitoring your FPL Monitor service at {self.server_url}",
            color=0x0099ff
        )
        
        try:
            while True:
                self.run_health_check()
                await asyncio.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping Discord Server Monitor...")
            self.send_discord_alert(
                "🛑 FPL Monitor Alert System Stopped",
                "Discord monitoring has been stopped.",
                color=0xff9900
            )
            print("✅ Monitor stopped")

def main():
    """Main function"""
    monitor = DiscordServerMonitor()
    
    try:
        asyncio.run(monitor.start_monitoring())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
