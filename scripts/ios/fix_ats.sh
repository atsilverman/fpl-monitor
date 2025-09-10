#!/bin/bash
# Script to add ATS settings to iOS project

echo "Adding App Transport Security settings to iOS project..."

# Find the project.pbxproj file
PROJECT_FILE="ios/FPLMonitor/FPLMonitor.xcodeproj/project.pbxproj"

if [ -f "$PROJECT_FILE" ]; then
    echo "Found project file: $PROJECT_FILE"
    echo "You need to manually add ATS settings in Xcode:"
    echo "1. Open Xcode"
    echo "2. Select FPLMonitor project"
    echo "3. Select FPLMonitor target"
    echo "4. Go to Info tab"
    echo "5. Add 'App Transport Security Settings' with:"
    echo "   - Allow Arbitrary Loads: YES"
    echo "   - Exception Domains > localhost > Allow Insecure HTTP Loads: YES"
else
    echo "Project file not found: $PROJECT_FILE"
fi
