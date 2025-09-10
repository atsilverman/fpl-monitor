#!/bin/bash
# Script to help add location permission to Info.plist

echo "To add location permission, add this entry in Xcode:"
echo ""
echo "1. In Xcode, go to the Info tab of your FPLMonitor target"
echo "2. Click the '+' button in Custom iOS Target Properties"
echo "3. Add 'NSLocationWhenInUseUsageDescription' and set it to:"
echo "   'FPL Monitor needs location access to detect your timezone for accurate notification times.'"
echo ""
echo "This will allow the app to request location permission for timezone detection."
