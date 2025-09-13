# 🚀 Event-Based Architecture Deployment Guide

## Overview

This guide deploys the new scalable event-based FPL monitoring system, replacing the old per-user notification approach.

## ⚠️ Important: Single Service Deployment

**CRITICAL**: This deployment ensures only ONE monitoring service runs at a time to prevent conflicts.

## Pre-Deployment Checklist

- [ ] Database migration script ready
- [ ] New monitoring service tested
- [ ] Old service identified and will be stopped
- [ ] Backup of current system (optional)

## Deployment Steps

### Step 1: Clean Up Old Monitoring

```bash
# Run cleanup script to remove old files
./scripts/deployment/cleanup_old_monitoring.sh
```

This will:
- Stop the existing monitoring service
- Remove old monitoring files
- Clean up Python cache files
- Verify no conflicting processes

### Step 2: Deploy New Architecture

```bash
# Deploy the new event-based system
python3 scripts/deployment/deploy_events_architecture.py
```

This will:
- Run database migration
- Deploy new monitoring service
- Update systemd service
- Start new service
- Test API endpoints

### Step 3: Verify Deployment

```bash
# Check service status
ssh root@138.68.28.59 'systemctl status fpl-monitor --no-pager'

# Test API endpoints
curl http://138.68.28.59:8000/
curl http://138.68.28.59:8000/api/v1/events/recent

# Run comprehensive test
python3 scripts/tools/test_events_architecture.py
```

## What Gets Deployed

### ✅ New Files
- `backend/services/fpl_monitor_production.py` - Main monitoring service
- `start_production_monitor.py` - Startup script
- Database migration scripts
- Updated systemd service

### ❌ Removed Files
- `backend/services/fpl_monitor_enhanced_production.py` - OLD service
- `start_production_monitor.py` - OLD startup script
- Old log files

## Service Management

### Start Service
```bash
ssh root@138.68.28.59 'systemctl start fpl-monitor'
```

### Stop Service
```bash
ssh root@138.68.28.59 'systemctl stop fpl-monitor'
```

### Restart Service
```bash
ssh root@138.68.28.59 'systemctl restart fpl-monitor'
```

### View Logs
```bash
ssh root@138.68.28.59 'journalctl -u fpl-monitor -f'
```

## API Endpoints

### Health Check
```
GET http://138.68.28.59:8000/
```

### Recent Events
```
GET http://138.68.28.59:8000/api/v1/events/recent?limit=50
```

### User Notifications
```
GET http://138.68.28.59:8000/api/v1/users/{user_id}/notifications?limit=50&offset=0
```

### Update User Ownership
```
POST http://138.68.28.59:8000/api/v1/users/ownership
{
  "user_id": "uuid",
  "fpl_manager_id": 12345,
  "owned_players": [1, 2, 3, 4, 5]
}
```

## Scalability Benefits

| Metric | Old Approach | New Approach | Improvement |
|--------|-------------|--------------|-------------|
| 10K users, 1K events/day | 10M records/day | 1K records/day | **10,000x** |
| Annual storage | 3.65B records | 365K records | **99.99%** |
| Query performance | Per-user lookups | Single event queries | **Massive** |

## Troubleshooting

### Service Won't Start
```bash
# Check logs
ssh root@138.68.28.59 'journalctl -u fpl-monitor -n 50'

# Check Python path
ssh root@138.68.28.59 'ls -la /opt/fpl-monitor/backend/services/'

# Restart service
ssh root@138.68.28.59 'systemctl restart fpl-monitor'
```

### Database Issues
```bash
# Check migration status
ssh root@138.68.28.59 'psql -h db.your-project.supabase.co -U postgres -d postgres -c "SELECT COUNT(*) FROM events;"'

# Re-run migration if needed
ssh root@138.68.28.59 'psql -h db.your-project.supabase.co -U postgres -d postgres -f /tmp/migrate_to_events_architecture.sql'
```

### API Not Responding
```bash
# Check if service is running
ssh root@138.68.28.59 'ps aux | grep fpl'

# Check port binding
ssh root@138.68.28.59 'netstat -tlnp | grep 8000'

# Test locally on server
ssh root@138.68.28.59 'curl localhost:8000/'
```

## Rollback Plan

If issues occur, you can rollback:

```bash
# Stop new service
ssh root@138.68.28.59 'systemctl stop fpl-monitor'

# Restore old service (if you have backup)
# This would require restoring the old files and restarting

# Or redeploy old version
python3 scripts/deployment/deploy_monitoring.py
```

## Success Criteria

- [ ] Only one monitoring service running
- [ ] Database migration completed successfully
- [ ] API endpoints responding correctly
- [ ] Events being created and stored
- [ ] No errors in logs
- [ ] Service auto-starts on reboot

## Support

If you encounter issues:
1. Check the logs: `journalctl -u fpl-monitor -f`
2. Verify service status: `systemctl status fpl-monitor`
3. Test API endpoints locally on server
4. Check database connectivity

---

**Deployment Complete!** 🎉

Your FPL monitoring system now uses the scalable event-based architecture and can handle millions of users efficiently.
