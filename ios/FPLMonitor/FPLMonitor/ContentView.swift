//
//  ContentView.swift
//  FPLMonitor
//
//  Main app view with tab navigation
//

import SwiftUI

struct ContentView: View {
    @StateObject private var userManager = UserManager.shared
    
    var body: some View {
        Group {
            if userManager.hasCompletedOnboarding {
                MainTabView()
            } else {
                OnboardingView()
            }
        }
        .onAppear {
            print("🔍 ContentView: hasCompletedOnboarding = \(userManager.hasCompletedOnboarding)")
            print("🔍 ContentView: currentManager = \(userManager.currentManager?.playerName ?? "nil")")
            print("🔍 ContentView: activeLeague = \(userManager.activeLeague?.name ?? "nil")")
        }
    }
}

struct MainTabView: View {
    @EnvironmentObject private var notificationManager: NotificationManager
    @EnvironmentObject private var analyticsManager: AnalyticsManager
    
    var body: some View {
        TabView {
            // Notifications Tab
            NotificationTimelineView()
                .tabItem {
                    Image(systemName: "bell.fill")
                    Text("Notifications")
                }
            
            // Analytics Tab
            AnalyticsView()
                .tabItem {
                    Image(systemName: "chart.bar.fill")
                    Text("Analytics")
                }
            
            // Settings Tab
            SettingsView()
                .tabItem {
                    Image(systemName: "gear")
                    Text("Settings")
                }
        }
        .accentColor(.fplPrimary)
        .onAppear {
            analyticsManager.trackEvent(.appOpen)
        }
    }
}

// MARK: - FPL Color Scheme
extension Color {
    static let fplPrimary = Color(red: 0.0, green: 0.4, blue: 0.8)      // FPL Blue
    static let fplSecondary = Color(red: 0.9, green: 0.1, blue: 0.1)    // FPL Red
    static let fplAccent = Color(red: 1.0, green: 0.8, blue: 0.0)       // Gold
    static let fplBackground = Color(red: 0.95, green: 0.95, blue: 0.95) // Light Gray
    static let fplCard = Color.white
    static let fplText = Color.primary
    static let fplSubtext = Color.secondary
}

// MARK: - FPL Typography
extension Font {
    static let fplTitle = Font.largeTitle.weight(.bold)
    static let fplHeadline = Font.title2.weight(.semibold)
    static let fplBody = Font.body
    static let fplCaption = Font.caption
    static let fplButton = Font.headline.weight(.medium)
}

#Preview {
    ContentView()
        .environmentObject(NotificationManager())
        .environmentObject(APIManager())
        .environmentObject(AnalyticsManager())
}
