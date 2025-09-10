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
    let points: Int
    let timestamp: Date
    let isRead: Bool
    let homeTeam: String
    let awayTeam: String
    let fixture: String
    let impact: NotificationImpact
    
    init(id: String = UUID().uuidString, title: String, body: String, type: NotificationType, player: String, team: String, points: Int, timestamp: Date = Date(), isRead: Bool = false, homeTeam: String, awayTeam: String, fixture: String, impact: NotificationImpact = .medium) {
        self.id = id
        self.title = title
        self.body = body
        self.type = type
        self.player = player
        self.team = team
        self.points = points
        self.timestamp = timestamp
        self.isRead = isRead
        self.homeTeam = homeTeam
        self.awayTeam = awayTeam
        self.fixture = fixture
        self.impact = impact
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
        case .defensiveContribution: return "🛡️ Defensive Contribution"
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
