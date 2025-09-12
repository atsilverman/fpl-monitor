#!/usr/bin/env python3
"""
Setup Monitoring Log Table
=========================
Creates the monitoring_log table and sets up the monitoring system.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

def setup_monitoring_log():
    """Create the monitoring_log table and related functions"""
    load_dotenv()
    
    try:
        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        print("🔧 Setting up monitoring log table...")
        
        # Read and execute the schema
        with open(os.path.join(os.path.dirname(__file__), '..', 'database', 'monitoring_log_schema.sql'), 'r') as f:
            schema_sql = f.read()
        
        # Execute the schema
        cur.execute(schema_sql)
        conn.commit()
        
        print("✅ Monitoring log table created successfully!")
        
        # Test the monitoring logger
        print("\n🧪 Testing monitoring logger...")
        from services.monitoring_logger import MonitoringLogger
        
        logger = MonitoringLogger("setup_test")
        log_id = logger.log_heartbeat("setup_test", {"test": True})
        logger.log_complete(log_id, "success", records_processed=1)
        
        print("✅ Monitoring logger test successful!")
        
        # Show current status
        print("\n📊 Current monitoring status:")
        services = logger.get_all_services_status()
        for service in services:
            health_emoji = {
                'running': '🟢',
                'recent': '🟢', 
                'stale': '🟡',
                'offline': '🔴'
            }.get(service['health_status'], '❓')
            
            print(f"{health_emoji} {service['service_name']} - {service['health_status']}")
            print(f"   Last run: {service['started_at']}")
            print(f"   Status: {service['status']}")
            print()
        
        logger.close()
        cur.close()
        conn.close()
        
        print("🎉 Setup complete! You can now:")
        print("   1. Run monitoring services with heartbeat logging")
        print("   2. Check status with: python3 scripts/tools/check_monitoring_status.py")
        print("   3. Query monitoring_log table directly for detailed logs")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    setup_monitoring_log()
