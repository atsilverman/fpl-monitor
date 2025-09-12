#!/usr/bin/env python3
"""
Database Population Script
=========================

This script populates the database with initial FPL data from the API.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

def get_fpl_data():
    """Get bootstrap data from FPL API"""
    print("🔌 Fetching FPL bootstrap data...")
    
    try:
        response = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching FPL data: {e}")
        return None

def populate_teams(data, cursor):
    """Populate teams table"""
    print("🏟️  Populating teams...")
    
    teams = data.get("teams", [])
    for team in teams:
        cursor.execute("""
            INSERT INTO teams (
                fpl_id, code, name, short_name, position, played, win, draw, loss,
                points, strength, form, badge_url, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (fpl_id) DO UPDATE SET
                code = EXCLUDED.code,
                name = EXCLUDED.name,
                short_name = EXCLUDED.short_name,
                position = EXCLUDED.position,
                played = EXCLUDED.played,
                win = EXCLUDED.win,
                draw = EXCLUDED.draw,
                loss = EXCLUDED.loss,
                points = EXCLUDED.points,
                strength = EXCLUDED.strength,
                form = EXCLUDED.form,
                badge_url = EXCLUDED.badge_url,
                updated_at = NOW()
        """, (
            team["id"], team["code"], team["name"], team["short_name"],
            team.get("position"), team.get("played", 0), team.get("win", 0),
            team.get("draw", 0), team.get("loss", 0), team.get("points", 0),
            team.get("strength"), team.get("form"), team.get("badge_url")
        ))
    
    print(f"✅ Populated {len(teams)} teams")

def populate_players(data, cursor):
    """Populate players table"""
    print("⚽ Populating players...")
    
    players = data.get("elements", [])
    for player in players:
        cursor.execute("""
            INSERT INTO players (
                fpl_id, web_name, first_name, second_name, team_id, element_type,
                now_cost, total_points, event_points, points_per_game, form,
                selected_by_percent, status, photo_url, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (fpl_id) DO UPDATE SET
                web_name = EXCLUDED.web_name,
                first_name = EXCLUDED.first_name,
                second_name = EXCLUDED.second_name,
                team_id = EXCLUDED.team_id,
                element_type = EXCLUDED.element_type,
                now_cost = EXCLUDED.now_cost,
                total_points = EXCLUDED.total_points,
                event_points = EXCLUDED.event_points,
                points_per_game = EXCLUDED.points_per_game,
                form = EXCLUDED.form,
                selected_by_percent = EXCLUDED.selected_by_percent,
                status = EXCLUDED.status,
                photo_url = EXCLUDED.photo_url,
                updated_at = NOW()
        """, (
            player["id"], player["web_name"], player.get("first_name"),
            player.get("second_name"), player["team"], player["element_type"],
            player["now_cost"], player["total_points"], player["event_points"],
            player.get("points_per_game"), player.get("form"),
            player.get("selected_by_percent", 0), player["status"],
            player.get("photo")
        ))
    
    print(f"✅ Populated {len(players)} players")

def populate_gameweeks(data, cursor):
    """Populate gameweeks table"""
    print("📅 Populating gameweeks...")
    
    events = data.get("events", [])
    for event in events:
        cursor.execute("""
            INSERT INTO gameweeks (
                id, name, deadline_time, finished, is_previous, is_current, is_next,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                deadline_time = EXCLUDED.deadline_time,
                finished = EXCLUDED.finished,
                is_previous = EXCLUDED.is_previous,
                is_current = EXCLUDED.is_current,
                is_next = EXCLUDED.is_next,
                updated_at = NOW()
        """, (
            event["id"], event["name"], event["deadline_time"],
            event["finished"], event["is_previous"], event["is_current"],
            event["is_next"]
        ))
    
    print(f"✅ Populated {len(events)} gameweeks")

def populate_fixtures(cursor):
    """Populate fixtures table"""
    print("🏆 Populating fixtures...")
    
    try:
        response = requests.get("https://fantasy.premierleague.com/api/fixtures/")
        response.raise_for_status()
        fixtures = response.json()
        
        for fixture in fixtures:
            cursor.execute("""
                INSERT INTO fixtures (
                    id, event_id, team_h, team_a, team_h_score, team_a_score,
                    kickoff_time, started, finished, minutes, team_h_difficulty,
                    team_a_difficulty, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    event_id = EXCLUDED.event_id,
                    team_h = EXCLUDED.team_h,
                    team_a = EXCLUDED.team_a,
                    team_h_score = EXCLUDED.team_h_score,
                    team_a_score = EXCLUDED.team_a_score,
                    kickoff_time = EXCLUDED.kickoff_time,
                    started = EXCLUDED.started,
                    finished = EXCLUDED.finished,
                    minutes = EXCLUDED.minutes,
                    team_h_difficulty = EXCLUDED.team_h_difficulty,
                    team_a_difficulty = EXCLUDED.team_a_difficulty,
                    updated_at = NOW()
            """, (
                fixture["id"], fixture["event"], fixture["team_h"], fixture["team_a"],
                fixture.get("team_h_score"), fixture.get("team_a_score"),
                fixture.get("kickoff_time"), fixture.get("started", False),
                fixture.get("finished", False), fixture.get("minutes", 0),
                fixture.get("team_h_difficulty"), fixture.get("team_a_difficulty")
            ))
        
        print(f"✅ Populated {len(fixtures)} fixtures")
        
    except Exception as e:
        print(f"❌ Error fetching fixtures: {e}")

def main():
    """Main population function"""
    print("🗄️  FPL Monitor - Database Population")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("Run: python3 setup_environment.py")
        sys.exit(1)
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        sys.exit(1)
    
    # Get FPL data
    data = get_fpl_data()
    if not data:
        print("❌ Failed to fetch FPL data")
        sys.exit(1)
    
    # Connect to database
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        
        # Populate tables
        populate_teams(data, cursor)
        populate_players(data, cursor)
        populate_gameweeks(data, cursor)
        populate_fixtures(cursor)
        
        # Commit changes
        conn.commit()
        print("\n🎉 Database population completed successfully!")
        
        # Verify data
        cursor.execute("SELECT COUNT(*) FROM teams")
        team_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM players")
        player_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gameweeks")
        gameweek_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fixtures")
        fixture_count = cursor.fetchone()[0]
        
        print(f"\n📊 Database Summary:")
        print(f"   Teams: {team_count}")
        print(f"   Players: {player_count}")
        print(f"   Gameweeks: {gameweek_count}")
        print(f"   Fixtures: {fixture_count}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
