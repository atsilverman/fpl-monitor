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
    static let fplBackground = Color(hex: "F8F9FD")                      // Light Blue Background
    static let fplAppBackground = Color(hex: "EFF0F4")                   // Main App Background
    static let fplCard = Color(hex: "F4F5F9")                            // Light Gray Card Background
    static let fplCardBorder = Color(hex: "FFFFFF")                      // Pure White Border
    static let fplText = Color(hex: "292D38")                            // Dark Text Color
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
        .background(Color.fplAppBackground)
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
    @State private var selectedTab = 0
    
    var body: some View {
        ZStack {
            // Main Content
            Group {
                switch selectedTab {
                case 0:
                    NotificationTimelineView()
                case 1:
                    LeagueView()
                case 2:
                    AnalyticsView()
                default:
                    NotificationTimelineView()
                }
            }
            .background(Color.fplAppBackground)
            .onAppear {
                analyticsManager.trackEvent(.appOpen)
            }
            
            // Floating Dock
            VStack {
                Spacer()
                FloatingDock(selectedTab: $selectedTab)
                    .padding(.bottom, 20)
            }
        }
    }
}

struct FloatingDock: View {
    @Binding var selectedTab: Int
    
    var body: some View {
        ZStack {
            // Background
            RoundedRectangle(cornerRadius: 25)
                .fill(.ultraThinMaterial)
                .overlay(
                    RoundedRectangle(cornerRadius: 25)
                        .stroke(Color.white, lineWidth: 1)
                )
                .shadow(color: .black.opacity(0.15), radius: 10, x: 0, y: 5)
                .frame(width: 200, height: 50)
            
            // Sliding indicator - positioned behind the tabs
            HStack(spacing: 0) {
                RoundedRectangle(cornerRadius: 24)
                    .fill(Color.fplText)
                    .frame(width: 60, height: 44)
                    .offset(x: CGFloat(selectedTab) * 66.67 + 3.33)
                    .animation(.spring(response: 0.3, dampingFraction: 0.7), value: selectedTab)
                Spacer()
            }
            .frame(width: 200)
            .padding(.horizontal, 5)
            
            // Tab items container - on top of the indicator
            HStack(spacing: 0) {
                DockTabItem(
                    icon: "calendar.day.timeline.left",
                    isSelected: selectedTab == 0
                ) {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        selectedTab = 0
                    }
                }
                
                DockTabItem(
                    icon: "chart.line.uptrend.xyaxis",
                    isSelected: selectedTab == 1
                ) {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        selectedTab = 1
                    }
                }
                
                DockTabItem(
                    icon: "chart.bar.fill",
                    isSelected: selectedTab == 2
                ) {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        selectedTab = 2
                    }
                }
            }
            .frame(width: 200)
        }
        .scaleEffect(1.15) // Scale entire dock by 15%
    }
}

struct DockTabItem: View {
    let icon: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 18, weight: .medium))
                .foregroundColor(isSelected ? .white : .fplSubtext)
                .frame(width: 66.67, height: 40)
        }
        .buttonStyle(PlainButtonStyle())
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
