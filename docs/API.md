# 📡 FPL Monitor API Documentation

## Overview

The FPL Monitor API provides real-time Fantasy Premier League data and monitoring capabilities through a RESTful interface.

**Base URL**: `https://your-domain.com/api/v1`

## Authentication

Currently, the API is open and doesn't require authentication. Future versions will include API key authentication.

## Endpoints

### Health Check

#### `GET /`
Check if the API is running.

**Response:**
```json
{
  "service": "FPL Monitor API",
  "version": "1.0.0",
  "status": "healthy",
  "docs": "/docs"
}
```

### Monitoring Status

#### `GET /api/v1/monitoring/status`
Get the current monitoring status and statistics.

**Response:**
```json
{
  "status": "running",
  "last_check": "2024-01-15T10:30:00Z",
  "total_notifications": 1250,
  "active_monitors": 4,
  "uptime": "72h 15m 30s"
}
```

### Notifications

#### `GET /api/v1/notifications`
Get FPL notifications with pagination.

**Query Parameters:**
- `limit` (optional): Number of notifications to return (1-100, default: 50)
- `offset` (optional): Number of notifications to skip (default: 0)

**Response:**
```json
[
  {
    "id": 123,
    "player_id": 456,
    "player_name": "Mohamed Salah",
    "team_name": "Liverpool",
    "notification_type": "goal",
    "message": "⚽ Mohamed Salah scored a goal!",
    "points": 4,
    "timestamp": "2024-01-15T10:30:00Z",
    "gameweek": 20,
    "is_read": false
  }
]
```

### Player Search

#### `GET /api/v1/players/search`
Search for players by name.

**Query Parameters:**
- `query` (required): Search term (minimum 2 characters)

**Response:**
```json
{
  "players": [
    {
      "id": 456,
      "first_name": "Mohamed",
      "second_name": "Salah",
      "web_name": "Salah",
      "team_id": 11,
      "team_name": "Liverpool",
      "position": "MID",
      "price": 12.5,
      "total_points": 180,
      "form": 8.2,
      "selected_by_percent": "45.2%",
      "status": "a",
      "news": "",
      "news_added": null
    }
  ],
  "query": "salah"
}
```

### Gameweek Information

#### `GET /api/v1/fpl/current-gameweek`
Get current gameweek information.

**Response:**
```json
{
  "id": 20,
  "name": "Gameweek 20",
  "deadline_time": "2024-01-20T11:00:00Z",
  "is_current": true,
  "is_next": false,
  "is_previous": false,
  "finished": false,
  "is_updated": true,
  "highest_score": 95,
  "most_selected": 123,
  "most_transferred_in": 456,
  "most_captained": 789,
  "most_vice_captained": 321
}
```

### Teams

#### `GET /api/v1/fpl/teams`
Get all Premier League teams.

**Response:**
```json
{
  "teams": [
    {
      "id": 11,
      "name": "Liverpool",
      "short_name": "LIV",
      "strength": 4,
      "strength_attack_home": 4,
      "strength_attack_away": 4,
      "strength_defence_home": 3,
      "strength_defence_away": 3,
      "team_division": 1,
      "code": 14,
      "played": 19,
      "win": 12,
      "draw": 4,
      "loss": 3,
      "points": 40,
      "position": 1,
      "form": "WWWDW",
      "pulse_id": 11
    }
  ]
}
```

### Players

#### `GET /api/v1/fpl/players`
Get players with optional filtering.

**Query Parameters:**
- `team_id` (optional): Filter by team ID
- `position` (optional): Filter by position (GK, DEF, MID, FWD)
- `limit` (optional): Number of players to return (1-500, default: 100)

**Response:**
```json
{
  "players": [
    {
      "id": 456,
      "first_name": "Mohamed",
      "second_name": "Salah",
      "web_name": "Salah",
      "team_id": 11,
      "team_name": "Liverpool",
      "position": "MID",
      "price": 12.5,
      "total_points": 180,
      "form": 8.2,
      "selected_by_percent": "45.2%",
      "status": "a",
      "news": "",
      "news_added": null
    }
  ]
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

- **Rate Limit**: 1000 requests per hour per IP
- **Headers**: Rate limit information is included in response headers
  - `X-RateLimit-Limit`: Maximum requests per hour
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when the rate limit resets

## WebSocket Support

Real-time updates are available via WebSocket connection:

**Connection**: `wss://your-domain.com/ws`

**Message Types:**
- `notification`: New FPL notification
- `status_update`: Monitoring status update
- `player_update`: Player data update

## SDKs and Libraries

### Python
```python
import requests

# Get notifications
response = requests.get('https://your-domain.com/api/v1/notifications')
notifications = response.json()
```

### Swift
```swift
import Foundation

// Search players
let url = URL(string: "https://your-domain.com/api/v1/players/search?query=salah")!
let task = URLSession.shared.dataTask(with: url) { data, response, error in
    // Handle response
}
task.resume()
```

## Changelog

### v1.0.0 (2024-01-15)
- Initial API release
- Basic CRUD operations for notifications, players, teams
- Search functionality
- Real-time monitoring status
- WebSocket support
