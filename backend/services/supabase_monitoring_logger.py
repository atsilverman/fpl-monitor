#!/usr/bin/env python3
"""
Supabase Monitoring Logger
=========================
Utility class for logging monitoring service runs to track uptime and detect outages.
Uses Supabase client instead of direct PostgreSQL connection.
"""

import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv

# Try to import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Supabase client not available. Install with: pip install supabase")

load_dotenv()

class SupabaseMonitoringLogger:
    """Logs monitoring service runs to track uptime and detect outages using Supabase"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.supabase = None
        self._connect_supabase()
    
    def _connect_supabase(self):
        """Connect to Supabase"""
        if not SUPABASE_AVAILABLE:
            print("Supabase client not available")
            return
        
        try:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not url or not key:
                print("Missing Supabase credentials in .env file")
                return
            
            self.supabase = create_client(url, key)
            print(f"Connected to Supabase for monitoring logger")
        except Exception as e:
            print(f"Failed to connect to Supabase: {e}")
            self.supabase = None
    
    def _execute_query(self, query: str, params: dict = None) -> Optional[Any]:
        """Execute a Supabase query"""
        if not self.supabase:
            return None
        
        try:
            # For simple queries, we'll use the REST API
            if "INSERT" in query.upper():
                # Extract values from INSERT query
                # This is a simplified approach - in production you'd want a more robust parser
                return self._insert_record(query, params)
            elif "SELECT" in query.upper():
                return self._select_records(query, params)
            elif "UPDATE" in query.upper():
                return self._update_record(query, params)
        except Exception as e:
            print(f"Supabase query failed: {e}")
            return None
    
    def _insert_record(self, query: str, params: dict) -> Optional[int]:
        """Insert a record and return the ID"""
        try:
            # Parse the INSERT query to extract table and values
            # This is a simplified approach
            if "monitoring_log" in query:
                data = {
                    "service_name": params[0] if params else self.service_name,
                    "run_type": params[1] if params and len(params) > 1 else "heartbeat",
                    "status": "running",
                    "metadata": params[2] if params and len(params) > 2 else None
                }
                result = self.supabase.table('monitoring_log').insert(data).execute()
                return result.data[0]['id'] if result.data else None
        except Exception as e:
            print(f"Insert failed: {e}")
            return None
    
    def _select_records(self, query: str, params: dict) -> Optional[list]:
        """Select records from Supabase"""
        try:
            if "monitoring_status" in query:
                # Use the view
                result = self.supabase.table('monitoring_status').select('*').execute()
                return result.data
            elif "monitoring_log" in query:
                # Query the table directly
                result = self.supabase.table('monitoring_log').select('*').order('started_at', desc=True).limit(1).execute()
                return result.data
        except Exception as e:
            print(f"Select failed: {e}")
            return None
    
    def _update_record(self, query: str, params: dict) -> bool:
        """Update a record in Supabase"""
        try:
            if "monitoring_log" in query:
                log_id = params[-1] if params else None
                if log_id:
                    update_data = {
                        "status": params[0] if params else "success",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "records_processed": params[1] if params and len(params) > 1 else 0,
                        "changes_detected": params[2] if params and len(params) > 2 else 0,
                        "notifications_sent": params[3] if params and len(params) > 3 else 0,
                        "error_message": params[4] if params and len(params) > 4 else None
                    }
                    # Calculate duration
                    if params and len(params) > 5:
                        update_data["duration_seconds"] = params[5]
                    
                    self.supabase.table('monitoring_log').update(update_data).eq('id', log_id).execute()
                    return True
        except Exception as e:
            print(f"Update failed: {e}")
            return False
        
        return False
    
    def log_heartbeat(self, run_type: str = "heartbeat", metadata: Dict[str, Any] = None) -> Optional[int]:
        """Log a simple heartbeat to show service is alive"""
        return self.log_start(run_type, metadata)
    
    def log_start(self, run_type: str, metadata: Dict[str, Any] = None) -> Optional[int]:
        """Log the start of a monitoring run"""
        try:
            data = {
                "service_name": self.service_name,
                "run_type": run_type,
                "status": "running",
                "metadata": metadata
            }
            result = self.supabase.table('monitoring_log').insert(data).execute()
            return result.data[0]['id'] if result.data else None
        except Exception as e:
            print(f"Failed to log start: {e}")
            return None
    
    def log_complete(self, log_id: int, status: str = "success", 
                    records_processed: int = 0, changes_detected: int = 0,
                    notifications_sent: int = 0, error_message: str = None):
        """Log the completion of a monitoring run"""
        try:
            update_data = {
                "status": status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "records_processed": records_processed,
                "changes_detected": changes_detected,
                "notifications_sent": notifications_sent,
                "error_message": error_message
            }
            
            # Get the start time to calculate duration
            result = self.supabase.table('monitoring_log').select('started_at').eq('id', log_id).execute()
            if result.data:
                start_time = datetime.fromisoformat(result.data[0]['started_at'].replace('Z', '+00:00'))
                duration = int((datetime.now(timezone.utc) - start_time).total_seconds())
                update_data["duration_seconds"] = duration
            
            self.supabase.table('monitoring_log').update(update_data).eq('id', log_id).execute()
        except Exception as e:
            print(f"Failed to log completion: {e}")
    
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
    
    def get_latest_status(self) -> Optional[Dict[str, Any]]:
        """Get the latest status of this service"""
        try:
            result = self.supabase.table('monitoring_log').select('*').eq('service_name', self.service_name).order('started_at', desc=True).limit(1).execute()
            if result.data:
                record = result.data[0]
                return {
                    'service_name': record['service_name'],
                    'run_type': record['run_type'],
                    'status': record['status'],
                    'started_at': record['started_at'],
                    'completed_at': record['completed_at'],
                    'duration_seconds': record['duration_seconds'],
                    'records_processed': record['records_processed'],
                    'changes_detected': record['changes_detected'],
                    'notifications_sent': record['notifications_sent'],
                    'error_message': record['error_message'],
                    'health_status': self._calculate_health_status(record)
                }
        except Exception as e:
            print(f"Failed to get latest status: {e}")
        return None
    
    def get_all_services_status(self) -> list:
        """Get status of all monitoring services"""
        try:
            # Use the monitoring_status view
            result = self.supabase.table('monitoring_status').select('*').execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Failed to get services status: {e}")
            return []
    
    def _calculate_health_status(self, record: dict) -> str:
        """Calculate health status based on record"""
        if record['completed_at'] is None:
            return 'running'
        
        started_at = datetime.fromisoformat(record['started_at'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if (now - started_at).total_seconds() < 300:  # 5 minutes
            return 'recent'
        elif (now - started_at).total_seconds() < 3600:  # 1 hour
            return 'stale'
        else:
            return 'offline'

# Convenience functions for quick status checks
def check_monitoring_status():
    """Quick function to check all monitoring services status"""
    logger = SupabaseMonitoringLogger("status_checker")
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
            if service['error_message']:
                print(f"   Error: {service['error_message']}")
            print()
        return services
    finally:
        pass  # No need to close Supabase client

if __name__ == "__main__":
    # Quick test of the monitoring logger
    check_monitoring_status()
