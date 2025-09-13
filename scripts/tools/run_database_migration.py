#!/usr/bin/env python3
"""
Run Database Migration for Event-Based Architecture
==================================================

This script runs the database migration to create the new event-based tables
in your Supabase database.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def run_migration():
    """Run the database migration"""
    print("🔄 Running database migration for event-based architecture...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not service_key:
        print("❌ Missing Supabase credentials in .env file")
        return False
    
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    # Read the migration script
    try:
        with open('database/migrate_to_events_architecture.sql', 'r') as f:
            migration_sql = f.read()
    except FileNotFoundError:
        print("❌ Migration file not found: database/migrate_to_events_architecture.sql")
        return False
    
    print("📊 Migration SQL loaded, executing...")
    
    # Split the migration into individual statements
    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
    
    success_count = 0
    total_statements = len(statements)
    
    for i, statement in enumerate(statements, 1):
        if not statement or statement.startswith('--'):
            continue
            
        print(f"🔄 Executing statement {i}/{total_statements}...")
        
        try:
            # Use the SQL endpoint to execute the statement
            response = requests.post(
                f'{supabase_url}/rest/v1/rpc/exec_sql',
                headers=headers,
                json={'sql': statement},
                timeout=30
            )
            
            if response.status_code in [200, 201, 204]:
                success_count += 1
                print(f"✅ Statement {i} executed successfully")
            else:
                print(f"⚠️  Statement {i} returned {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error executing statement {i}: {e}")
    
    print(f"\n📊 Migration Results:")
    print(f"   • Statements executed: {success_count}/{total_statements}")
    print(f"   • Success rate: {(success_count/total_statements)*100:.1f}%")
    
    if success_count == total_statements:
        print("✅ Database migration completed successfully!")
        return True
    else:
        print("⚠️  Some statements failed - check the output above")
        return False

def test_new_tables():
    """Test that the new tables were created"""
    print("\n🧪 Testing new tables...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    tables_to_test = ['events', 'user_ownership', 'user_preferences']
    
    for table in tables_to_test:
        try:
            response = requests.get(
                f'{supabase_url}/rest/v1/{table}?limit=1',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Table '{table}' exists and accessible")
            else:
                print(f"❌ Table '{table}' error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing table '{table}': {e}")

def create_sample_data():
    """Create sample data for testing"""
    print("\n📝 Creating sample data...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    # Create a sample event
    sample_event = {
        "event_type": "goals",
        "player_id": 1,
        "player_name": "Test Player",
        "team_name": "Test Team",
        "team_abbreviation": "TST",
        "points": 4,
        "points_change": 4,
        "points_category": "Goal",
        "gameweek": 1,
        "old_value": 0,
        "new_value": 1,
        "title": "⚽ Goal!",
        "message": "Test Player scored for Test Team"
    }
    
    try:
        response = requests.post(
            f'{supabase_url}/rest/v1/events',
            headers=headers,
            json=sample_event,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print("✅ Sample event created successfully")
            return True
        else:
            print(f"❌ Failed to create sample event: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating sample event: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Database Migration for Event-Based Architecture")
    print("=" * 60)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found. Please create one with your Supabase credentials.")
        return False
    
    # Run migration
    if not run_migration():
        print("❌ Migration failed")
        return False
    
    # Test new tables
    test_new_tables()
    
    # Create sample data
    if create_sample_data():
        print("\n🎉 Migration and testing completed successfully!")
        print("\n✅ Next steps:")
        print("   1. Deploy the new monitoring service")
        print("   2. Test the API endpoints")
        print("   3. Verify events are being created")
        return True
    else:
        print("\n⚠️  Migration completed but sample data creation failed")
        print("   You may need to check the table structure manually")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
