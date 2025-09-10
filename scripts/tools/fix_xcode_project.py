#!/usr/bin/env python3
"""
Fix Xcode project Info.plist duplicate issue
"""

import os
import re
import shutil
from pathlib import Path

def fix_xcode_project():
    """Fix the duplicate Info.plist issue in Xcode project"""
    
    project_path = Path("/Users/silverman/Desktop/fpl-monitor/ios/FPLMonitor/FPLMonitor.xcodeproj/project.pbxproj")
    
    if not project_path.exists():
        print("❌ Xcode project not found!")
        return False
    
    print("🔧 Fixing Xcode project Info.plist duplicate issue...")
    
    # Read the project file
    with open(project_path, 'r') as f:
        content = f.read()
    
    # Count Info.plist references
    info_plist_refs = content.count('Info.plist')
    print(f"📊 Found {info_plist_refs} Info.plist references")
    
    # Look for duplicate copy commands
    copy_commands = re.findall(r'PBXResourcesBuildPhase.*?Info\.plist.*?PBXResourcesBuildPhase', content, re.DOTALL)
    
    if len(copy_commands) > 1:
        print("⚠️  Found duplicate Info.plist in Copy Bundle Resources")
        print("🔧 This needs to be fixed manually in Xcode")
        print("\n📋 Manual Fix Instructions:")
        print("1. Open Xcode")
        print("2. Open FPLMonitor.xcodeproj")
        print("3. Select the FPLMonitor project (top level)")
        print("4. Select the FPLMonitor target")
        print("5. Go to 'Build Phases' tab")
        print("6. Expand 'Copy Bundle Resources'")
        print("7. Find and remove the duplicate Info.plist entry")
        print("8. Keep only one Info.plist reference")
        print("9. Build the project")
        return False
    
    print("✅ No duplicate Info.plist found in project file")
    return True

def create_fresh_project():
    """Create a fresh Xcode project as backup"""
    
    print("\n🔄 Creating fresh Xcode project as backup...")
    
    # Create backup of current project
    backup_path = Path("/Users/silverman/Desktop/fpl-monitor/ios/FPLMonitor_backup")
    if backup_path.exists():
        shutil.rmtree(backup_path)
    
    current_path = Path("/Users/silverman/Desktop/fpl-monitor/ios/FPLMonitor")
    shutil.copytree(current_path, backup_path)
    print(f"✅ Backup created at: {backup_path}")
    
    print("\n📋 Fresh Project Creation Instructions:")
    print("1. Open Xcode")
    print("2. File → New → Project")
    print("3. iOS → App")
    print("4. Product Name: FPLMonitor")
    print("5. Bundle Identifier: com.silverman.fplmonitor")
    print("6. Language: Swift")
    print("7. Interface: SwiftUI")
    print("8. Use Core Data: No")
    print("9. Include Tests: No")
    print("10. Create the project")
    print("11. Copy all Swift files from backup to new project")
    print("12. Add Info.plist configuration")
    print("13. Build and run")

if __name__ == "__main__":
    print("🚀 FPL Monitor - Xcode Project Fixer")
    print("=" * 50)
    
    if fix_xcode_project():
        print("\n✅ Project file looks good!")
    else:
        print("\n⚠️  Manual fix required")
        create_fresh_project()
    
    print("\n🎯 Next Steps:")
    print("1. Fix the Xcode project (manual or fresh)")
    print("2. Test the iOS app in simulator")
    print("3. Enhance the UI with custom designs")
    print("4. Test push notifications on device")
    print("5. Deploy to production")
