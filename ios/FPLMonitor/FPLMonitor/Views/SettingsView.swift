//
//  SettingsView.swift
//  FPLMonitor
//
//  Settings and preferences view
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var notificationManager: NotificationManager
    @EnvironmentObject private var analyticsManager: AnalyticsManager
    @EnvironmentObject private var userManager: UserManager
    @State private var showingUserPreferences = false
    @State private var showingLeagueSwitcher = false
    
    var body: some View {
        NavigationView {
            List {
                // User Preferences Section
                Section {
                    NavigationLink(destination: UserPreferencesView()) {
                        SettingsRow(
                            icon: "person.circle.fill",
                            title: "User Preferences",
                            subtitle: "Customize your notification settings"
                        )
                    }
                    
                    NavigationLink(destination: NotificationFiltersView()) {
                        SettingsRow(
                            icon: "bell.badge.fill",
                            title: "Notification Filters",
                            subtitle: "Filter notifications by type"
                        )
                    }
                } header: {
                    Text("Preferences")
                }
                
                // App Settings Section
                Section {
                    ToggleRow(
                        icon: "bell.fill",
                        title: "Push Notifications",
                        subtitle: "Receive notifications on your device",
                        isOn: $notificationManager.userPreferences.pushEnabled
                    )
                    
                    ToggleRow(
                        icon: "envelope.fill",
                        title: "Email Notifications",
                        subtitle: "Receive notifications via email",
                        isOn: $notificationManager.userPreferences.emailEnabled
                    )
                    
                    NavigationLink(destination: QuietHoursView()) {
                        SettingsRow(
                            icon: "moon.fill",
                            title: "Quiet Hours",
                            subtitle: "Set times when you don't want notifications"
                        )
                    }
                } header: {
                    Text("Notifications")
                }
                
                // FPL Settings Section
                Section {
                    HStack {
                        Image(systemName: "person.fill")
                            .font(.title2)
                            .foregroundColor(.fplPrimary)
                            .frame(width: 30)
                        
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Manager")
                                .font(.fplBody)
                                .foregroundColor(.fplText)
                            
                            if let manager = userManager.currentManager {
                                Text(manager.playerName)
                                    .font(.caption)
                                    .foregroundColor(.fplSubtext)
                            } else {
                                Text("Not set")
                                    .font(.caption)
                                    .foregroundColor(.fplSubtext)
                            }
                        }
                        
                        Spacer()
                    }
                    .padding(.vertical, 4)
                    
                    HStack {
                        Image(systemName: "person.3.fill")
                            .font(.title2)
                            .foregroundColor(.fplPrimary)
                            .frame(width: 30)
                        
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Active League")
                                .font(.fplBody)
                                .foregroundColor(.fplText)
                            
                            if let league = userManager.activeLeague {
                                Text(league.name)
                                    .font(.caption)
                                    .foregroundColor(.fplSubtext)
                            } else {
                                Text("Not set")
                                    .font(.caption)
                                    .foregroundColor(.fplSubtext)
                            }
                        }
                        
                        Spacer()
                        
                        Button("Change") {
                            showingLeagueSwitcher = true
                        }
                        .font(.caption)
                        .foregroundColor(.fplPrimary)
                    }
                    .padding(.vertical, 4)
                    
                    // League Standings Navigation
                    if let league = userManager.activeLeague {
                        NavigationLink(destination: LeagueStandingsView(league: league)) {
                            SettingsRow(
                                icon: "chart.bar.fill",
                                title: "League Standings",
                                subtitle: "View detailed standings for \(league.name)"
                            )
                        }
                    }
                } header: {
                    Text("Fantasy Premier League")
                }
                
                // App Info Section
                Section {
                    SettingsRow(
                        icon: "info.circle.fill",
                        title: "App Version",
                        subtitle: "1.0.0"
                    )
                    
                    SettingsRow(
                        icon: "globe",
                        title: "API Status",
                        subtitle: "Connected"
                    )
                    
                    Button(action: {
                        analyticsManager.trackEvent(.appOpen)
                    }) {
                        SettingsRow(
                            icon: "arrow.clockwise",
                            title: "Refresh Data",
                            subtitle: "Sync with FPL servers"
                        )
                    }
                    
                    Button(action: {
                        userManager.resetAllData()
                    }) {
                        SettingsRow(
                            icon: "arrow.counterclockwise",
                            title: "Reset App",
                            subtitle: "Clear all data and restart onboarding"
                        )
                    }
                } header: {
                    Text("App Information")
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .sheet(isPresented: $showingLeagueSwitcher) {
                LeagueSwitcherView()
                    .environmentObject(userManager)
            }
        }
    }
}

struct SettingsRow: View {
    let icon: String
    let title: String
    let subtitle: String
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.fplPrimary)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.fplBody)
                    .foregroundColor(.fplText)
                
                Text(subtitle)
                    .font(.caption)
                    .foregroundColor(.fplSubtext)
            }
            
            Spacer()
        }
        .padding(.vertical, 4)
    }
}

struct ToggleRow: View {
    let icon: String
    let title: String
    let subtitle: String
    @Binding var isOn: Bool
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.fplPrimary)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.fplBody)
                    .foregroundColor(.fplText)
                
                Text(subtitle)
                    .font(.caption)
                    .foregroundColor(.fplSubtext)
            }
            
            Spacer()
            
            Toggle("", isOn: $isOn)
                .labelsHidden()
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Placeholder Views
struct UserPreferencesView: View {
    var body: some View {
        Text("User Preferences")
            .navigationTitle("User Preferences")
            .navigationBarTitleDisplayMode(.inline)
    }
}

struct NotificationFiltersView: View {
    var body: some View {
        Text("Notification Filters")
            .navigationTitle("Notification Filters")
            .navigationBarTitleDisplayMode(.inline)
    }
}

struct QuietHoursView: View {
    var body: some View {
        Text("Quiet Hours")
            .navigationTitle("Quiet Hours")
            .navigationBarTitleDisplayMode(.inline)
    }
}

struct FPLAccountView: View {
    var body: some View {
        Text("FPL Account")
            .navigationTitle("FPL Account")
            .navigationBarTitleDisplayMode(.inline)
    }
}

struct MiniLeaguesView: View {
    var body: some View {
        Text("Mini Leagues")
            .navigationTitle("Mini Leagues")
            .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    SettingsView()
        .environmentObject(NotificationManager())
        .environmentObject(AnalyticsManager())
}
