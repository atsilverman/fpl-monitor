#!/usr/bin/env python3
"""
Generate realistic FPL notification data from Supabase database
This script can be used to create realistic notification data based on actual player data
"""

import os
import sys
import json
from datetime import datetime, timedelta
from supabase import create_client, Client

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

def get_supabase_client():
    """Initialize Supabase client"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_ANON_KEY environment variables required")
        return None
    
    return create_client(url, key)

def get_top_players(supabase: Client, limit=25):
    """Get top players by total points for realistic notifications"""
    try:
        response = supabase.table('players').select(
            'web_name, first_name, second_name, total_points, selected_by_percent, now_cost, status'
        ).select(
            'teams(name, short_name)'
        ).order('total_points', desc=True).limit(limit).execute()
        
        return response.data
    except Exception as e:
        print(f"Error fetching players: {e}")
        return []

def generate_notification_data(players):
    """Generate realistic notification data based on player stats"""
    notifications = []
    
    # Sample notification types with realistic scenarios
    notification_scenarios = [
        {
            'type': 'goals',
            'title': '⚽ Goal!',
            'points': 4,
            'category': 'Goal',
            'impact': 'high'
        },
        {
            'type': 'assists', 
            'title': '🎯 Assist!',
            'points': 3,
            'category': 'Assist',
            'impact': 'medium'
        },
        {
            'type': 'cleanSheets',
            'title': '🛡️ Clean Sheet!',
            'points': 4,
            'category': 'Clean Sheet',
            'impact': 'medium'
        },
        {
            'type': 'bonus',
            'title': '⭐ Bonus Points!',
            'points': 2,
            'category': 'Bonus',
            'impact': 'medium'
        },
        {
            'type': 'yellowCards',
            'title': '🟡 Yellow Card',
            'points': -1,
            'category': 'Yellow Card',
            'impact': 'low'
        },
        {
            'type': 'redCards',
            'title': '🔴 Red Card',
            'points': -3,
            'category': 'Red Card',
            'impact': 'high'
        },
        {
            'type': 'saves',
            'title': '💪 Saves!',
            'points': 1,
            'category': 'Saves',
            'impact': 'low'
        }
    ]
    
    # Generate notifications for each player
    for i, player in enumerate(players):
        if not player.get('teams'):
            continue
            
        team = player['teams']
        player_name = player.get('web_name', 'Unknown Player')
        team_name = team.get('name', 'Unknown Team')
        team_short = team.get('short_name', 'UNK')
        
        # Select a random scenario for this player
        scenario = notification_scenarios[i % len(notification_scenarios)]
        
        # Calculate realistic ownership percentage
        ownership = float(player.get('selected_by_percent', 0))
        
        # Generate realistic total points (current + change)
        current_points = int(player.get('total_points', 0))
        points_change = scenario['points']
        new_total = max(0, current_points + points_change)
        
        # Generate realistic fixture
        fixtures = [
            f"{team_short} vs ARS", f"{team_short} vs LIV", f"{team_short} vs MCI",
            f"{team_short} vs CHE", f"{team_short} vs TOT", f"{team_short} vs AVL",
            f"{team_short} vs NEW", f"{team_short} vs WHU", f"{team_short} vs BHA"
        ]
        fixture = fixtures[i % len(fixtures)]
        
        # Generate timestamp (recent notifications)
        hours_ago = i % 48  # Spread over last 48 hours
        timestamp = datetime.now() - timedelta(hours=hours_ago)
        
        notification = {
            'id': f"notification_{i+1}",
            'title': scenario['title'],
            'body': f"{player_name} {'scored for' if scenario['type'] == 'goals' else 'provided an assist for' if scenario['type'] == 'assists' else 'kept a clean sheet' if scenario['type'] == 'cleanSheets' else 'earned bonus points' if scenario['type'] == 'bonus' else 'received a yellow card' if scenario['type'] == 'yellowCards' else 'received a red card' if scenario['type'] == 'redCards' else 'made saves for'} {team_name}",
            'type': scenario['type'],
            'player': player_name,
            'team': team_name,
            'teamAbbreviation': team_short,
            'points': scenario['points'],
            'pointsChange': points_change,
            'pointsCategory': scenario['category'],
            'totalPoints': new_total,
            'overallOwnership': ownership,
            'isOwned': i % 3 == 0,  # Every 3rd player is owned
            'timestamp': timestamp.isoformat(),
            'isRead': i > 5,  # First 6 are unread
            'homeTeam': team_name,
            'awayTeam': 'Opponent',
            'fixture': fixture,
            'impact': scenario['impact']
        }
        
        notifications.append(notification)
    
    return notifications

def main():
    """Main function to generate realistic notification data"""
    print("Generating realistic FPL notification data...")
    
    # Initialize Supabase client
    supabase = get_supabase_client()
    if not supabase:
        return
    
    # Get top players
    players = get_top_players(supabase, 25)
    if not players:
        print("No players found in database")
        return
    
    print(f"Found {len(players)} players")
    
    # Generate notifications
    notifications = generate_notification_data(players)
    
    # Save to JSON file
    output_file = os.path.join(os.path.dirname(__file__), '..', '..', 'ios', 'FPLMonitor', 'FPLMonitor', 'Models', 'realistic_notifications.json')
    
    with open(output_file, 'w') as f:
        json.dump(notifications, f, indent=2, default=str)
    
    print(f"Generated {len(notifications)} realistic notifications")
    print(f"Saved to: {output_file}")
    
    # Print sample
    print("\nSample notification:")
    print(json.dumps(notifications[0], indent=2, default=str))

if __name__ == "__main__":
    main()
