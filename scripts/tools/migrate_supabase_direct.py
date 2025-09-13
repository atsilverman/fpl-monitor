#!/usr/bin/env python3
"""
Direct Supabase Migration
========================

This script runs the database migration by executing SQL statements
directly against your Supabase database.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_database_connection():
    """Get database connection from environment variables"""
    # Extract connection details from Supabase URL
    supabase_url = os.getenv('SUPABASE_URL')
    if not supabase_url:
        print("❌ SUPABASE_URL not found in .env")
        return None
    
    # For Supabase, we need to construct the direct PostgreSQL connection
    # This requires the DATABASE_URL or individual components
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url)
    
    # Alternative: construct from individual components
    db_host = os.getenv('DB_HOST', 'db.your-project.supabase.co')
    db_name = os.getenv('DB_NAME', 'postgres')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD')
    db_port = os.getenv('DB_PORT', '5432')
    
    if not db_password:
        print("❌ Database password not found. Please set DB_PASSWORD in .env")
        return None
    
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port,
            sslmode='require'
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def run_migration():
    """Run the database migration"""
    print("🔄 Running database migration...")
    
    # Get database connection
    conn = get_database_connection()
    if not conn:
        print("❌ Cannot connect to database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Read migration file
        with open('database/migrate_to_events_architecture.sql', 'r') as f:
            migration_sql = f.read()
        
        print("📊 Executing migration SQL...")
        
        # Execute the migration
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration executed successfully!")
        
        # Test that tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('events', 'user_ownership', 'user_preferences')
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n📋 Created tables: {[table[0] for table in tables]}")
        
        # Test events table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'events' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print(f"\n📊 Events table has {len(columns)} columns:")
        for col_name, col_type in columns[:10]:  # Show first 10 columns
            print(f"   • {col_name}: {col_type}")
        if len(columns) > 10:
            print(f"   ... and {len(columns) - 10} more columns")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def create_sample_data():
    """Create sample data for testing"""
    print("\n📝 Creating sample data...")
    
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Insert sample event
        cursor.execute("""
            INSERT INTO events (
                event_type, player_id, player_name, team_name, team_abbreviation,
                points, points_change, points_category, gameweek, old_value, new_value,
                title, message
            ) VALUES (
                'goals', 1, 'Test Player', 'Test Team', 'TST',
                4, 4, 'Goal', 1, 0, 1,
                '⚽ Goal!', 'Test Player scored for Test Team'
            );
        """)
        
        conn.commit()
        print("✅ Sample event created")
        
        # Insert sample user ownership
        cursor.execute("""
            INSERT INTO user_ownership (user_id, fpl_manager_id, owned_players)
            VALUES ('00000000-0000-0000-0000-000000000000', 12345, ARRAY[1, 2, 3, 4, 5])
            ON CONFLICT (user_id) DO NOTHING;
        """)
        
        conn.commit()
        print("✅ Sample user ownership created")
        
        # Insert sample user preferences
        cursor.execute("""
            INSERT INTO user_preferences (user_id, notification_types)
            VALUES ('00000000-0000-0000-0000-000000000000', ARRAY['goals', 'assists', 'price_changes'])
            ON CONFLICT (user_id) DO NOTHING;
        """)
        
        conn.commit()
        print("✅ Sample user preferences created")
        
        return True
        
    except Exception as e:
        print(f"❌ Sample data creation failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def test_functions():
    """Test the database functions"""
    print("\n🧪 Testing database functions...")
    
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Test get_user_notifications function
        cursor.execute("""
            SELECT * FROM get_user_notifications('00000000-0000-0000-0000-000000000000', 10, 0);
        """)
        
        notifications = cursor.fetchall()
        print(f"✅ get_user_notifications function works - returned {len(notifications)} notifications")
        
        # Test get_unread_count function
        cursor.execute("""
            SELECT get_unread_count('00000000-0000-0000-0000-000000000000');
        """)
        
        unread_count = cursor.fetchone()[0]
        print(f"✅ get_unread_count function works - {unread_count} unread notifications")
        
        return True
        
    except Exception as e:
        print(f"❌ Function testing failed: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main function"""
    print("🚀 Direct Supabase Database Migration")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found. Please create one with your database credentials.")
        print("\nRequired environment variables:")
        print("   • DATABASE_URL (preferred)")
        print("   • OR DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT")
        return False
    
    # Run migration
    if not run_migration():
        print("❌ Migration failed")
        return False
    
    # Create sample data
    if not create_sample_data():
        print("⚠️  Sample data creation failed")
    
    # Test functions
    if not test_functions():
        print("⚠️  Function testing failed")
    
    print("\n🎉 Database migration completed!")
    print("\n✅ Next steps:")
    print("   1. Deploy the new monitoring service")
    print("   2. Test the API endpoints")
    print("   3. Verify events are being created")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
