# FPL Monitor iOS App - Rollback Guide

## Overview
This guide explains how to rollback the iOS app to the original design if needed. The original design has been preserved in the backup directory.

## Backup Location
The original design files are backed up at:
`/Users/silverman/Documents/fpl-monitor/20250909 2/archive/ios_design_backup_20250910_210932/`

## Files Modified in Redesign
The following files were modified to implement the new design:

1. **ContentView.swift** - Updated main tab structure and navigation
2. **DesignSystem.swift** - New design system file (can be deleted)
3. **NotificationTimelineView.swift** - Updated with earnings-style layout
4. **OnboardingView.swift** - Updated to use new design system
5. **SettingsView.swift** - Updated to use new design system

## Rollback Steps

### Option 1: Complete Rollback (Recommended)
To completely restore the original design:

```bash
# Navigate to the project directory
cd "/Users/silverman/Documents/fpl-monitor/20250909 2"

# Remove the new design system file
rm ios/FPLMonitor/FPLMonitor/DesignSystem.swift

# Restore original files from backup
cp archive/ios_design_backup_20250910_210932/FPLMonitor/ContentView.swift ios/FPLMonitor/FPLMonitor/
cp archive/ios_design_backup_20250910_210932/FPLMonitor/Views/NotificationTimelineView.swift ios/FPLMonitor/FPLMonitor/Views/
cp archive/ios_design_backup_20250910_210932/FPLMonitor/Views/OnboardingView.swift ios/FPLMonitor/FPLMonitor/Views/
cp archive/ios_design_backup_20250910_210932/FPLMonitor/Views/SettingsView.swift ios/FPLMonitor/FPLMonitor/Views/

# Clean and rebuild the project
# In Xcode: Product -> Clean Build Folder, then build again
```

### Option 2: Selective Rollback
To rollback specific components while keeping others:

1. **Restore original ContentView.swift**:
   ```bash
   cp archive/ios_design_backup_20250910_210932/FPLMonitor/ContentView.swift ios/FPLMonitor/FPLMonitor/
   ```

2. **Restore original NotificationTimelineView.swift**:
   ```bash
   cp archive/ios_design_backup_20250910_210932/FPLMonitor/Views/NotificationTimelineView.swift ios/FPLMonitor/FPLMonitor/Views/
   ```

3. **Restore original OnboardingView.swift**:
   ```bash
   cp archive/ios_design_backup_20250910_210932/FPLMonitor/Views/OnboardingView.swift ios/FPLMonitor/FPLMonitor/Views/
   ```

4. **Restore original SettingsView.swift**:
   ```bash
   cp archive/ios_design_backup_20250910_210932/FPLMonitor/Views/SettingsView.swift ios/FPLMonitor/FPLMonitor/Views/
   ```

## What Changed in the Redesign

### New Design System
- **Colors**: Updated to use neutral tones with accent colors
- **Typography**: Standardized font weights and sizes
- **Spacing**: Consistent spacing system using Spacing constants
- **Components**: New button styles and card designs

### Navigation Changes
- **Tab Structure**: Changed from standard TabView to custom bottom navigation
- **Tab Names**: Updated to financial app style (Home, Earn, Chat, Invest)
- **Action Buttons**: Added Receive, Send, Swap buttons

### Layout Changes
- **NotificationTimelineView**: Added earnings-style header with stats
- **OnboardingView**: Updated to use new design system
- **SettingsView**: Updated row components and styling

## Testing the Rollback

After rolling back:

1. **Build the project** in Xcode
2. **Test navigation** between tabs
3. **Test onboarding flow** (if applicable)
4. **Test settings** functionality
5. **Verify notifications** display correctly

## Troubleshooting

### Build Errors
If you encounter build errors after rollback:
1. Clean the build folder (Product -> Clean Build Folder)
2. Delete derived data
3. Rebuild the project

### Missing Files
If any files are missing:
1. Check the backup directory exists
2. Verify file paths are correct
3. Restore from backup again

### Design Inconsistencies
If some components still use the new design:
1. Check for any remaining references to DesignSystem
2. Look for any custom styling that wasn't rolled back
3. Restore the specific component from backup

## Backup Verification

To verify the backup is complete:
```bash
# List all files in backup
ls -la "/Users/silverman/Documents/fpl-monitor/20250909 2/archive/ios_design_backup_20250910_210932/FPLMonitor/"

# Compare file sizes
ls -la ios/FPLMonitor/FPLMonitor/ContentView.swift
ls -la archive/ios_design_backup_20250910_210932/FPLMonitor/ContentView.swift
```

## Future Design Changes

If you want to make further design changes:
1. Create a new backup before making changes
2. Document what changes you're making
3. Test thoroughly before committing
4. Keep the rollback guide updated

## Support

If you encounter issues with the rollback:
1. Check this guide first
2. Verify file paths and permissions
3. Ensure Xcode is closed before making file changes
4. Clean and rebuild after rollback
