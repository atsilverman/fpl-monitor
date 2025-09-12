#!/usr/bin/env python3
"""
Simple Monitoring Logger
=======================
A simplified monitoring logger that uses direct HTTP requests to Supabase.
Avoids dependency issues with the Supabase client.
"""

import os
import time
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

class SimpleMonitoringLogger:
    """Simple monitoring logger using direct HTTP requests to Supabase"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            print("Missing Supabase credentials in .env file")
            self.supabase_url = None
            self.supabase_key = None
        else:
            print(f"Monitoring logger initialized for {service_name}")
    
    def _get_headers(self):
        """Get headers for Supabase requests"""
        return {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json'
        }
    
    def log_heartbeat(self, run_type: str = "heartbeat", metadata: Dict[str, Any] = None) -> Optional[int]:
        """Log a simple heartbeat to show service is alive"""
        return self.log_start(run_type, metadata)
    
    def log_start(self, run_type: str, metadata: Dict[str, Any] = None) -> Optional[int]:
        """Log the start of a monitoring run"""
        if not self.supabase_url or not self.supabase_key:
            print("Supabase not configured")
            return None
        
        try:
            data = {
                "service_name": self.service_name,
                "run_type": run_type,
                "status": "running",
                "metadata": metadata or {}
            }
            
            response = requests.post(
                f"{self.supabase_url}/rest/v1/monitoring_log",
                headers=self._get_headers(),
                json=data,
                timeout=10
            )
            
            if response.status_code == 201:
                result = response.json()
                log_id = result[0]['id'] if result else None
                print(f"Logged start: {run_type} (ID: {log_id})")
                return log_id
            else:
                print(f"Failed to log start: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error logging start: {e}")
            return None
    
    def log_complete(self, log_id: int, status: str = "success", 
                    records_processed: int = 0, changes_detected: int = 0,
                    notifications_sent: int = 0, error_message: str = None):
        """Log the completion of a monitoring run"""
        if not self.supabase_url or not self.supabase_key:
            print("Supabase not configured")
            return
        
        try:
            # Get the start time to calculate duration
            response = requests.get(
                f"{self.supabase_url}/rest/v1/monitoring_log?id=eq.{log_id}&select=started_at",
                headers=self._get_headers(),
                timeout=10
            )
            
            duration_seconds = None
            if response.status_code == 200:
                data = response.json()
                if data:
                    start_time = datetime.fromisoformat(data[0]['started_at'].replace('Z', '+00:00'))
                    duration_seconds = int((datetime.now(timezone.utc) - start_time).total_seconds())
            
            update_data = {
                "status": status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "records_processed": records_processed,
                "changes_detected": changes_detected,
                "notifications_sent": notifications_sent,
                "error_message": error_message
            }
            
            if duration_seconds is not None:
                update_data["duration_seconds"] = duration_seconds
            
            response = requests.patch(
                f"{self.supabase_url}/rest/v1/monitoring_log?id=eq.{log_id}",
                headers=self._get_headers(),
                json=update_data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"Logged completion: {status}")
            else:
                print(f"Failed to log completion: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error logging completion: {e}")
    
    def log_error(self, log_id: int, error_message: str):
        """Log an error for a monitoring run"""
        self.log_complete(log_id, "error", error_message=error_message)
    
    @contextmanager
    def log_run(self, run_type: str, metadata: Dict[str, Any] = None):
        """Context manager for logging a complete monitoring run"""
        log_id = self.log_start(run_type, metadata)
        start_time = time.time()
        
        try:
            yield log_id
            duration = int(time.time() - start_time)
            self.log_complete(log_id, "success", duration_seconds=duration)
        except Exception as e:
            duration = int(time.time() - start_time)
            self.log_complete(log_id, "error", duration_seconds=duration, 
                            error_message=str(e))
            raise
    
    def get_all_services_status(self) -> list:
        """Get status of all monitoring services"""
        if not self.supabase_url or not self.supabase_key:
            print("Supabase not configured")
            return []
        
        try:
            # Try to get from the monitoring_status view first
            response = requests.get(
                f"{self.supabase_url}/rest/v1/monitoring_status",
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to direct table query
                response = requests.get(
                    f"{self.supabase_url}/rest/v1/monitoring_log?select=*&order=started_at.desc&limit=100",
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Group by service_name and get latest for each
                    services = {}
                    for record in data:
                        service_name = record['service_name']
                        if service_name not in services:
                            services[service_name] = record
                    
                    # Convert to list and add health_status
                    result = []
                    for record in services.values():
                        record['health_status'] = self._calculate_health_status(record)
                        result.append(record)
                    
                    return result
                else:
                    print(f"Failed to get services status: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            print(f"Error getting services status: {e}")
            return []
    
    def _calculate_health_status(self, record: dict) -> str:
        """Calculate health status based on record"""
        if record.get('completed_at') is None:
            return 'running'
        
        try:
            started_at = datetime.fromisoformat(record['started_at'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            
            if (now - started_at).total_seconds() < 300:  # 5 minutes
                return 'recent'
            elif (now - started_at).total_seconds() < 3600:  # 1 hour
                return 'stale'
            else:
                return 'offline'
        except:
            return 'unknown'

# Convenience functions for quick status checks
def check_monitoring_status():
    """Quick function to check all monitoring services status"""
    logger = SimpleMonitoringLogger("status_checker")
    try:
        services = logger.get_all_services_status()
        print("=== MONITORING SERVICES STATUS ===")
        for service in services:
            health_emoji = {
                'running': '🟢',
                'recent': 'ONLINE', 
                'stale': 'STALE',
                'offline': 'OFFLINE'
            }.get(service['health_status'], 'UNKNOWN')
            
            print(f"{health_emoji} {service['service_name']} - {service['health_status']}")
            print(f"   Last run: {service['started_at']}")
            print(f"   Status: {service['status']}")
            if service.get('error_message'):
                print(f"   Error: {service['error_message']}")
            print()
        return services
    finally:
        pass

if __name__ == "__main__":
    # Quick test of the monitoring logger
    check_monitoring_status()
