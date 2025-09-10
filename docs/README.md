# FPL Live Monitor

A real-time Fantasy Premier League monitoring system that detects and notifies about player performance changes, price movements, and status updates via Discord.

## 🚀 Features

- **Real-time Monitoring**: Intelligent refresh rates based on game state
- **Comprehensive Change Detection**: 12 different notification types
- **Discord Integration**: Instant notifications with emojis and formatting
- **Smart Thresholds**: Only notifies on significant changes
- **Production Ready**: Single script, minimal dependencies
- **Dynamic Price Monitoring**: 5-minute intervals during FPL price update windows (1:00-3:00 AM GMT)

## 📊 Complete Monitoring Table

| **Category** | **Stat Name** | **Position Relevance** | **FPL Points** | **Threshold/Trigger** | **Data Source** | **Notification Criteria** |
|--------------|---------------|------------------------|-----------------|------------------------|-----------------|---------------------------|
| **⚽ Goals** | `goals` | GK, DEF, MID, FWD | GK: +6, DEF: +6, MID: +5, FWD: +4 | Any change > 0 | Live API | Points change ≥ 1 |
| **🎯 Assists** | `assists` | GK, DEF, MID, FWD | +3 for all | Any change > 0 | Live API | Points change ≥ 1 |
| **🛡️ Clean Sheets** | `clean_sheets` | GK, DEF, MID | GK: +4, DEF: +4, MID: +1, FWD: +0 | 60+ minutes | Live API | Points change ≥ 1 |
| **⭐ Bonus*** | `bonus` | GK, DEF, MID, FWD | +1 per bonus | Any change > 0 + 60+ min | Live API | Points change ≥ 1 |
| **🟥 Red Cards** | `red_cards` | GK, DEF, MID, FWD | -3 | Any change > 0 | Live API | Points change ≥ 1 |
| **🟨 Yellow Cards** | `yellow_cards` | GK, DEF, MID, FWD | -1 | Any change > 0 | Live API | Points change ≥ 1 |
| **🧤 Penalties Saved** | `penalties_saved` | GK only | +5 | Any change > 0 | Live API | Points change ≥ 1 |
| **❌ Penalties Missed** | `penalties_missed` | GK, DEF, MID, FWD | -2 | Any change > 0 | Live API | Points change ≥ 1 |
| **😱 Own Goals** | `own_goals` | GK, DEF, MID, FWD | -2 | Any change > 0 | Live API | Points change ≥ 1 |
| **💾 Saves** | `saves` | GK only | +1 per 3 saves | Every 3 saves | Live API | Threshold crossing only |
| **🥅 Goals Conceded** | `goals_conceded` | GK, DEF only | -1 per 2 goals | Every 2 goals | Live API | Threshold crossing only |
| **🔄 Defensive Contribution** | `defensive_contribution` | DEF, MID, FWD | +2 if threshold met | DEF: ≥10, MID/FWD: ≥12 | Live API | Threshold crossing only |
| **💰 Price Changes** | `price` | GK, DEF, MID, FWD | N/A | Any change | Bootstrap API | Any price movement |
| **🏥 Status Changes** | `status` | GK, DEF, MID, FWD | N/A | Any status change | Bootstrap API | Any status change |

**Position Relevance Key:**
- **GK**: Goalkeeper
- **DEF**: Defender  
- **MID**: Midfielder
- **FWD**: Forward

**Threshold-Based Stats:**
- **Saves**: Every 3 saves = +1 point (Goalkeepers only)
- **Goals Conceded**: Every 2 goals = -1 point (GK/DEF only)
- **Defensive Contribution**: DEF ≥10, MID/FWD ≥12 = +2 points

## 📢 **Example Notifications by Category**

### **⚽ Performance Stats (Live Matches)**
```
**HAALAND** (MCI)
⚽ **GOALS** +6 pts
---------------

**SALAH** (LIV)
🎯 **ASSIST** +3 pts
---------------

**ALISSON** (LIV)
🛡️ **CLEAN SHEET** +4 pts
---------------

**VAN DIJK** (LIV)
🛡️ **CLEAN SHEET** +4 pts
---------------

**ROBERTSON** (LIV)
🔄 **DEFCON** (12) +2 pts
---------------

**FODEN** (MCI)
⭐ **BONUS** +1 pt
---------------

**DE BRUYNE** (MCI)
🟨 **YELLOW CARD** -1 pt
---------------

**WATKINS** (AVL)
❌ **PENALTY MISSED** -2 pts
---------------

**EDERSON** (MCI)
💾 **SAVES** (6) +2 pts
---------------

**DIAS** (MCI)
🥅 **GOALS CONCEDED** (2) -1 pt
---------------

**TONEY** (BRE)
😱 **OWN GOAL** -2 pts
---------------

**MARTINEZ** (AVL)
🧤 **PENALTY SAVED** +5 pts
---------------
```

### **💰 Player Changes (Between Matches)**
```
**WATKINS** (AVL) 9.0m
💰 **PRICE CHANGE** +0.1m
---------------

**DE BRUYNE** (MCI)
🏥 **STATUS CHANGE** a → i
📋 **Injured - Player is injured and unavailable**
---------------
```

### **📈 Daily Ownership Summary (9:00 PM PDT)**
```
📈 **TOP 10 OWNERSHIP INCREASES (Day over Day)**
1. Haaland (MCI) +2.3%
2. Salah (LIV) +1.8%
3. Watkins (AVL) +1.5%
4. Foden (MCI) +1.2%
5. Saka (ARS) +1.1%
6. Trippier (NEW) +0.9%
7. Alisson (LIV) +0.8%
8. Van Dijk (LIV) +0.7%
9. Robertson (LIV) +0.6%
10. Ederson (MCI) +0.5%
---------------

📉 **TOP 10 OWNERSHIP DECREASES (Day over Day)**
1. De Bruyne (MCI) -1.8%
2. Rashford (MUN) -1.5%
3. Sterling (CHE) -1.2%
4. Kane (BAY) -1.0%
5. Son (TOT) -0.9%
6. Fernandes (MUN) -0.8%
7. Alexander-Arnold (LIV) -0.7%
8. Chilwell (CHE) -0.6%
9. Mount (MUN) -0.5%
10. Grealish (MCI) -0.4%
---------------
```

## 🛠️ Setup

### 1. Database Setup

```bash
# Create PostgreSQL database
createdb fpl

# Run schema
psql -d fpl -f fpl_lean_schema.sql
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Discord Webhook

The Discord webhook URL is embedded in the script. Update it in `fpl_refresh.py`:

```python
self.webhook_url = "YOUR_DISCORD_WEBHOOK_URL"
```

## 🎯 Usage

### Production Monitoring

Start continuous monitoring with intelligent refresh rates:

```bash
python3 fpl_refresh.py --monitor
```

**Smart Refresh Rates:**
- **Live Matches**: 30 seconds (performance stats)
- **Price Update Windows**: 5 minutes (1:00-3:00 AM GMT / 5:00-7:00 PM PST)
- **Between Matches**: 1 hour (status changes)

### Manual Refresh

Run a single refresh cycle with change detection:

```bash
python3 fpl_refresh.py --once
```

### Quiet Data Update

Update database without notifications:

```bash
python3 fpl_refresh.py --muted
```

## 📋 Command Line Arguments

| **Argument** | **Description** | **Use Case** |
|--------------|-----------------|--------------|
| `--monitor` | Start continuous monitoring | Production monitoring |
| `--once` | Single refresh with notifications | Manual updates, testing |
| `--muted` | Update data without notifications | Database maintenance |

## 🗄️ Database Schema

**7 Essential Tables:**
- `teams` - Premier League teams
- `players` - FPL players and prices
- `gameweeks` - FPL gameweek info
- `fixtures` - Match schedules and results
- `gameweek_stats` - Player performance data
- `player_history` - Daily ownership snapshots
- `live_monitor_history` - Change tracking

## 🔍 How It Works

### 1. Data Collection
- Fetches data from FPL API endpoints (`bootstrap-static`, `fixtures`, `event/{gameweek}/live`)
- Updates database with latest information
- Maintains data integrity with conflict resolution

### 2. Daily Ownership Tracking
- **Daily Snapshots**: Captures `selected_by_percent` data daily at 9:00 PM PDT (4:00 AM GMT)
- **Change Detection**: Compares current ownership against previous day's snapshot
- **Top Movers**: Sends 2 Discord notifications showing:
  - 📈 **Top 10 Ownership Increases** (biggest gains)
  - 📉 **Top 10 Ownership Decreases** (biggest drops)
- **Data Storage**: Uses `player_history` table for historical tracking

### 3. Change Detection
- Creates temporary snapshots before updates
- Compares new data against previous state
- Identifies significant changes only
- Handles stat reversals and corrections from FPL API

### 4. Notification Processing
- Validates changes against thresholds
- Calculates FPL points impact by position
- Formats Discord messages with emojis
- Enriches player/team information for robust notifications

### 5. Smart Monitoring
- Detects live matches automatically
- Monitors price changes during FPL update windows (1:00-3:00 AM GMT)
- Adjusts refresh rates based on activity
- Resource-efficient operation with 70-80% cost reduction

## 📈 Example Notifications

```
**HAALAND** (MCI)
⚽ **GOALS** +4 pts
---------------

**SALAH** (LIV)
🎯 **ASSIST** +3 pts
---------------

**ALISSON** (LIV)
💾 **SAVES** (6) +2 pts
---------------

**VAN DIJK** (LIV)
🛡️ **CLEAN SHEET** +4 pts
---------------

**ROBERTSON** (LIV)
🔄 **DEFCON** (12) +2 pts
---------------

**FODEN** (MCI)
⭐ **BONUS** 2 → 3 pts
---------------

**DE BRUYNE** (MCI)
🏥 **STATUS CHANGE** a → i
📋 **Injured - Player is injured and unavailable**
---------------

**WATKINS** (AVL)
💰 **PRICE CHANGE** +0.1m
---------------
```

## 🔧 Configuration

### Embedded Settings

All configuration is embedded in the script:

```python
# Discord settings
self.webhook_url = "https://discord.com/api/webhooks/1409729125123358741/eGGCfPs3A-WhA1SuRsjMW9wFXCkf364ENxXTSJPOt9ho9L9d3bTK2X27fSb3YcQ-lJW1"
self.bot_username = "FPL Live Monitor"
self.min_points_change = 1

# Notification categories (12 types)
self.notification_categories = {
    'goals': {'emoji': '⚽', 'points_impact': True},
    'assists': {'emoji': '🎯', 'points_impact': True},
    'clean_sheets': {'emoji': '🛡️', 'negative_emoji': '🛡️❌', 'points_impact': True},
    
    'yellow_cards': {'emoji': '🟨', 'points_impact': True},
    'red_cards': {'emoji': '🟥', 'points_impact': True},
    'penalties_missed': {'emoji': '❌', 'points_impact': True},
    'saves': {'emoji': '💾', 'points_impact': True},
    'goals_conceded': {'emoji': '🥅', 'points_impact': True},
    'defensive_contribution': {'emoji': '🔄', 'points_impact': True},
    'price_changes': {'emoji': '💰', 'points_impact': False},
    'status_changes': {'emoji': '🏥', 'points_impact': False}
}
```

### Threshold-Based Notifications

Some stats only trigger on threshold crossings:

- **Saves**: Every 3 saves = +1 point (GK only)
- **Goals Conceded**: Every 2 goals = -1 point (GK/DEF only)
- **Defensive Contribution**: Position-specific thresholds (DEF/MID/FWD)
- **Bonus**: Based on BPS ranking system

### Emoji Behavior

- **Clean Sheets**: 🛡️ for gained, 🛡️❌ for lost
- **Goals/Assists**: ⚽🎯 always positive
- **Cards**: 🟨🟥 always negative
- **Saves**: 💾 always positive

### FPL Points by Position

| **Stat** | **GK** | **DEF** | **MID** | **FWD** |
|----------|--------|---------|---------|---------|
| **Goal** | +6 | +6 | +5 | +4 |
| **Assist** | +3 | +3 | +3 | +3 |
| **Clean Sheet** | +4 | +4 | +1 | +0 |
| **Save** | +1/3 | - | - | - |
| **Goal Conceded** | -1/2 | -1/2 | - | - |
| **Defensive Contribution** | - | +1/12 | +1/12 | - |

## 🚨 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check PostgreSQL is running
brew services start postgresql
# Or
sudo systemctl start postgresql
```

**No Notifications**
- Verify Discord webhook URL is correct
- Check minimum points change threshold (default: 1 point)
- Ensure database has data (`python3 fpl_refresh.py --once`)

**Price Changes Not Detected**
- Price monitoring only active during FPL update windows (1:00-3:00 AM GMT)
- Check if current time falls within price update window
- Verify `players` table is being refreshed

**API Errors**
- FPL API may be temporarily unavailable
- Check internet connection
- Script will retry automatically

### Logs

The script provides detailed console output:
- ✅ Success messages
- ⚠️ Warnings
- ❌ Error messages
- 📊 Change detection results
- 🕐 Game state detection

## 📁 File Structure

```
fpl-research/
├── fpl_refresh.py          # Main monitoring script
├── fpl_lean_schema.sql     # Database schema
├── requirements.txt        # Python dependencies
├── ideas.txt              # Feature ideas and notes
└── fpl_scoring.txt        # FPL scoring rules reference
```

## 🔄 System Architecture

```
FPL API → Data Fetch → Database Update → Change Detection → Discord Notification
```

- **Single Script**: Everything in one file
- **No External Config**: All settings embedded
- **Self-Contained**: Minimal dependencies
- **Production Ready**: Robust error handling
- **Self-Sustaining**: Dynamic refresh rates and comprehensive change detection

## 🎉 Getting Started

1. **Setup Database**: `psql -d fpl -f fpl_lean_schema.sql`
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Update Webhook**: Edit Discord URL in script (if needed)
4. **Test**: `python3 fpl_refresh.py --once`
5. **Deploy**: `python3 fpl_refresh.py --monitor`

## 🖥️ Deployment Options

### Local Continuous Monitoring

**Option 1: Terminal Session**
```bash
# Keep terminal open
python3 fpl_refresh.py --monitor
```

**Option 2: Screen Session**
```bash
screen -S fpl-monitor
python3 fpl_refresh.py --monitor
# Ctrl+A, D to detach
```

**Option 3: Mac Mini with Amphetamine**
- Install Amphetamine to prevent sleep
- Run monitoring script continuously
- Cost-effective 24/7 operation

### Amphetamine Settings for 24/7 Monitoring

1. **Basic Setup**: Enable "Prevent system sleep"
2. **Advanced**: Set custom duration (24 hours, repeat)
3. **Power Management**: Disable "Allow display to sleep"
4. **Menu Bar**: Enable indicator for monitoring status

## 📝 License

This project is for personal FPL monitoring use. Please respect FPL's API terms of service.
