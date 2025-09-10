#!/bin/bash
# FPL Mobile Monitor Deployment Script
# Deploys to DigitalOcean App Platform

set -e

echo "🚀 Deploying FPL Mobile Monitor to DigitalOcean..."

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl is not installed. Please install it first:"
    echo "   https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Check if user is authenticated
if ! doctl account get &> /dev/null; then
    echo "❌ Please authenticate with doctl first:"
    echo "   doctl auth init"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy env.example to .env and fill in your values."
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
required_vars=("SUPABASE_URL" "SUPABASE_ANON_KEY" "DATABASE_URL")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set in .env file"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Create or update the app
echo "📦 Creating/updating DigitalOcean app..."

if doctl apps get fpl-monitor &> /dev/null; then
    echo "🔄 Updating existing app..."
    doctl apps update fpl-monitor --spec .do/app.yaml
else
    echo "🆕 Creating new app..."
    doctl apps create --spec .do/app.yaml
fi

echo "✅ Deployment initiated!"

# Get app status
echo "📊 Checking app status..."
doctl apps get fpl-monitor

echo "🎉 Deployment complete!"
echo "📱 Your FPL Monitor API is now running on DigitalOcean App Platform"
echo "🔗 Check the app URL in the DigitalOcean dashboard"
