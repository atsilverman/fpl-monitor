//
//  FPLNotification.swift
//  FPLMonitor
//
//  Data model for FPL notifications
//

import Foundation
import SwiftUI

struct FPLNotification: Identifiable, Codable {
    let id: String
    let title: String
    let body: String
    let type: NotificationType
    let player: String
    let team: String
    let teamAbbreviation: String
    let points: Int
    let pointsChange: Int
    let pointsCategory: String
    let totalPoints: Int
    let gameweekPoints: Int
    let gameweek: Int
    let overallOwnership: Double
    let isOwned: Bool
    let timestamp: Date
    let isRead: Bool
    let homeTeam: String
    let awayTeam: String
    let fixture: String
    let impact: NotificationImpact
    let playerPrice: Double?
    let priceChange: Double?
    let playerStatus: String?
    let oldStatus: String?
    let newsText: String?
    let oldNews: String?
    
    init(id: String = UUID().uuidString, title: String, body: String, type: NotificationType, player: String, team: String, teamAbbreviation: String, points: Int, pointsChange: Int, pointsCategory: String, totalPoints: Int, gameweekPoints: Int, gameweek: Int, overallOwnership: Double = 0.0, isOwned: Bool = false, timestamp: Date = Date(), isRead: Bool = false, homeTeam: String, awayTeam: String, fixture: String, impact: NotificationImpact = .medium, playerPrice: Double? = nil, priceChange: Double? = nil, playerStatus: String? = nil, oldStatus: String? = nil, newsText: String? = nil, oldNews: String? = nil) {
        self.id = id
        self.title = title
        self.body = body
        self.type = type
        self.player = player
        self.team = team
        self.teamAbbreviation = teamAbbreviation
        self.points = points
        self.pointsChange = pointsChange
        self.pointsCategory = pointsCategory
        self.totalPoints = totalPoints
        self.gameweekPoints = gameweekPoints
        self.gameweek = gameweek
        self.overallOwnership = overallOwnership
        self.isOwned = isOwned
        self.timestamp = timestamp
        self.isRead = isRead
        self.homeTeam = homeTeam
        self.awayTeam = awayTeam
        self.fixture = fixture
        self.impact = impact
        self.playerPrice = playerPrice
        self.priceChange = priceChange
        self.playerStatus = playerStatus
        self.oldStatus = oldStatus
        self.newsText = newsText
        self.oldNews = oldNews
    }
}

enum NotificationType: String, CaseIterable, Codable {
    case goals = "goals"
    case assists = "assists"
    case cleanSheets = "clean_sheets"
    case bonus = "bonus"
    case redCards = "red_cards"
    case yellowCards = "yellow_cards"
    case penaltySaved = "penalty_saved"
    case penaltyMissed = "penalty_missed"
    case ownGoals = "own_goals"
    case saves = "saves"
    case goalsConceded = "goals_conceded"
    case defensiveContribution = "defensive_contribution"
    case priceChanges = "price_changes"
    case statusChanges = "status_changes"
    
    var displayName: String {
        switch self {
        case .goals: return "⚽ Goals"
        case .assists: return "🎯 Assists"
        case .cleanSheets: return "🛡️ Clean Sheets"
        case .bonus: return "⭐ Bonus Points"
        case .redCards: return "🔴 Red Cards"
        case .yellowCards: return "🟡 Yellow Cards"
        case .penaltySaved: return "🥅 Penalties Saved"
        case .penaltyMissed: return "❌ Penalties Missed"
        case .ownGoals: return "😱 Own Goals"
        case .saves: return "💪 Saves"
        case .goalsConceded: return "😞 Goals Conceded"
        case .defensiveContribution: return "🛡️ DEFCON"
        case .priceChanges: return "💰 Price Changes"
        case .statusChanges: return "📊 Status Changes"
        }
    }
    
    var emoji: String {
        switch self {
        case .goals: return "⚽"
        case .assists: return "🎯"
        case .cleanSheets: return "🛡️"
        case .bonus: return "⭐"
        case .redCards: return "🔴"
        case .yellowCards: return "🟡"
        case .penaltySaved: return "🥅"
        case .penaltyMissed: return "❌"
        case .ownGoals: return "😱"
        case .saves: return "💪"
        case .goalsConceded: return "😞"
        case .defensiveContribution: return "🛡️"
        case .priceChanges: return "💰"
        case .statusChanges: return "📊"
        }
    }
    
    var accentColor: Color {
        switch self {
        case .goals: return Color(red: 0.2, green: 0.7, blue: 0.3) // Forest Green
        case .assists: return Color(red: 0.0, green: 0.5, blue: 0.8) // Ocean Blue
        case .cleanSheets: return Color(red: 0.6, green: 0.2, blue: 0.8) // Purple
        case .bonus: return Color(red: 1.0, green: 0.5, blue: 0.0) // Orange
        case .redCards: return Color(red: 0.8, green: 0.2, blue: 0.2) // Red
        case .yellowCards: return Color(red: 0.9, green: 0.7, blue: 0.0) // Gold
        case .penaltySaved: return Color(red: 0.0, green: 0.7, blue: 0.7) // Teal
        case .penaltyMissed: return Color(red: 0.9, green: 0.3, blue: 0.3) // Coral Red
        case .ownGoals: return Color(red: 0.7, green: 0.2, blue: 0.2) // Dark Red
        case .saves: return Color(red: 0.0, green: 0.6, blue: 0.9) // Sky Blue
        case .goalsConceded: return Color(red: 0.8, green: 0.4, blue: 0.4) // Light Red
        case .defensiveContribution: return Color(red: 0.4, green: 0.2, blue: 0.8) // Indigo
        case .priceChanges: return Color(red: 0.0, green: 0.6, blue: 0.4) // Emerald
        case .statusChanges: return Color(red: 0.5, green: 0.5, blue: 0.5) // Medium Gray
        }
    }
}

enum NotificationImpact: String, CaseIterable, Codable {
    case low = "low"
    case medium = "medium"
    case high = "high"
    case critical = "critical"
    
    var color: Color {
        switch self {
        case .low: return .green
        case .medium: return .blue
        case .high: return .orange
        case .critical: return .red
        }
    }
    
    var displayName: String {
        switch self {
        case .low: return "Low Impact"
        case .medium: return "Medium Impact"
        case .high: return "High Impact"
        case .critical: return "Critical Impact"
        }
    }
}

// MARK: - Status Helper Functions

extension FPLNotification {
    /// Convert FPL status code to display text
    static func statusDisplayText(for status: String?) -> String {
        guard let status = status else { return "Unknown" }
        
        switch status.lowercased() {
        case "a": return "Available"
        case "d": return "Doubtful"
        case "i": return "Injured"
        case "s": return "Suspended"
        case "u": return "Unavailable"
        case "n": return "Not Eligible"
        default: return "Unknown"
        }
    }
    
    /// Get status color for display
    static func statusColor(for status: String?) -> Color {
        guard let status = status else { return .gray }
        
        switch status.lowercased() {
        case "a": return .green // Match price rise green
        case "d": return Color(red: 0.831, green: 0.506, blue: 0.008) // #D4C302
        case "i": return .red // Match price fall red
        case "s": return .red // Match price fall red
        case "u": return .red // Match price fall red
        case "n": return .gray
        default: return .gray
        }
    }
    
    /// Get status SF Symbol for display
    static func statusIcon(for status: String?) -> String {
        guard let status = status else { return "questionmark.circle.fill" }
        
        switch status.lowercased() {
        case "a": return "exclamationmark.triangle.fill"
        case "d": return "exclamationmark.triangle.fill"
        case "i": return "exclamationmark.triangle.fill"
        case "s": return "exclamationmark.triangle.fill"
        case "u": return "x.circle.fill"
        case "n": return "x.circle.fill"
        default: return "questionmark.circle.fill"
        }
    }
}
