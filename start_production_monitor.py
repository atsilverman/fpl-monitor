#!/usr/bin/env python3
"""
Start FPL Event-Based Production Monitoring Service
==================================================

Scalable event-based monitoring service startup script.
This is the main entry point for the production server.
"""

import sys
import os
import asyncio
from backend.services.fpl_monitor_production import FPLMonitoringService, app

async def main():
    """Start the production monitoring service"""
    print("🚀 Starting FPL Event-Based Production Monitoring Service...")
    print("📊 Architecture: Scalable event-based (1 event = 1 record)")
    print("📈 Monitoring modes: Live Performance, Status & News, Price Changes, Final Bonus")
    
    # Initialize the monitoring service
    monitoring_service = FPLMonitoringService()
    
    # Start monitoring
    await monitoring_service.start_monitoring()
    
    # Keep the service running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping monitoring service...")
        await monitoring_service.stop_monitoring()
        print("✅ Monitoring service stopped")

if __name__ == "__main__":
    asyncio.run(main())
