//
//  FPLMonitorApp.swift
//  FPLMonitor
//
//  Fantasy Premier League Monitor - Real-time notifications and analytics
//

import SwiftUI

@main
struct FPLMonitorApp: App {
    @StateObject private var notificationManager = NotificationManager()
    @StateObject private var apiManager = APIManager()
    @StateObject private var analyticsManager = AnalyticsManager()
    @StateObject private var userManager = UserManager.shared
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(notificationManager)
                .environmentObject(apiManager)
                .environmentObject(analyticsManager)
                .environmentObject(userManager)
                .onAppear {
                    notificationManager.requestNotificationPermission()
                }
        }
    }
}

// MARK: - App Delegate Methods
extension FPLMonitorApp {
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        notificationManager.handlePushToken(deviceToken)
    }
    
    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        print("Failed to register for remote notifications: \(error.localizedDescription)")
    }
    
    func application(_ application: UIApplication, didReceiveRemoteNotification userInfo: [AnyHashable: Any]) {
        // Handle notification received while app is in foreground
        notificationManager.handleNotificationReceived(userInfo)
    }
    
    func application(_ application: UIApplication, didReceiveRemoteNotification userInfo: [AnyHashable: Any], fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void) {
        // Handle notification received while app is in background
        notificationManager.handleNotificationReceived(userInfo)
        completionHandler(.newData)
    }
}
