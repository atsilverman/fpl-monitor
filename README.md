# FPL Mobile Monitor

A comprehensive Fantasy Premier League monitoring system with real-time notifications, dynamic monitoring modes, and mobile app integration.

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   iOS Mobile    │    │  Monitoring     │    │   Supabase      │
│   Application   │◄──►│   Service       │◄──►│   Database      │
│   (SwiftUI)     │    │   (Python)      │    │   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Push          │    │   FPL API       │    │   DigitalOcean  │
│ Notifications   │    │   (External)    │    │   Droplet       │
│   (APNS)        │    │                 │    │   (Production)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Features

- **Dynamic Monitoring**: Automatically adjusts refresh rates based on game state
- **Real-time Notifications**: Push notifications for goals, assists, price changes, and more
- **Deduplication**: Prevents duplicate notifications across service restarts
- **Mobile-First**: Clean, emoji-free output optimized for SwiftUI
- **Scalable**: Built on Supabase with PostgreSQL backend

## 📊 Monitoring Modes

### Mode 1: Live Performance Monitoring
**When Active**: During live matches
**Refresh Rate**: 60 seconds
**Triggers**: 
- Live matches detected in `fixtures` table (`started=true AND finished=false`)
- FPL API `/event/{gameweek}/live` endpoint

**Monitors**:
- Goals scored
- Assists
- Clean sheets
- Bonus points (unofficial BPS calculation)
- Yellow/Red cards
- Penalties saved/missed

**Database Inputs**:
- `fixtures` table: Live match detection
- `live_monitor_history` table: Change tracking
- FPL API: Real-time player stats

### Mode 2: Price Change Monitoring
**When Active**: 6:30-6:40 PM Pacific Time (10-minute window)
**Refresh Rate**: 5 minutes (300 seconds)
**Triggers**: 
- Time-based detection (Pacific timezone)
- FPL API price changes

**Monitors**:
- Player price increases/decreases
- Price change notifications

**Database Inputs**:
- `players` table: Current prices
- `live_monitor_history` table: Change tracking
- FPL API: Price updates

### Mode 3: Final Bonus Monitoring
**When Active**: After gameweeks finish + FPL data updated
**Refresh Rate**: 5 minutes (300 seconds)
**Triggers**:
- Gameweek finished (`finished=true`)
- FPL data checked (`data_checked=true`)
- Not already processed

**Monitors**:
- Official FPL bonus points
- Final bonus point changes

**Database Inputs**:
- `monitoring_state` table: Processed gameweek tracking
- `live_monitor_history` table: Change tracking
- FPL API: Official bonus data

### Mode 4: Status Change Monitoring
**When Active**: Always (24/7)
**Refresh Rate**: 1 hour (3600 seconds)
**Triggers**: Continuous monitoring

**Monitors**:
- Player injury status
- Suspension status
- Availability changes

**Database Inputs**:
- `players` table: Status changes
- `live_monitor_history` table: Change tracking
- FPL API: Player status updates

## 🗄️ Database Schema

### Core Tables

#### `players`
**Purpose**: FPL player data and current status
```sql
- id (SERIAL PRIMARY KEY)
- fpl_id (INTEGER UNIQUE) -- FPL's element_id
- web_name (VARCHAR) -- Player display name
- team_id (INTEGER) -- References teams table
- element_type (INTEGER) -- 1=GK, 2=DEF, 3=MID, 4=FWD
- now_cost (INTEGER) -- Current price (55 = £5.5m)
- status (VARCHAR) -- 'a'=available, 'i'=injured, etc.
- total_points (INTEGER) -- Season total points
- event_points (INTEGER) -- Current gameweek points
```

#### `fixtures`
**Purpose**: Match fixtures and live status
```sql
- id (INTEGER PRIMARY KEY) -- FPL's fixture_id
- event_id (INTEGER) -- References gameweeks table
- team_h (INTEGER) -- Home team ID
- team_a (INTEGER) -- Away team ID
- started (BOOLEAN) -- Match has started
- finished (BOOLEAN) -- Match has finished
- kickoff_time (TIMESTAMP) -- Match start time
- team_h_score (INTEGER) -- Home team score
- team_a_score (INTEGER) -- Away team score
```

#### `gameweek_stats`
**Purpose**: Player performance statistics per gameweek
```sql
- id (SERIAL PRIMARY KEY)
- player_id (INTEGER) -- References players table
- fixture_id (INTEGER) -- References fixtures table
- gameweek (INTEGER) -- Gameweek number
- goals_scored (INTEGER) -- Goals scored
- assists (INTEGER) -- Assists made
- clean_sheets (INTEGER) -- Clean sheets
- bonus (INTEGER) -- Bonus points awarded
- bps (INTEGER) -- Bonus points system score
- yellow_cards (INTEGER) -- Yellow cards
- red_cards (INTEGER) -- Red cards
- minutes (INTEGER) -- Minutes played
```

#### `live_monitor_history`
**Purpose**: Audit trail of all monitoring events and changes
```sql
- id (SERIAL PRIMARY KEY)
- player_id (INTEGER) -- References players table
- player_name (VARCHAR) -- Player name for quick reference
- team_name (VARCHAR) -- Team name for quick reference
- fixture_id (INTEGER) -- References fixtures table
- gameweek (INTEGER) -- Gameweek number
- event_type (VARCHAR) -- Type of event (live_goals_scored, price_change, etc.)
- old_value (INTEGER) -- Previous value
- new_value (INTEGER) -- New value
- points_change (INTEGER) -- FPL points change
- timestamp (TIMESTAMP) -- When change occurred
```

#### `monitoring_state`
**Purpose**: Tracks processed gameweeks to prevent duplicate processing
```sql
- id (SERIAL PRIMARY KEY)
- gameweek (INTEGER UNIQUE) -- Gameweek number
- bonus_processed (BOOLEAN) -- Whether bonus points processed
- last_processed_at (TIMESTAMP) -- When last processed
- created_at (TIMESTAMP) -- Record creation time
```

#### `monitoring_log`
**Purpose**: Service run logs and health monitoring
```sql
- id (SERIAL PRIMARY KEY)
- service_name (VARCHAR) -- Name of monitoring service
- run_type (VARCHAR) -- Type of run (monitoring_start, price_check, etc.)
- status (VARCHAR) -- running, completed, failed
- started_at (TIMESTAMP) -- When run started
- completed_at (TIMESTAMP) -- When run completed
- duration_seconds (INTEGER) -- Run duration
- records_processed (INTEGER) -- Number of records processed
- changes_detected (INTEGER) -- Number of changes detected
- notifications_sent (INTEGER) -- Number of notifications sent
```

### User Management Tables

#### `users`
**Purpose**: User profiles extending Supabase auth
```sql
- id (UUID PRIMARY KEY) -- References auth.users
- email (TEXT UNIQUE) -- User email
- fpl_manager_id (INTEGER) -- User's FPL manager ID
- notification_preferences (JSONB) -- Notification settings
- owned_players (INTEGER[]) -- Array of owned player IDs
- mini_league_ids (INTEGER[]) -- Array of mini league IDs
- timezone (TEXT) -- User timezone
```

#### `user_notifications`
**Purpose**: User-specific notification timeline
```sql
- id (UUID PRIMARY KEY)
- user_id (UUID) -- References users table
- notification_type (TEXT) -- Type of notification
- player_id (INTEGER) -- Player involved
- player_name (TEXT) -- Player name
- team_name (TEXT) -- Team name
- points_change (INTEGER) -- Points change
- message (TEXT) -- Notification message
- is_read (BOOLEAN) -- Read status
- created_at (TIMESTAMP) -- Notification time
```

## 🔌 API Endpoints

### Health & Status
- `GET /` - Health check
- `GET /api/v1/monitoring/status` - Complete monitoring status
- `GET /api/v1/fpl/current-gameweek` - Current gameweek information

### WebSocket
- `WS /ws` - Real-time updates for mobile app

### API Response Examples

#### Monitoring Status
```json
{
  "monitoring_active": true,
  "current_game_state": "no_live_matches",
  "websocket_connections": 0,
  "timestamp": "2025-09-12T16:40:53.992Z",
  "fpl_api_connected": true,
  "monitoring_categories": {
    "live_performance": {
      "active": false,
      "next_refresh": 0,
      "config": {
        "refresh_seconds": 60,
        "active_during": ["live_matches", "upcoming_matches"],
        "priority": "high",
        "description": "Goals, assists, cards, clean sheets"
      }
    },
    "price_changes": {
      "active": false,
      "next_refresh": 0,
      "config": {
        "refresh_seconds": 300,
        "active_during": ["price_update_windows"],
        "priority": "high",
        "description": "Player price movements (6:30-6:40 PM user time)"
      }
    }
  },
  "user_timezone": "America/Los_Angeles",
  "price_window_active": false,
  "processed_gameweeks": [1, 2, 3]
}
```

## 🚀 Production Deployment

### Server Requirements
- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **Python**: 3.8+
- **Memory**: 2GB+ RAM
- **Storage**: 10GB+ disk space
- **Network**: Stable internet connection

### Dependencies
```bash
# Core dependencies
fastapi==0.104.1
uvicorn==0.24.0
requests==2.31.0
python-dotenv==1.0.0
pytz==2023.3
pydantic==2.5.0

# Database
supabase==2.0.0
psycopg2-binary==2.9.9

# Monitoring
websockets==12.0
```

### Environment Variables
```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# FPL Configuration
FPL_MINI_LEAGUE_ID=your_league_id

# APNS Configuration (for push notifications)
APNS_KEY_ID=your_key_id
APNS_TEAM_ID=your_team_id
APNS_BUNDLE_ID=your_bundle_id
APNS_PRIVATE_KEY_PATH=/path/to/AuthKey.p8

# Optional
DISCORD_WEBHOOK_URL=your_discord_webhook
```

### Deployment Steps

1. **Clone Repository**
   ```bash
   git clone <repository_url>
   cd fpl-monitor
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Setup Database**
   ```bash
   # Run Supabase schema
   psql -h your_db_host -U your_user -d your_db -f database/supabase_schema.sql
   ```

5. **Deploy Service**
   ```bash
   # Copy service file
   cp backend/services/fpl_monitor_enhanced_production.py /opt/fpl-monitor/
   
   # Setup systemd service
   sudo cp deployment/fpl-monitor.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable fpl-monitor
   sudo systemctl start fpl-monitor
   ```

6. **Verify Deployment**
   ```bash
   # Check service status
   sudo systemctl status fpl-monitor
   
   # Check logs
   sudo journalctl -u fpl-monitor -f
   
   # Test API
   curl http://localhost:8000/
   ```

## 📱 Mobile App Integration

### iOS SwiftUI App
The mobile app is located in the `ios/` directory and includes:

- **Real-time Notifications**: Push notifications for all monitoring events
- **Clean UI**: No emojis, optimized for SwiftUI
- **User Management**: Supabase authentication integration
- **Notification Timeline**: Historical notification view
- **Settings**: Customizable notification preferences

### Key Features
- **Push Notifications**: APNS integration for real-time alerts
- **Offline Support**: Local notification storage
- **User Preferences**: Customizable notification types
- **Team Badges**: Visual team identification
- **Analytics**: Notification statistics and trends

## 🔧 Monitoring & Maintenance

### Service Management
```bash
# Start service
sudo systemctl start fpl-monitor

# Stop service
sudo systemctl stop fpl-monitor

# Restart service
sudo systemctl restart fpl-monitor

# Check status
sudo systemctl status fpl-monitor

# View logs
sudo journalctl -u fpl-monitor -f
```

### Health Monitoring
- **Service Health**: Check `/api/v1/monitoring/status`
- **Database Health**: Monitor Supabase connection
- **FPL API Health**: Monitor external API connectivity
- **Log Monitoring**: Review service logs for errors

### Troubleshooting

#### Common Issues
1. **Service Won't Start**
   - Check Python dependencies
   - Verify environment variables
   - Check systemd service configuration

2. **Database Connection Issues**
   - Verify Supabase credentials
   - Check network connectivity
   - Review database permissions

3. **FPL API Issues**
   - Check internet connectivity
   - Verify API endpoint availability
   - Review rate limiting

4. **Notification Issues**
   - Verify APNS configuration
   - Check device registration
   - Review notification permissions

## 📈 Performance & Scaling

### Current Performance
- **Monitoring Frequency**: 60s (live), 5min (price), 1h (status)
- **Database Queries**: Optimized with proper indexing
- **Memory Usage**: ~200MB typical
- **CPU Usage**: Low during normal operation

### Scaling Considerations
- **Database**: Supabase handles scaling automatically
- **Monitoring Service**: Can run multiple instances with load balancing
- **Mobile App**: Client-side scaling through app store distribution

## 🔒 Security

### Data Protection
- **Row Level Security**: Enabled on all Supabase tables
- **API Authentication**: Service role key for backend operations
- **User Data**: Encrypted at rest and in transit
- **Push Notifications**: APNS secure delivery

### Access Control
- **Database Access**: Service role key only
- **API Access**: Public read-only endpoints
- **User Data**: User-specific access through Supabase auth

## 📝 Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python backend/services/fpl_monitor_enhanced_production.py

# Test API
curl http://localhost:8000/
```

### Testing
```bash
# Run tests
python -m pytest tests/

# Test specific components
python tests/backend/test_supabase_connection.py
python tests/backend/test_local_endpoints.py
```

## 📚 Additional Documentation

- **API Documentation**: `docs/API.md`
- **Deployment Guide**: `docs/DEPLOYMENT.md`
- **Project Structure**: `docs/PROJECT_STRUCTURE.md`
- **Price Monitoring Analysis**: `docs/PRICE_MONITORING_ANALYSIS.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the logs for error details

---

**Last Updated**: September 12, 2025
**Version**: 3.0.0
**Status**: Production Ready