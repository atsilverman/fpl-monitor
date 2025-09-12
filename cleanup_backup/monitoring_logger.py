#!/usr/bin/env python3
"""
Monitoring Logger
================
Utility class for logging monitoring service runs to track uptime and detect outages.
"""

import os
import time
import psycopg2
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

class MonitoringLogger:
    """Logs monitoring service runs to track uptime and detect outages"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.db_conn = None
        self._connect_db()
    
    def _connect_db(self):
        """Connect to database"""
        try:
            self.db_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        except Exception as e:
            print(f"Failed to connect to database for monitoring logger: {e}")
            self.db_conn = None
    
    def _execute_query(self, query: str, params: tuple = None) -> Optional[Any]:
        """Execute a database query"""
        if not self.db_conn:
            return None
        
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return cur.fetchone()
                else:
                    self.db_conn.commit()
                    return cur.fetchone()[0] if cur.rowcount > 0 else None
        except Exception as e:
            print(f"Database query failed: {e}")
            return None
    
    def log_heartbeat(self, run_type: str = "heartbeat", metadata: Dict[str, Any] = None) -> Optional[int]:
        """Log a simple heartbeat to show service is alive"""
        return self.log_start(run_type, metadata)
    
    def log_start(self, run_type: str, metadata: Dict[str, Any] = None) -> Optional[int]:
        """Log the start of a monitoring run"""
        query = """
            INSERT INTO monitoring_log (service_name, run_type, status, metadata)
            VALUES (%s, %s, 'running', %s)
            RETURNING id
        """
        return self._execute_query(query, (self.service_name, run_type, metadata))
    
    def log_complete(self, log_id: int, status: str = "success", 
                    records_processed: int = 0, changes_detected: int = 0,
                    notifications_sent: int = 0, error_message: str = None):
        """Log the completion of a monitoring run"""
        query = """
            UPDATE monitoring_log 
            SET 
                status = %s,
                completed_at = NOW(),
                duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER,
                records_processed = %s,
                changes_detected = %s,
                notifications_sent = %s,
                error_message = %s
            WHERE id = %s
        """
        self._execute_query(query, (status, records_processed, changes_detected, 
                                  notifications_sent, error_message, log_id))
    
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
        query = """
            SELECT 
                service_name,
                run_type,
                status,
                started_at,
                completed_at,
                duration_seconds,
                records_processed,
                changes_detected,
                notifications_sent,
                error_message,
                CASE 
                    WHEN completed_at IS NULL THEN 'running'
                    WHEN started_at > NOW() - INTERVAL '5 minutes' THEN 'recent'
                    WHEN started_at > NOW() - INTERVAL '1 hour' THEN 'stale'
                    ELSE 'offline'
                END as health_status
            FROM monitoring_log
            WHERE service_name = %s
            ORDER BY started_at DESC
            LIMIT 1
        """
        result = self._execute_query(query, (self.service_name,))
        if result:
            return {
                'service_name': result[0],
                'run_type': result[1],
                'status': result[2],
                'started_at': result[3],
                'completed_at': result[4],
                'duration_seconds': result[5],
                'records_processed': result[6],
                'changes_detected': result[7],
                'notifications_sent': result[8],
                'error_message': result[9],
                'health_status': result[10]
            }
        return None
    
    def get_all_services_status(self) -> list:
        """Get status of all monitoring services"""
        query = """
            SELECT 
                service_name,
                run_type,
                status,
                started_at,
                completed_at,
                duration_seconds,
                records_processed,
                changes_detected,
                notifications_sent,
                error_message,
                CASE 
                    WHEN completed_at IS NULL THEN 'running'
                    WHEN started_at > NOW() - INTERVAL '5 minutes' THEN 'recent'
                    WHEN started_at > NOW() - INTERVAL '1 hour' THEN 'stale'
                    ELSE 'offline'
                END as health_status
            FROM monitoring_log
            WHERE id IN (
                SELECT MAX(id) 
                FROM monitoring_log 
                GROUP BY service_name
            )
            ORDER BY started_at DESC
        """
        if not self.db_conn:
            return []
        
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(query)
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            print(f"Failed to get services status: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()

# Convenience functions for quick status checks
def check_monitoring_status():
    """Quick function to check all monitoring services status"""
    logger = MonitoringLogger("status_checker")
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
        logger.close()

if __name__ == "__main__":
    # Quick test of the monitoring logger
    check_monitoring_status()
