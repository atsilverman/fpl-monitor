#!/usr/bin/env python3
"""
Test Supabase Connection
========================

Simple script to test Supabase database connection and verify schema.
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

def test_supabase_connection():
    """Test Supabase client connection"""
    print("🔌 Testing Supabase connection...")
    
    # Get credentials
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env file")
        return False
    
    try:
        # Create client
        supabase: Client = create_client(url, key)
        
        # Test connection with a simple query
        result = supabase.table("teams").select("id, name").limit(1).execute()
        
        print(f"✅ Supabase connection successful")
        print(f"   URL: {url}")
        print(f"   Response: {len(result.data)} rows returned")
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def test_postgres_connection():
    """Test direct PostgreSQL connection"""
    print("\n🐘 Testing PostgreSQL connection...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Missing DATABASE_URL in .env file")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test query
        cursor.execute("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'")
        result = cursor.fetchone()
        
        print(f"✅ PostgreSQL connection successful")
        print(f"   Tables in public schema: {result['table_count']}")
        
        # Check if our tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'teams', 'players', 'gameweeks', 'fixtures', 'gameweek_stats')
            ORDER BY table_name
        """)
        tables = [row['table_name'] for row in cursor.fetchall()]
        
        print(f"   FPL tables found: {', '.join(tables)}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

def test_schema_tables():
    """Test that all required tables exist"""
    print("\n📋 Testing database schema...")
    
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check table existence
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = ANY(%s)
            ORDER BY table_name
        """, (required_tables,))
        
        existing_tables = [row['table_name'] for row in cursor.fetchall()]
        missing_tables = set(required_tables) - set(existing_tables)
        
        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            print("   Run the supabase_schema.sql script in Supabase SQL Editor")
            return False
        else:
            print(f"✅ All required tables exist: {', '.join(existing_tables)}")
            return True
            
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_rls_policies():
    """Test that RLS policies are enabled"""
    print("\n🔒 Testing Row Level Security...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Missing DATABASE_URL in .env file")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check RLS status
        cursor.execute("""
            SELECT schemaname, tablename, rowsecurity 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('users', 'user_notifications', 'teams', 'players')
            ORDER BY tablename
        """)
        
        rls_status = cursor.fetchall()
        all_enabled = all(row['rowsecurity'] for row in rls_status)
        
        if all_enabled:
            print("✅ Row Level Security enabled on all tables")
            for row in rls_status:
                print(f"   {row['tablename']}: {'✅' if row['rowsecurity'] else '❌'}")
            return True
        else:
            print("❌ Some tables missing RLS")
            for row in rls_status:
                print(f"   {row['tablename']}: {'✅' if row['rowsecurity'] else '❌'}")
            return False
            
    except Exception as e:
        print(f"❌ RLS test failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Run all tests"""
    print("🧪 FPL Monitor - Supabase Connection Test")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("   Create .env file with Supabase credentials")
        print("   See SUPABASE_SETUP.md for details")
        return
    
    # Run tests
    tests = [
        test_supabase_connection,
        test_postgres_connection,
        test_schema_tables,
        test_rls_policies
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All tests passed ({passed}/{total})")
        print("🎉 Supabase is ready for FPL Monitor!")
    else:
        print(f"❌ {total - passed} tests failed ({passed}/{total})")
        print("🔧 Fix the issues above before proceeding")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
