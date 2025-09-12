#!/usr/bin/env python3
"""
Setup Discord Alerts
====================

Interactive setup for Discord server monitoring alerts.
"""

import os
import requests
from dotenv import load_dotenv

def setup_discord_webhook():
    """Setup Discord webhook for alerts"""
    print("🔔 Discord Alert Setup")
    print("=" * 25)
    print("This will set up Discord alerts for your FPL Monitor server.")
    print("You'll get notifications when the server is down or has issues.")
    print()
    
    # Check if webhook already exists
    load_dotenv()
    existing_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    
    if existing_webhook and existing_webhook != "your-discord-webhook-url":
        print(f"✅ Discord webhook already configured: {existing_webhook[:50]}...")
        use_existing = input("Use existing webhook? (y/N): ").strip().lower()
        if use_existing == 'y':
            return existing_webhook
    
    print("To set up Discord alerts, you need to create a Discord webhook:")
    print()
    print("1. Open Discord and go to your server")
    print("2. Right-click on a channel (or create a new one for alerts)")
    print("3. Click 'Edit Channel' → 'Integrations' → 'Webhooks'")
    print("4. Click 'Create Webhook'")
    print("5. Copy the webhook URL")
    print()
    
    webhook_url = input("Enter your Discord webhook URL: ").strip()
    
    if not webhook_url:
        print("❌ No webhook URL provided")
        return None
    
    # Test the webhook
    print("\n🧪 Testing webhook...")
    test_payload = {
        "username": "FPL Monitor Test",
        "content": "🔔 **Test Alert** - Discord webhook is working correctly!"
    }
    
    try:
        response = requests.post(webhook_url, json=test_payload, timeout=10)
        if response.status_code in [200, 204]:
            print("✅ Webhook test successful!")
            print("   Check your Discord channel for the test message.")
        else:
            print(f"❌ Webhook test failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Webhook test error: {e}")
        return None
    
    # Update .env file
    print("\n💾 Updating .env file...")
    env_file = ".env"
    
    # Read existing .env
    env_content = ""
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Update or add webhook URL
    if "DISCORD_WEBHOOK_URL=" in env_content:
        # Replace existing
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith("DISCORD_WEBHOOK_URL="):
                lines[i] = f"DISCORD_WEBHOOK_URL={webhook_url}"
                break
        env_content = '\n'.join(lines)
    else:
        # Add new
        env_content += f"\n# Discord Webhook for Alerts\nDISCORD_WEBHOOK_URL={webhook_url}\n"
    
    # Write updated .env
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ .env file updated with Discord webhook")
    return webhook_url

def show_monitoring_commands():
    """Show commands for running the monitor"""
    print("\n🚀 Discord Monitoring Commands")
    print("=" * 35)
    print("To start monitoring your FPL Monitor server:")
    print()
    print("1. Start Discord monitoring (runs continuously):")
    print("   python3 discord_server_monitor.py")
    print()
    print("2. Run a single health check:")
    print("   python3 -c \"from discord_server_monitor import DiscordServerMonitor; DiscordServerMonitor().run_health_check()\"")
    print()
    print("3. Test webhook only:")
    print("   python3 -c \"from discord_server_monitor import DiscordServerMonitor; DiscordServerMonitor().send_discord_alert('Test', 'This is a test message')\"")
    print()
    print("The monitor will check your server every 5 minutes and send Discord alerts for:")
    print("• Server down")
    print("• Monitoring service not active")
    print("• FPL API connection lost")
    print("• Database issues")
    print("• Any other problems detected")

def main():
    """Main setup function"""
    print("🎯 FPL Monitor - Discord Alert Setup")
    print("=" * 40)
    
    webhook_url = setup_discord_webhook()
    
    if webhook_url:
        print("\n🎉 Discord alerts configured successfully!")
        show_monitoring_commands()
    else:
        print("\n❌ Discord alert setup failed")
        print("   You can run this script again to retry")

if __name__ == "__main__":
    main()
