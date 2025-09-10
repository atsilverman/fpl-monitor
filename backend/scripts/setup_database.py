#!/usr/bin/env python3
"""
Database Setup Script
=====================

This script deploys the database schema to your Supabase project.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from supabase import create_client, Client
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install supabase psycopg2-binary python-dotenv")
    sys.exit(1)

def read_schema_file():
    """Read the database schema from file"""
    try:
        with open('supabase_schema.sql', 'r') as f:
            return f.read()
    except FileNotFoundError:
        print("❌ supabase_schema.sql file not found")
        return None
    except Exception as e:
        print(f"❌ Error reading schema file: {e}")
        return None

def deploy_schema_via_supabase():
    """Deploy schema using Supabase client"""
    print("🔌 Deploying schema via Supabase client...")
    
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not service_key:
        print("❌ Missing Supabase credentials in .env file")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(url, service_key)
        
        # Read schema
        schema_sql = read_schema_file()
        if not schema_sql:
            return False
        
        # Split schema into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        print(f"📝 Executing {len(statements)} SQL statements...")
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    # Use RPC to execute SQL
                    result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"   ✅ Statement {i}/{len(statements)} executed")
                except Exception as e:
                    print(f"   ⚠️  Statement {i} failed: {e}")
                    # Continue with other statements
        
        print("✅ Schema deployment via Supabase completed")
        return True
        
    except Exception as e:
        print(f"❌ Supabase deployment failed: {e}")
        return False

def deploy_schema_via_postgres():
    """Deploy schema using direct PostgreSQL connection"""
    print("🐘 Deploying schema via PostgreSQL connection...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Missing DATABASE_URL in .env file")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Read schema
        schema_sql = read_schema_file()
        if not schema_sql:
            return False
        
        # Execute schema
        cursor.execute(schema_sql)
        conn.commit()
        
        print("✅ Schema deployment via PostgreSQL completed")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Created tables: {', '.join(tables)}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL deployment failed: {e}")
        return False

def verify_schema():
    """Verify that the schema was deployed correctly"""
    print("\n🔍 Verifying schema deployment...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Missing DATABASE_URL in .env file")
        return False
    
    required_tables = [
        'users', 'user_notifications', 'teams', 'players', 
        'gameweeks', 'fixtures', 'gameweek_stats', 
        'player_history', 'live_monitor_history'
    ]
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check table existence
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = ANY(%s)
            ORDER BY table_name
        """, (required_tables,))
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        missing_tables = set(required_tables) - set(existing_tables)
        
        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        else:
            print(f"✅ All required tables exist: {', '.join(existing_tables)}")
            
            # Check RLS status
            cursor.execute("""
                SELECT tablename, rowsecurity 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = ANY(%s)
                ORDER BY tablename
            """, (required_tables,))
            
            rls_status = cursor.fetchall()
            all_rls_enabled = all(row[1] for row in rls_status)
            
            if all_rls_enabled:
                print("✅ Row Level Security enabled on all tables")
            else:
                print("⚠️  Some tables missing RLS")
                for table, rls in rls_status:
                    print(f"   {table}: {'✅' if rls else '❌'}")
            
            return True
            
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main setup function"""
    print("🗄️  FPL Monitor - Database Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("Run: python3 setup_environment.py")
        sys.exit(1)
    
    # Check if schema file exists
    if not os.path.exists('supabase_schema.sql'):
        print("❌ supabase_schema.sql file not found")
        sys.exit(1)
    
    print("🚀 Starting database setup...")
    
    # Try PostgreSQL deployment first (more reliable)
    if deploy_schema_via_postgres():
        if verify_schema():
            print("\n🎉 Database setup completed successfully!")
            print("\nNext steps:")
            print("1. Test the connection: python3 test_supabase_connection.py")
            print("2. Start the enhanced service: python3 fpl_monitor_enhanced.py")
        else:
            print("\n❌ Schema verification failed")
            sys.exit(1)
    else:
        print("\n❌ Database setup failed")
        print("\nAlternative: Deploy schema manually in Supabase dashboard:")
        print("1. Go to your Supabase project dashboard")
        print("2. Navigate to SQL Editor")
        print("3. Copy and paste the contents of supabase_schema.sql")
        print("4. Click 'Run' to execute the schema")
        sys.exit(1)

if __name__ == "__main__":
    main()
