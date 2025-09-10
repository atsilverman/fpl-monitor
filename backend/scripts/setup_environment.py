#!/usr/bin/env python3
"""
Environment Setup Script
========================

This script helps you set up the environment variables for the FPL Monitor project.
"""

import os
import sys

def create_env_file():
    """Create .env file with Supabase credentials"""
    
    print("🔧 Setting up environment variables...")
    
    # Supabase credentials (provided by user)
    supabase_url = "https://ukeptogquyuxaohgvhwd.supabase.co"
    supabase_anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrZXB0b2dxdXl1eGFvaGd2aHdkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcyOTQ4MzUsImV4cCI6MjA3Mjg3MDgzNX0.GwugiB7YcpnCn1BGAc48Bd0LzllgfWXayhXeFBPU09Y"
    supabase_service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrZXB0b2dxdXl1eGFvaGd2aHdkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcyOTQ4MzUsImV4cCI6MjA3Mjg3MDgzNX0.GwugiB7YcpnCn1BGAc48Bd0LzllgfWXayhXeFBPU09Y"
    
    # Get database password from user
    print("\n📝 Please provide your Supabase database password:")
    print("   (You can find this in your Supabase project settings)")
    db_password = input("Database Password: ").strip()
    
    if not db_password:
        print("❌ Database password is required")
        return False
    
    # Create .env content
    env_content = f"""# Supabase Configuration
SUPABASE_URL={supabase_url}
SUPABASE_ANON_KEY={supabase_anon_key}
SUPABASE_SERVICE_ROLE_KEY={supabase_service_key}

# Database URL for direct PostgreSQL access
DATABASE_URL=postgresql://postgres:{db_password}@db.ukeptogquyuxaohgvhwd.supabase.co:5432/postgres

# FPL Configuration
FPL_MINI_LEAGUE_ID=814685

# Optional: DigitalOcean Configuration (for deployment)
# DIGITALOCEAN_ACCESS_TOKEN=your_token_here
# DIGITALOCEAN_REGION=nyc3
"""
    
    # Write .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ .env file created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 FPL Monitor - Environment Setup")
    print("=" * 40)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        print("⚠️  .env file already exists")
        overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("❌ Setup cancelled")
            return
    
    # Create .env file
    if create_env_file():
        print("\n🎉 Environment setup complete!")
        print("\nNext steps:")
        print("1. Run the database schema: python3 setup_database.py")
        print("2. Test the connection: python3 test_supabase_connection.py")
        print("3. Start the enhanced service: python3 fpl_monitor_enhanced.py")
    else:
        print("\n❌ Environment setup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
