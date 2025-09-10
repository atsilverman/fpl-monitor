# 📝 Changelog

All notable changes to the FPL Monitor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Production-ready folder structure
- Comprehensive API documentation
- Docker deployment configuration
- Contributing guidelines
- Automated testing framework

### Changed
- Reorganized backend services into modular structure
- Consolidated documentation into clear sections
- Updated deployment scripts for new structure
- Improved code organization and maintainability

### Removed
- Duplicate iOS app (`FPLMonitorBrandNew/`)
- Massive cleanup folder with archived files
- Scattered test files from root directory
- Redundant documentation files

## [1.0.0] - 2024-01-15

### Added
- Initial release of FPL Monitor
- Real-time FPL data monitoring
- iOS SwiftUI application
- FastAPI backend with Supabase integration
- Push notification support
- Player search functionality
- Analytics dashboard
- DigitalOcean deployment configuration

### Features
- **Real-time Monitoring**: Status changes, price changes, bonus points
- **iOS App**: Modern SwiftUI interface with notifications
- **REST API**: Complete API for mobile app consumption
- **WebSocket Support**: Real-time communication
- **Push Notifications**: iOS APNs integration
- **Analytics**: User engagement tracking
- **Database**: Supabase PostgreSQL with 736 players, 20 teams

### Technical Details
- **Backend**: FastAPI with Python 3.11+
- **Frontend**: SwiftUI with iOS 17.0+
- **Database**: Supabase PostgreSQL
- **Infrastructure**: DigitalOcean cloud deployment
- **Monitoring**: 24/7 real-time FPL data monitoring

## [0.9.0] - 2024-01-10

### Added
- Basic monitoring service
- Database schema setup
- Initial iOS app structure
- Local development environment

### Changed
- Migrated from Discord bot to mobile app
- Implemented cloud backend architecture
- Added user preference management

## [0.8.0] - 2024-01-05

### Added
- Discord bot integration
- Local monitoring service
- Basic notification system

### Changed
- Initial project structure
- Local development setup

---

## Legend

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes
