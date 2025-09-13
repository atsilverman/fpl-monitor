#!/usr/bin/env python3
"""
Supabase SQL Editor Migration
============================

This script provides the migration SQL that you can run directly
in your Supabase SQL editor.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def print_migration_instructions():
    """Print instructions for running the migration"""
    print("🚀 Supabase Database Migration Instructions")
    print("=" * 60)
    
    supabase_url = os.getenv('SUPABASE_URL', 'your-project.supabase.co')
    
    print(f"📍 Your Supabase URL: {supabase_url}")
    print("\n📋 Steps to run the migration:")
    print("1. Go to your Supabase dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Copy and paste the migration SQL below")
    print("4. Click 'Run' to execute")
    print("\n" + "="*60)

def print_migration_sql():
    """Print the migration SQL"""
    try:
        with open('database/migrate_to_events_architecture.sql', 'r') as f:
            migration_sql = f.read()
        
        print("📄 Migration SQL:")
        print("-" * 60)
        print(migration_sql)
        print("-" * 60)
        
    except FileNotFoundError:
        print("❌ Migration file not found: database/migrate_to_events_architecture.sql")

def print_verification_sql():
    """Print SQL to verify the migration"""
    print("\n🧪 Verification SQL (run after migration):")
    print("-" * 60)
    
    verification_sql = """
-- Check if new tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('events', 'user_ownership', 'user_preferences')
ORDER BY table_name;

-- Check events table structure
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'events' 
ORDER BY ordinal_position;

-- Test creating a sample event
INSERT INTO events (
    event_type, player_id, player_name, team_name, team_abbreviation,
    points, points_change, points_category, gameweek, old_value, new_value,
    title, message
) VALUES (
    'goals', 1, 'Test Player', 'Test Team', 'TST',
    4, 4, 'Goal', 1, 0, 1,
    '⚽ Goal!', 'Test Player scored for Test Team'
);

-- Check the sample event was created
SELECT * FROM events WHERE player_name = 'Test Player';

-- Test the get_user_notifications function
SELECT * FROM get_user_notifications('00000000-0000-0000-0000-000000000000', 10, 0);
"""
    
    print(verification_sql)
    print("-" * 60)

def main():
    """Main function"""
    print_migration_instructions()
    print_migration_sql()
    print_verification_sql()
    
    print("\n✅ After running the migration:")
    print("   1. Verify all tables were created")
    print("   2. Test the sample event creation")
    print("   3. Deploy the new monitoring service")
    print("   4. Test the API endpoints")

if __name__ == "__main__":
    main()
