# 🎯 FPL Monitor

**Production-ready Fantasy Premier League monitoring system with iOS app and cloud backend.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Swift](https://img.shields.io/badge/Swift-5.9+-orange.svg)](https://swift.org)
[![iOS](https://img.shields.io/badge/iOS-17.0+-lightgrey.svg)](https://developer.apple.com/ios)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Xcode 15+ (for iOS development)
- Supabase account
- DigitalOcean account (for deployment)

### Backend Setup
```bash
# Clone repository
git clone <repository-url>
cd fpl-monitor

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your Supabase credentials

# Run the service
python -m backend.main
```

### iOS App Setup
```bash
# Open in Xcode
open ios/FPLMonitor/FPLMonitor.xcodeproj

# Update API URL in APIManager.swift
# Build and run on simulator/device
```

## 🏗️ Architecture

```
FPL API → DigitalOcean Server → Supabase Database → REST API → iOS App
```

- **Backend**: FastAPI with PostgreSQL (Supabase)
- **Frontend**: SwiftUI iOS app
- **Infrastructure**: DigitalOcean cloud deployment
- **Monitoring**: 24/7 real-time FPL data monitoring

## 📁 Project Structure

```
fpl-monitor/
├── 📱 ios/                          # iOS Mobile App
│   └── FPLMonitor/
│       ├── FPLMonitor.xcodeproj/    # Xcode project
│       └── FPLMonitor/              # Swift source code
│           ├── FPLMonitorApp.swift  # App entry point
│           ├── ContentView.swift    # Main view
│           ├── Managers/            # API & Notification managers
│           ├── Models/              # Data models
│           └── Views/               # SwiftUI views
│
├── 🐍 backend/                      # Backend Services
│   ├── api/                         # API routes
│   ├── config/                      # Configuration
│   ├── models/                      # Data models
│   ├── services/                    # Core services
│   └── main.py                      # Application entry point
│
├── 🗄️ database/                     # Database Schemas
│   ├── schema.sql                   # Production schema
│   └── supabase_schema.sql          # Supabase schema
│
├── 🚀 deployment/                   # Production Deployment
│   ├── Dockerfile                   # Container configuration
│   ├── requirements.txt             # Dependencies
│   └── deploy.sh                    # Deployment script
│
├── 🧪 tests/                        # All Testing
│   ├── backend/                     # Backend tests
│   ├── ios/                         # iOS tests
│   └── integration/                 # Integration tests
│
├── 📚 docs/                         # Documentation
│   ├── README.md                    # This file
│   ├── API.md                       # API documentation
│   └── DEPLOYMENT.md                # Deployment guide
│
└── 🔧 scripts/                      # Utility Scripts
    ├── setup/                       # Setup scripts
    ├── maintenance/                 # Maintenance scripts
    └── tools/                       # Development tools
```

## 📊 Features

### Real-time Monitoring
- **Status Changes**: Player injuries, suspensions (every hour)
- **Price Changes**: Player price movements (during price windows)
- **Bonus Points**: Final bonus points (every 5 minutes)
- **Live Matches**: Goals, assists, cards, clean sheets (when active)

### iOS App Features
- **Real-time Notifications**: Push notifications for FPL events
- **Player Search**: Find and track specific players
- **Analytics Dashboard**: View engagement and usage statistics
- **Settings Management**: Customize notification preferences
- **Modern UI**: Clean, intuitive SwiftUI interface

### Backend Features
- **RESTful API**: Complete API for mobile app consumption
- **WebSocket Support**: Real-time communication
- **Database Integration**: Supabase PostgreSQL with 736 players, 20 teams
- **Push Notifications**: iOS APNs integration
- **Analytics**: User engagement and usage tracking

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/v1/monitoring/status` | GET | Monitoring status |
| `/api/v1/notifications` | GET | FPL notifications |
| `/api/v1/players/search` | GET | Search players |
| `/api/v1/fpl/current-gameweek` | GET | Current gameweek info |
| `/api/v1/fpl/teams` | GET | All Premier League teams |
| `/api/v1/fpl/players` | GET | All players with filtering |

## 🚀 Deployment

### DigitalOcean Deployment
```bash
# Deploy to DigitalOcean
./deployment/deploy.sh

# Check service status
ssh root@your-server "systemctl status fpl-monitor"

# View logs
ssh root@your-server "tail -f /opt/fpl-monitor/logs/fpl_monitor.log"
```

### Docker Deployment
```bash
# Build and run with Docker
docker build -t fpl-monitor .
docker run -p 8000:8000 fpl-monitor
```

## 🧪 Testing

```bash
# Run backend tests
python -m pytest tests/backend/

# Run integration tests
python -m pytest tests/integration/

# Run all tests
python -m pytest tests/
```

## 📱 iOS Development

### Requirements
- Xcode 15+
- iOS 17.0+
- Swift 5.9+

### Setup
1. Open `ios/FPLMonitor/FPLMonitor.xcodeproj` in Xcode
2. Update API URL in `APIManager.swift`
3. Configure push notifications in `NotificationManager.swift`
4. Build and run on simulator or device

## 🔐 Environment Variables

Create a `.env` file with the following variables:

```env
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
DATABASE_URL=your_database_url

# Push Notifications
APNS_BUNDLE_ID=com.yourcompany.fplmonitor
APNS_KEY_ID=your_apns_key_id
APNS_TEAM_ID=your_apns_team_id
APNS_KEY_PATH=path/to/your/key.p8

# Server
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `docs/` folder for detailed guides
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

## 🎯 Roadmap

- [ ] Android app development
- [ ] Web dashboard
- [ ] Advanced analytics
- [ ] Team management features
- [ ] League integration
- [ ] Historical data analysis

---

**Built with ❤️ using SwiftUI + FastAPI + Supabase + DigitalOcean**