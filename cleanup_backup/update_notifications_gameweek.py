#!/usr/bin/env python3
"""
Update FPLNotification data to include gameweek points
"""

import re

def update_notification_file():
    file_path = "/Users/silverman/Documents/fpl-monitor/20250909 2/ios/FPLMonitor/FPLMonitor/Models/RealisticNotificationData.swift"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match FPLNotification with totalPoints but no gameweekPoints
    pattern = r'(FPLNotification\(\s*title: "[^"]+",\s*body: "[^"]+",\s*type: \.[^,]+,\s*player: "[^"]+",\s*team: "[^"]+",\s*teamAbbreviation: "[^"]+",\s*points: \d+,\s*pointsChange: [+\-]?\d+,\s*pointsCategory: "[^"]+",\s*totalPoints: \d+)(,\s*overallOwnership: [\d.]+)'
    
    def replace_notification(match):
        total_points = int(re.search(r'totalPoints: (\d+)', match.group(1)).group(1))
        ownership = float(re.search(r'overallOwnership: ([\d.]+)', match.group(2)).group(1))
        
        # Calculate realistic gameweek points (typically 2-12 points)
        if total_points > 80:
            gameweek_points = 8  # High-performing players
        elif total_points > 60:
            gameweek_points = 6  # Good players
        elif total_points > 40:
            gameweek_points = 4  # Average players
        else:
            gameweek_points = 2  # Lower-performing players
        
        # Add some variation based on ownership (higher ownership = more points)
        if ownership > 30:
            gameweek_points += 2
        elif ownership > 15:
            gameweek_points += 1
        
        # Ensure reasonable range
        gameweek_points = max(2, min(12, gameweek_points))
        
        return f"{match.group(1)}, gameweekPoints: {gameweek_points}, gameweek: 15{match.group(2)}"
    
    # Apply the replacement
    updated_content = re.sub(pattern, replace_notification, content, flags=re.MULTILINE | re.DOTALL)
    
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print("✅ Updated all notifications with gameweek points")

if __name__ == "__main__":
    update_notification_file()
