//
//  ContentView.swift
//  FPLMonitor
//
//  Main app view with tab navigation
//

import SwiftUI

// MARK: - FPL Color Scheme
extension Color {
    static let fplPrimary = Color(red: 0.0, green: 0.4, blue: 0.8)      // FPL Blue
    static let fplSecondary = Color(red: 0.9, green: 0.1, blue: 0.1)    // FPL Red
    static let fplAccent = Color(red: 1.0, green: 0.8, blue: 0.0)       // Gold
    static let fplBackground = Color(hex: "F8F8FA")                      // Light Gray Background
    static let fplCard = Color(hex: "FFFFFF")                            // White Card Background
    static let fplCardBorder = Color(hex: "E5E5E5")                      // Light Gray Border
    static let fplText = Color.primary
    static let fplSubtext = Color.secondary
}

// MARK: - Color Extension for Hex Support
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }

        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

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
    @EnvironmentObject private var userManager: UserManager
    
    var body: some View {
        TabView {
            // Notifications Tab
            NotificationTimelineView()
                .tabItem {
                    Image(systemName: "bell.fill")
                    Text("Notifications")
                }
            
            // Standings Tab
            LeagueView()
                .tabItem {
                    Image(systemName: "chart.line.uptrend.xyaxis")
                    Text("Standings")
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
