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

// MARK: - User Preferences View
struct UserPreferencesView: View {
    @EnvironmentObject private var notificationManager: NotificationManager
    @EnvironmentObject private var apiManager: APIManager
    @State private var isLoading = false
    @State private var showingAlert = false
    @State private var alertMessage = ""
    
    var body: some View {
        Form {
            // FPL Manager ID Section
            Section("FPL Manager") {
                HStack {
                    Text("Manager ID")
                    Spacer()
                    TextField("Enter your FPL Manager ID", value: $notificationManager.userPreferences.fplManagerId, format: .number)
                        .keyboardType(.numberPad)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .frame(width: 120)
                }
                
                HStack {
                    Text("Mini Leagues")
                    Spacer()
                    TextField("Enter league IDs (comma separated)", text: $notificationManager.userPreferences.miniLeagueIds)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .frame(width: 200)
                }
            }
            
            // Notification Frequency Section
            Section("Notification Frequency") {
                Picker("Frequency", selection: $notificationManager.userPreferences.frequency) {
                    Text("Immediate").tag("immediate")
                    Text("Every 5 minutes").tag("5min")
                    Text("Every 15 minutes").tag("15min")
                    Text("Every hour").tag("hourly")
                    Text("Daily digest").tag("daily")
                }
                .pickerStyle(MenuPickerStyle())
            }
            
            // Timezone Section
            Section("Timezone") {
                HStack {
                    Text("Current Timezone")
                    Spacer()
                    Text(notificationManager.userPreferences.timezone)
                        .foregroundColor(.secondary)
                }
            }
            
            // Save Button
            Section {
                Button("Save Preferences") {
                    savePreferences()
                }
                .frame(maxWidth: .infinity)
                .disabled(isLoading)
            }
        }
        .navigationTitle("User Preferences")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Preferences", isPresented: $showingAlert) {
            Button("OK") { }
        } message: {
            Text(alertMessage)
        }
        .onAppear {
            loadPreferences()
        }
    }
    
    private func loadPreferences() {
        isLoading = true
        apiManager.fetchUserPreferences { result in
            DispatchQueue.main.async {
                isLoading = false
                switch result {
                case .success(let preferences):
                    notificationManager.userPreferences = preferences
                case .failure(let error):
                    alertMessage = "Failed to load preferences: \(error.localizedDescription)"
                    showingAlert = true
                }
            }
        }
    }
    
    private func savePreferences() {
        isLoading = true
        apiManager.saveUserPreferences(notificationManager.userPreferences) { result in
            DispatchQueue.main.async {
                isLoading = false
                switch result {
                case .success:
                    alertMessage = "Preferences saved successfully!"
                    showingAlert = true
                case .failure(let error):
                    alertMessage = "Failed to save preferences: \(error.localizedDescription)"
                    showingAlert = true
                }
            }
        }
    }
}

struct NotificationFiltersView: View {
    @EnvironmentObject private var notificationManager: NotificationManager
    @State private var showingAlert = false
    @State private var alertMessage = ""
    
    var body: some View {
        Form {
            Section("Notification Types") {
                ForEach(NotificationType.allCases, id: \.self) { type in
                    ToggleRow(
                        icon: type.emoji,
                        title: type.displayName,
                        subtitle: "Receive notifications for \(type.rawValue)",
                        isOn: Binding(
                            get: { notificationManager.userPreferences.notificationTypes[type.rawValue] ?? true },
                            set: { notificationManager.userPreferences.notificationTypes[type.rawValue] = $0 }
                        )
                    )
                }
            }
            
            Section("Impact Level Filtering") {
                ToggleRow(
                    icon: "exclamationmark.triangle.fill",
                    title: "High Impact Only",
                    subtitle: "Only show high and critical impact notifications",
                    isOn: Binding(
                        get: { notificationManager.userPreferences.notificationTypes["high_impact_only"] ?? false },
                        set: { notificationManager.userPreferences.notificationTypes["high_impact_only"] = $0 }
                    )
                )
            }
            
            Section {
                Button("Save Filters") {
                    saveFilters()
                }
                .frame(maxWidth: .infinity)
            }
        }
        .navigationTitle("Notification Filters")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Filters", isPresented: $showingAlert) {
            Button("OK") { }
        } message: {
            Text(alertMessage)
        }
    }
    
    private func saveFilters() {
        // Save to UserDefaults
        if let data = try? JSONEncoder().encode(notificationManager.userPreferences) {
            UserDefaults.standard.set(data, forKey: "userPreferences")
            alertMessage = "Filters saved successfully!"
            showingAlert = true
        } else {
            alertMessage = "Failed to save filters"
            showingAlert = true
        }
    }
}

struct QuietHoursView: View {
    @EnvironmentObject private var notificationManager: NotificationManager
    @State private var showingAlert = false
    @State private var alertMessage = ""
    
    var body: some View {
        Form {
            Section("Quiet Hours Settings") {
                ToggleRow(
                    icon: "moon.fill",
                    title: "Enable Quiet Hours",
                    subtitle: "Disable notifications during specified hours",
                    isOn: $notificationManager.userPreferences.quietHoursEnabled
                )
            }
            
            if notificationManager.userPreferences.quietHoursEnabled {
                Section("Time Settings") {
                    DatePicker(
                        "Start Time",
                        selection: $notificationManager.userPreferences.quietHoursStart,
                        displayedComponents: .hourAndMinute
                    )
                    
                    DatePicker(
                        "End Time",
                        selection: $notificationManager.userPreferences.quietHoursEnd,
                        displayedComponents: .hourAndMinute
                    )
                }
                
                Section("Preview") {
                    HStack {
                        Text("Quiet Period")
                        Spacer()
                        Text("\(formatTime(notificationManager.userPreferences.quietHoursStart)) - \(formatTime(notificationManager.userPreferences.quietHoursEnd))")
                            .foregroundColor(.secondary)
                    }
                }
            }
            
            Section {
                Button("Save Settings") {
                    saveQuietHours()
                }
                .frame(maxWidth: .infinity)
            }
        }
        .navigationTitle("Quiet Hours")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Quiet Hours", isPresented: $showingAlert) {
            Button("OK") { }
        } message: {
            Text(alertMessage)
        }
    }
    
    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
    
    private func saveQuietHours() {
        // Save to UserDefaults
        if let data = try? JSONEncoder().encode(notificationManager.userPreferences) {
            UserDefaults.standard.set(data, forKey: "userPreferences")
            alertMessage = "Quiet hours saved successfully!"
            showingAlert = true
        } else {
            alertMessage = "Failed to save quiet hours"
            showingAlert = true
        }
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
