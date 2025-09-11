# FPL Monitor iOS App - Current Design Documentation

## Overview
This document captures the current UI design and component structure of the FPL Monitor iOS app before implementing a radical redesign. The app is built with SwiftUI and follows a tab-based navigation structure.

## App Structure

### Main App Entry Point
- **File**: `FPLMonitorApp.swift`
- **Purpose**: Main app entry point with environment object setup
- **Key Components**:
  - NotificationManager
  - APIManager
  - AnalyticsManager
  - UserManager

### Content View Structure
- **File**: `ContentView.swift`
- **Purpose**: Root view that handles onboarding vs main app flow
- **Key Components**:
  - MainTabView (4 tabs)
  - OnboardingView (3-step process)

## Current Design System

### Color Palette
```swift
// FPL Color Scheme
static let fplPrimary = Color(red: 0.0, green: 0.4, blue: 0.8)      // FPL Blue
static let fplSecondary = Color(red: 0.9, green: 0.1, blue: 0.1)    // FPL Red
static let fplAccent = Color(red: 1.0, green: 0.8, blue: 0.0)       // Gold
static let fplBackground = Color(red: 0.95, green: 0.95, blue: 0.95) // Light Gray
static let fplCard = Color.white
static let fplText = Color.primary
static let fplSubtext = Color.secondary
```

### Typography
```swift
// FPL Typography
static let fplTitle = Font.largeTitle.weight(.bold)
static let fplHeadline = Font.title2.weight(.semibold)
static let fplBody = Font.body
static let fplCaption = Font.caption
static let fplButton = Font.headline.weight(.medium)
```

## Main Navigation Structure

### TabView with 4 Tabs
1. **Notifications Tab** (`NotificationTimelineView`)
   - Icon: `bell.fill`
   - Purpose: Main notifications timeline
   - Features: List of notifications, pull-to-refresh, empty state

2. **Standings Tab** (`LeagueView`)
   - Icon: `chart.line.uptrend.xyaxis`
   - Purpose: League standings and rankings

3. **Analytics Tab** (`AnalyticsView`)
   - Icon: `chart.bar.fill`
   - Purpose: Performance analytics and insights

4. **Settings Tab** (`SettingsView`)
   - Icon: `gear`
   - Purpose: App settings and preferences

## Key UI Components

### 1. NotificationTimelineView
- **Purpose**: Main notifications display
- **Layout**: NavigationView with List
- **Features**:
  - Empty state with icon and messaging
  - Notification cards with tap gestures
  - Pull-to-refresh functionality
  - Analytics tracking

### 2. OnboardingView
- **Purpose**: 3-step user onboarding process
- **Steps**:
  1. Welcome screen with feature highlights
  2. Manager search and selection
  3. League selection
- **Features**:
  - Progress bar
  - TabView with page style
  - Navigation buttons (Back/Next)
  - Skip options for optional steps

### 3. SettingsView
- **Purpose**: App configuration and preferences
- **Sections**:
  - User Preferences
  - Notification Settings
  - FPL Account Info
  - App Information
- **Features**:
  - Toggle switches for settings
  - Navigation links to sub-screens
  - Manager and league display

## Component Architecture

### Reusable Components
1. **SettingsRow**: Standard settings list item
2. **ToggleRow**: Settings item with toggle switch
3. **ManagerRow**: Manager selection list item
4. **FeatureRow**: Feature highlight in onboarding
5. **OnboardingLeagueRow**: League selection list item

### Button Styles
1. **PrimaryButtonStyle**: Main action buttons (blue background)
2. **SecondaryButtonStyle**: Secondary actions (blue outline)

## Current Visual Design Characteristics

### Layout Patterns
- **Navigation**: TabView with 4 main sections
- **Lists**: Standard SwiftUI List with custom styling
- **Cards**: Rounded rectangle cards with padding
- **Spacing**: Consistent 12-16px padding throughout

### Interactive Elements
- **Buttons**: Rounded corners (12px radius)
- **Cards**: Rounded corners with subtle shadows
- **Toggles**: Standard iOS toggle switches
- **Text Fields**: Rounded border style

### Color Usage
- **Primary**: FPL Blue for main actions and highlights
- **Secondary**: FPL Red for warnings/errors
- **Accent**: Gold for special highlights
- **Background**: Light gray for app background
- **Cards**: White for content areas

## Data Flow
- **State Management**: @StateObject and @EnvironmentObject
- **Navigation**: NavigationView and NavigationLink
- **Data Fetching**: Combine publishers with API managers
- **Persistence**: UserDefaults for user preferences

## Files to Preserve
All current UI files are backed up in:
`/Users/silverman/Documents/fpl-monitor/20250909 2/archive/ios_design_backup_20250910_210932/`

## Next Steps for Redesign
1. Maintain same component structure and functionality
2. Apply new color palette and typography
3. Update visual styling while preserving behavior
4. Test changes incrementally
5. Keep ability to rollback to current design

## Component Mapping for Redesign
- **MainTabView** → Keep structure, update styling
- **NotificationTimelineView** → Keep functionality, update appearance
- **OnboardingView** → Keep flow, update visual design
- **SettingsView** → Keep sections, update styling
- **All Row Components** → Update colors and spacing
- **Button Styles** → Update colors and appearance
