#!/bin/bash

echo "Adding LSSupportsOpeningDocumentsInPlace to Info.plist..."

# Path to the Info.plist file
INFO_PLIST_PATH="ios/FPLMonitor/FPLMonitor/Info.plist"

# Check if Info.plist exists
if [ ! -f "$INFO_PLIST_PATH" ]; then
    echo "Error: Info.plist not found at $INFO_PLIST_PATH"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Add LSSupportsOpeningDocumentsInPlace entry
echo "Adding LSSupportsOpeningDocumentsInPlace entry..."

# Use PlistBuddy to add the entry
/usr/libexec/PlistBuddy -c "Add :LSSupportsOpeningDocumentsInPlace bool false" "$INFO_PLIST_PATH" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :LSSupportsOpeningDocumentsInPlace false" "$INFO_PLIST_PATH"

echo "✅ Added LSSupportsOpeningDocumentsInPlace entry to Info.plist"
echo "This will suppress the document support warning in Xcode"