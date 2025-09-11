#!/usr/bin/env python3
"""
Deploy FPL Monitor to DigitalOcean
Updates the existing server with the new working code
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            return True
        else:
            print(f"❌ {description} - Failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Exception: {e}")
        return False

def main():
    print("🚀 Deploying FPL Monitor to DigitalOcean")
    print("=" * 50)
    
    # Server details
    DROPLET_IP = "138.68.28.59"
    DROPLET_USER = "root"
    
    print(f"📍 Target: {DROPLET_USER}@{DROPLET_IP}")
    
    # Check if we can connect
    if not run_command(f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {DROPLET_USER}@{DROPLET_IP} 'echo Connected'", "Testing SSH connection"):
        print("❌ Cannot connect to DigitalOcean server")
        print("Please check:")
        print("1. Server is running")
        print("2. SSH key is configured")
        print("3. Firewall allows SSH (port 22)")
        return False
    
    # Create deployment package
    print("\n📦 Creating deployment package...")
    
    # Create a simple deployment script
    deploy_script = f"""#!/bin/bash
set -e

echo "🚀 Updating FPL Monitor on DigitalOcean..."

# Update system
apt update -y

# Install Python dependencies
apt install -y python3 python3-pip python3-venv

# Create app directory
mkdir -p /opt/fpl-monitor
cd /opt/fpl-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install fastapi uvicorn requests psycopg2-binary python-dotenv pytz websockets

# Create the simple API server
cat > simple_api.py << 'EOF'
#!/usr/bin/env python3
import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="FPL Monitor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
HEADERS = {{
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {{SUPABASE_KEY}}',
    'Content-Type': 'application/json'
}}

def get_supabase_data(endpoint: str, params: dict = None):
    try:
        response = requests.get(
            f"{{SUPABASE_URL}}/rest/v1/{{endpoint}}",
            headers=HEADERS,
            params=params or {{}},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {{"message": "FPL Monitor API", "status": "running"}}

@app.get("/fpl/players")
async def get_players(limit: int = 100, fpl_id: int = None):
    params = {{"limit": limit}}
    if fpl_id:
        params["fpl_id"] = f"eq.{{fpl_id}}"
    return get_supabase_data("players", params)

@app.get("/fpl/teams")
async def get_teams():
    return get_supabase_data("teams")

@app.get("/fpl/fixtures")
async def get_fixtures():
    return get_supabase_data("fixtures")

@app.get("/fpl/gameweeks")
async def get_gameweeks():
    return get_supabase_data("gameweeks")

@app.get("/health")
async def health_check():
    try:
        test_data = get_supabase_data("players", {{"limit": 1}})
        return {{
            "status": "healthy",
            "supabase_connected": True,
            "players_count": len(test_data) if test_data else 0
        }}
    except Exception as e:
        return {{
            "status": "unhealthy",
            "supabase_connected": False,
            "error": str(e)
        }}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# Create environment file template
cat > .env.template << 'EOF'
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
EOF

# Create systemd service
cat > /etc/systemd/system/fpl-monitor.service << 'EOF'
[Unit]
Description=FPL Monitor API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpl-monitor
Environment=PATH=/opt/fpl-monitor/venv/bin
ExecStart=/opt/fpl-monitor/venv/bin/python simple_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Make scripts executable
chmod +x simple_api.py

echo "✅ FPL Monitor updated successfully!"
echo "📝 Next steps:"
echo "1. Copy your .env file to /opt/fpl-monitor/.env"
echo "2. Run: systemctl enable fpl-monitor"
echo "3. Run: systemctl start fpl-monitor"
echo "4. Check status: systemctl status fpl-monitor"
"""
    
    # Write deployment script to file
    with open("deploy_script.sh", "w") as f:
        f.write(deploy_script)
    
    # Make it executable
    os.chmod("deploy_script.sh", 0o755)
    
    # Copy deployment script to server
    if not run_command(f"scp deploy_script.sh {DROPLET_USER}@{DROPLET_IP}:/tmp/", "Copying deployment script"):
        return False
    
    # Run deployment script on server
    if not run_command(f"ssh {DROPLET_USER}@{DROPLET_IP} 'bash /tmp/deploy_script.sh'", "Running deployment on server"):
        return False
    
    # Clean up
    os.remove("deploy_script.sh")
    
    print("\n🎉 Deployment completed!")
    print(f"🌐 Your API should be available at: http://{DROPLET_IP}:8000")
    print("\n📝 Next steps:")
    print("1. Copy your .env file to the server:")
    print(f"   scp .env {DROPLET_USER}@{DROPLET_IP}:/opt/fpl-monitor/.env")
    print("2. Start the service:")
    print(f"   ssh {DROPLET_USER}@{DROPLET_IP} 'systemctl enable fpl-monitor && systemctl start fpl-monitor'")
    print("3. Check status:")
    print(f"   ssh {DROPLET_USER}@{DROPLET_IP} 'systemctl status fpl-monitor'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
