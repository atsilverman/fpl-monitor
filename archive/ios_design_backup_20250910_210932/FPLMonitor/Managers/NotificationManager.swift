//
//  NotificationManager.swift
//  FPLMonitor
//
//  Manages push notifications and user preferences
//

import Foundation
import UserNotifications
import Combine
import UIKit

class NotificationManager: NSObject, ObservableObject {
    @Published var notifications: [FPLNotification] = []
    @Published var userPreferences = UserPreferences()
    @Published var isNotificationPermissionGranted = false
    
    private let apiManager = APIManager()
    private var cancellables = Set<AnyCancellable>()
    
    override init() {
        super.init()
        UNUserNotificationCenter.current().delegate = self
        loadUserPreferences()
        loadSampleNotifications()
    }
    
    // MARK: - Notification Permission
    func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { [weak self] granted, error in
            DispatchQueue.main.async {
                self?.isNotificationPermissionGranted = granted
                if granted {
                    self?.registerForRemoteNotifications()
                }
            }
        }
    }
    
    private func registerForRemoteNotifications() {
        DispatchQueue.main.async {
            UIApplication.shared.registerForRemoteNotifications()
        }
    }
    
    // MARK: - Push Token Handling
    func handlePushToken(_ deviceToken: Data) {
        let tokenString = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        print("Device token: \(tokenString)")
        sendDeviceTokenToBackend(tokenString)
    }
    
    private func sendDeviceTokenToBackend(_ token: String) {
        // Send device token to backend for push notifications
        apiManager.registerDeviceToken(token) { result in
            switch result {
            case .success:
                print("Device token registered successfully")
            case .failure(let error):
                print("Failed to register device token: \(error)")
            }
        }
    }
    
    // MARK: - User Preferences
    func loadUserPreferences() {
        // Load from UserDefaults or API
        userPreferences = UserPreferences()
    }
    
    func saveUserPreferences() {
        // Save to UserDefaults or API
        print("Saving user preferences")
    }
    
    // MARK: - Notification Handling
    func handleNotificationReceived(_ userInfo: [AnyHashable: Any]) {
        // Handle notification received while app is running
        print("Notification received: \(userInfo)")
        refreshNotifications()
    }
    
    func refreshNotifications() {
        // Refresh notifications from backend
        apiManager.fetchNotifications { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success(let notifications):
                    self?.notifications = notifications
                case .failure(let error):
                    print("Error fetching notifications: \(error)")
                }
            }
        }
    }
    
    // MARK: - Sample Data
    private func loadSampleNotifications() {
        let now = Date()
        let calendar = Calendar.current
        
        notifications = [
            FPLNotification(
                title: "⚽ Goal!",
                body: "Erling Haaland scored for Manchester City",
                type: .goals,
                player: "Erling Haaland",
                team: "Manchester City",
                teamAbbreviation: "MCI",
                points: 4,
                pointsChange: +4,
                pointsCategory: "Goal",
                totalPoints: 156,
                overallOwnership: 38.7,
                isOwned: true,
                timestamp: calendar.date(byAdding: .minute, value: -5, to: now) ?? now,
                homeTeam: "Manchester City",
                awayTeam: "Arsenal",
                fixture: "MCI vs ARS",
                impact: .high
            ),
            FPLNotification(
                title: "🎯 Assist!",
                body: "Kevin De Bruyne provided an assist",
                type: .assists,
                player: "Kevin De Bruyne",
                team: "Manchester City",
                teamAbbreviation: "MCI",
                points: 3,
                pointsChange: +3,
                pointsCategory: "Assist",
                totalPoints: 142,
                overallOwnership: 52.3,
                isOwned: true,
                timestamp: calendar.date(byAdding: .hour, value: -2, to: now) ?? now,
                homeTeam: "Manchester City",
                awayTeam: "Arsenal",
                fixture: "MCI vs ARS",
                impact: .medium
            ),
            FPLNotification(
                title: "🛡️ Clean Sheet!",
                body: "Alisson kept a clean sheet",
                type: .cleanSheets,
                player: "Alisson",
                team: "Liverpool",
                teamAbbreviation: "LIV",
                points: 4,
                pointsChange: +4,
                pointsCategory: "Clean Sheet",
                totalPoints: 98,
                overallOwnership: 18.4,
                isOwned: false,
                timestamp: calendar.date(byAdding: .day, value: -1, to: now) ?? now,
                homeTeam: "Liverpool",
                awayTeam: "Chelsea",
                fixture: "LIV vs CHE",
                impact: .medium
            ),
            FPLNotification(
                title: "🟡 Yellow Card",
                body: "John Stones received a yellow card",
                type: .yellowCards,
                player: "John Stones",
                team: "Manchester City",
                teamAbbreviation: "MCI",
                points: -1,
                pointsChange: -1,
                pointsCategory: "Yellow Card",
                totalPoints: 89,
                overallOwnership: 8.9,
                isOwned: true,
                timestamp: calendar.date(byAdding: .day, value: -2, to: now) ?? now,
                homeTeam: "Manchester City",
                awayTeam: "Arsenal",
                fixture: "MCI vs ARS",
                impact: .low
            ),
            FPLNotification(
                title: "⭐ Bonus Points",
                body: "Mohamed Salah earned bonus points",
                type: .bonus,
                player: "Mohamed Salah",
                team: "Liverpool",
                teamAbbreviation: "LIV",
                points: 2,
                pointsChange: +2,
                pointsCategory: "Bonus",
                totalPoints: 134,
                overallOwnership: 65.2,
                isOwned: false,
                timestamp: calendar.date(byAdding: .day, value: -3, to: now) ?? now,
                homeTeam: "Liverpool",
                awayTeam: "Chelsea",
                fixture: "LIV vs CHE",
                impact: .medium
            ),
            FPLNotification(
                title: "💪 Save!",
                body: "Ederson made a crucial save",
                type: .saves,
                player: "Ederson",
                team: "Manchester City",
                teamAbbreviation: "MCI",
                points: 1,
                pointsChange: +1,
                pointsCategory: "Save",
                totalPoints: 45,
                overallOwnership: 12.8,
                isOwned: false,
                timestamp: calendar.date(byAdding: .day, value: -4, to: now) ?? now,
                homeTeam: "Manchester City",
                awayTeam: "Arsenal",
                fixture: "MCI vs ARS",
                impact: .low
            ),
            FPLNotification(
                title: "🔴 Red Card",
                body: "Player received a red card",
                type: .redCards,
                player: "João Cancelo",
                team: "Barcelona",
                teamAbbreviation: "BAR",
                points: -3,
                pointsChange: -3,
                pointsCategory: "Red Card",
                totalPoints: 67,
                overallOwnership: 5.7,
                isOwned: false,
                timestamp: calendar.date(byAdding: .day, value: -5, to: now) ?? now,
                homeTeam: "Barcelona",
                awayTeam: "Real Madrid",
                fixture: "BAR vs RMA",
                impact: .high
            ),
            FPLNotification(
                title: "🥅 Penalty Saved",
                body: "Goalkeeper saved a penalty",
                type: .penaltySaved,
                player: "Alisson",
                team: "Liverpool",
                teamAbbreviation: "LIV",
                points: 5,
                pointsChange: +5,
                pointsCategory: "Penalty Saved",
                totalPoints: 112,
                overallOwnership: 14.2,
                isOwned: true,
                timestamp: calendar.date(byAdding: .day, value: -6, to: now) ?? now,
                homeTeam: "Liverpool",
                awayTeam: "Chelsea",
                fixture: "LIV vs CHE",
                impact: .high
            )
        ]
    }
}

// MARK: - User Preferences
struct UserPreferences: Codable {
    var notificationTypes: [String: Bool] = [:]
    var pushEnabled: Bool = true
    var emailEnabled: Bool = false
    var frequency: String = "immediate"
    var quietHoursEnabled: Bool = false
    var quietHoursStart: Date = Calendar.current.date(from: DateComponents(hour: 22, minute: 0)) ?? Date()
    var quietHoursEnd: Date = Calendar.current.date(from: DateComponents(hour: 8, minute: 0)) ?? Date()
    var fplManagerId: Int?
    var miniLeagueIds: String = ""
    var timezone: String = TimeZone.current.identifier
    
    init() {
        // Initialize with all notification types enabled
        for type in NotificationType.allCases {
            notificationTypes[type.rawValue] = true
        }
    }
}

// MARK: - UNUserNotificationCenterDelegate
extension NotificationManager: UNUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner, .sound, .badge])
    }
    
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
        // Handle notification tap
        print("Notification tapped: \(response.notification.request.content.userInfo)")
        completionHandler()
    }
}
