//
//  AnalyticsManager.swift
//  FPLMonitor
//
//  Manages analytics data collection and retrieval
//

import Foundation
import Combine

class AnalyticsManager: ObservableObject {
    @Published var analyticsData = AnalyticsData(
        engagementScore: 0.0,
        notificationStats: AnalyticsNotificationStats(received: 0, tapped: 0, dismissed: 0, tapRate: 0.0),
        activityData: [],
        notificationTypesData: [],
        mostActiveHours: []
    )
    @Published var isLoading = false
    
    private let apiManager = APIManager()
    private var cancellables = Set<AnyCancellable>()
    
    // MARK: - Track Events
    func trackEvent(_ eventType: AnalyticsEventType, properties: [String: String] = [:]) {
        let event = AnalyticsEvent(
            eventId: UUID().uuidString,
            userId: "user_123", // This would come from user authentication
            eventType: eventType,
            timestamp: Date(),
            properties: properties,
            sessionId: "session_123", // This would be managed per session
            appVersion: "1.0.0",
            platform: "ios"
        )
        
        apiManager.trackEvent(event) { result in
            switch result {
            case .success:
                print("Event tracked: \(eventType.rawValue)")
            case .failure(let error):
                print("Failed to track event: \(error)")
            }
        }
    }
    
    // MARK: - Fetch Analytics Data
    func fetchAnalyticsData(timeRange: AnalyticsTimeRange = .week) {
        isLoading = true
        
        // Simulate API call - in real app this would call the backend
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.analyticsData = self.generateSampleData()
            self.isLoading = false
        }
    }
    
    private func generateSampleData() -> AnalyticsData {
        return AnalyticsData(
            engagementScore: 85.5,
            notificationStats: AnalyticsNotificationStats(
                received: 47,
                tapped: 32,
                dismissed: 15,
                tapRate: 0.68
            ),
            activityData: [
                AnalyticsActivityData(date: Date().addingTimeInterval(-86400 * 6), notifications: 8),
                AnalyticsActivityData(date: Date().addingTimeInterval(-86400 * 5), notifications: 12),
                AnalyticsActivityData(date: Date().addingTimeInterval(-86400 * 4), notifications: 6),
                AnalyticsActivityData(date: Date().addingTimeInterval(-86400 * 3), notifications: 15),
                AnalyticsActivityData(date: Date().addingTimeInterval(-86400 * 2), notifications: 9),
                AnalyticsActivityData(date: Date().addingTimeInterval(-86400 * 1), notifications: 11),
                AnalyticsActivityData(date: Date(), notifications: 7)
            ],
            notificationTypesData: [
                AnalyticsNotificationTypeData(type: "goals", count: 12, tapRate: 0.75),
                AnalyticsNotificationTypeData(type: "assists", count: 8, tapRate: 0.62),
                AnalyticsNotificationTypeData(type: "clean_sheets", count: 6, tapRate: 0.83),
                AnalyticsNotificationTypeData(type: "bonus", count: 15, tapRate: 0.47),
                AnalyticsNotificationTypeData(type: "red_cards", count: 2, tapRate: 1.0),
                AnalyticsNotificationTypeData(type: "yellow_cards", count: 4, tapRate: 0.5)
            ],
            mostActiveHours: [9, 10, 11, 14, 15, 16, 19, 20, 21]
        )
    }
}

// MARK: - Analytics Data Models
enum AnalyticsEventType: String, CaseIterable, Codable {
    case appOpen = "app_open"
    case notificationReceived = "notification_received"
    case notificationTapped = "notification_tapped"
    case notificationDismissed = "notification_dismissed"
    case playerSearch = "player_search"
    case settingsUpdated = "settings_updated"
    case pushEnabled = "push_enabled"
    case pushDisabled = "push_disabled"
    case errorOccurred = "error_occurred"
}

struct AnalyticsEvent: Codable {
    let eventId: String
    let userId: String
    let eventType: AnalyticsEventType
    let timestamp: Date
    let properties: [String: String]
    let sessionId: String
    let appVersion: String
    let platform: String
}

enum AnalyticsTimeRange: String, CaseIterable, Codable {
    case day = "day"
    case week = "week"
    case month = "month"
    case year = "year"
    
    var displayName: String {
        switch self {
        case .day: return "Last 24 Hours"
        case .week: return "Last 7 Days"
        case .month: return "Last 30 Days"
        case .year: return "Last Year"
        }
    }
}

struct AnalyticsData: Codable {
    let engagementScore: Double
    let notificationStats: AnalyticsNotificationStats
    let activityData: [AnalyticsActivityData]
    let notificationTypesData: [AnalyticsNotificationTypeData]
    let mostActiveHours: [Int]
}

struct AnalyticsNotificationStats: Codable {
    let received: Int
    let tapped: Int
    let dismissed: Int
    let tapRate: Double
}

struct AnalyticsActivityData: Codable, Identifiable {
    let id: UUID
    let date: Date
    let notifications: Int
    
    init(date: Date, notifications: Int) {
        self.id = UUID()
        self.date = date
        self.notifications = notifications
    }
}

struct AnalyticsNotificationTypeData: Codable {
    let type: String
    let count: Int
    let tapRate: Double
}
