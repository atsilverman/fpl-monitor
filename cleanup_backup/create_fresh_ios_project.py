#!/usr/bin/env python3
"""
Create a fresh iOS project with all Swift files
"""

import os
import shutil
from pathlib import Path

def create_fresh_ios_project():
    """Create a completely fresh iOS project"""
    
    print("🚀 Creating Fresh iOS Project")
    print("=" * 40)
    
    # Create new project directory
    new_project_dir = Path("/Users/silverman/Desktop/fpl-monitor/ios/FPLMonitorFresh")
    if new_project_dir.exists():
        shutil.rmtree(new_project_dir)
    
    new_project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create project structure
    app_dir = new_project_dir / "FPLMonitor"
    app_dir.mkdir(exist_ok=True)
    
    # Copy all Swift files
    source_dir = Path("/Users/silverman/Desktop/fpl-monitor/ios/FPLMonitor/FPLMonitor")
    target_dir = new_project_dir / "FPLMonitor"
    
    if source_dir.exists():
        for file in source_dir.rglob("*.swift"):
            relative_path = file.relative_to(source_dir)
            target_file = target_dir / relative_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target_file)
            print(f"✅ Copied: {relative_path}")
        
        # Copy Assets.xcassets
        assets_source = source_dir / "Assets.xcassets"
        if assets_source.exists():
            assets_target = target_dir / "Assets.xcassets"
            shutil.copytree(assets_source, assets_target)
            print("✅ Copied: Assets.xcassets")
        
        # Copy Info.plist
        info_plist_source = source_dir / "Info.plist"
        if info_plist_source.exists():
            info_plist_target = target_dir / "Info.plist"
            shutil.copy2(info_plist_source, info_plist_target)
            print("✅ Copied: Info.plist")
    
    print(f"\n📁 New project created at: {new_project_dir}")
    print("\n📋 Next Steps:")
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
    print("11. Replace the generated files with files from FPLMonitorFresh/")
    print("12. Build and run!")
    
    return new_project_dir

if __name__ == "__main__":
    create_fresh_ios_project()
