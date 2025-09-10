#!/usr/bin/env python3
"""
Simple Database Connection Test
==============================

Test database connection without Supabase client dependencies.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install psycopg2-binary python-dotenv")
    sys.exit(1)

def test_connection():
    """Test database connection"""
    print("🔌 Testing database connection...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Missing DATABASE_URL in .env file")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()['version']
        
        print(f"✅ Database connection successful")
        print(f"   PostgreSQL version: {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_schema():
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

def test_rls():
    """Test Row Level Security"""
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
            SELECT tablename, rowsecurity 
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

def test_functions():
    """Test database functions"""
    print("\n⚙️  Testing database functions...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Missing DATABASE_URL in .env file")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if functions exist
        cursor.execute("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_name IN ('get_user_notifications', 'mark_notifications_read', 'get_unread_count')
            ORDER BY routine_name
        """)
        
        functions = [row['routine_name'] for row in cursor.fetchall()]
        expected_functions = ['get_user_notifications', 'mark_notifications_read', 'get_unread_count']
        missing_functions = set(expected_functions) - set(functions)
        
        if missing_functions:
            print(f"❌ Missing functions: {', '.join(missing_functions)}")
            return False
        else:
            print(f"✅ All required functions exist: {', '.join(functions)}")
            return True
            
    except Exception as e:
        print(f"❌ Functions test failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Run all tests"""
    print("🧪 FPL Monitor - Database Connection Test")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("   Create .env file with database credentials")
        return
    
    # Run tests
    tests = [
        test_connection,
        test_schema,
        test_rls,
        test_functions
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
        print("🎉 Database is ready for FPL Monitor!")
    else:
        print(f"❌ {total - passed} tests failed ({passed}/{total})")
        print("🔧 Fix the issues above before proceeding")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
