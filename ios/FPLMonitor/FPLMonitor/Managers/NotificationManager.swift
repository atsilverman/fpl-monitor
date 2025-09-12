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
        // Use realistic Premier League data
        notifications = RealisticNotificationData.sampleNotifications
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
