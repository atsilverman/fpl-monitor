//
//  NotificationCardView.swift
//  FPLMonitor
//
//  Individual notification card component
//

import SwiftUI

struct NotificationCardView: View {
    let notification: FPLNotification
    @State private var isPressed = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header with teams and time
            HStack {
                TeamBadgeView(team: notification.homeTeam)
                Text("vs")
                    .font(.caption)
                    .foregroundColor(.fplSubtext)
                TeamBadgeView(team: notification.awayTeam)
                Spacer()
                TimeAgoView(timestamp: notification.timestamp)
            }
            
            // Notification content
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(notification.type.emoji)
                        .font(.title2)
                    Text(notification.title)
                        .font(.fplHeadline)
                        .foregroundColor(.fplText)
                    Spacer()
                    PointsView(points: notification.points)
                }
                
                Text(notification.body)
                    .font(.fplBody)
                    .foregroundColor(.fplSubtext)
                
                // Player and team info
                HStack {
                    Text(notification.player)
                        .font(.fplBody.weight(.medium))
                        .foregroundColor(.fplText)
                    Text("•")
                        .foregroundColor(.fplSubtext)
                    Text(notification.team)
                        .font(.fplBody)
                        .foregroundColor(.fplSubtext)
                    Spacer()
                    ImpactIndicator(impact: notification.impact)
                }
            }
        }
        .padding()
        .background(Color.fplCard)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .scaleEffect(isPressed ? 0.98 : 1.0)
        .animation(.easeInOut(duration: 0.1), value: isPressed)
        .onTapGesture {
            withAnimation(.easeInOut(duration: 0.1)) {
                isPressed = true
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                withAnimation(.easeInOut(duration: 0.1)) {
                    isPressed = false
                }
            }
        }
    }
}

struct TeamBadgeView: View {
    let team: String
    
    var body: some View {
        Circle()
            .fill(Color.fplBackground)
            .frame(width: 32, height: 32)
            .overlay(
                Text(String(team.prefix(1)))
                    .font(.caption.weight(.bold))
                    .foregroundColor(.fplText)
            )
    }
}

struct TimeAgoView: View {
    let timestamp: Date
    
    var body: some View {
        Text(timeAgoString)
            .font(.caption)
            .foregroundColor(.fplSubtext)
    }
    
    private var timeAgoString: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: timestamp, relativeTo: Date())
    }
}

struct PointsView: View {
    let points: Int
    
    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: "star.fill")
                .foregroundColor(.fplAccent)
            Text("\(points)")
                .font(.fplBody.weight(.semibold))
                .foregroundColor(.fplText)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color.fplAccent.opacity(0.1))
        .cornerRadius(8)
    }
}

struct ImpactIndicator: View {
    let impact: NotificationImpact
    
    var body: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(impact.color)
                .frame(width: 8, height: 8)
            Text(impact.displayName)
                .font(.caption)
                .foregroundColor(.fplSubtext)
        }
    }
}

#Preview {
    VStack(spacing: 16) {
        NotificationCardView(notification: FPLNotification(
            title: "⚽ Goal!",
            body: "Erling Haaland scored for Manchester City",
            type: .goals,
            player: "Erling Haaland",
            team: "Manchester City",
            points: 4,
            homeTeam: "Manchester City",
            awayTeam: "Arsenal",
            fixture: "MCI vs ARS",
            impact: .high
        ))
        
        NotificationCardView(notification: FPLNotification(
            title: "🎯 Assist!",
            body: "Kevin De Bruyne provided an assist",
            type: .assists,
            player: "Kevin De Bruyne",
            team: "Manchester City",
            points: 3,
            homeTeam: "Manchester City",
            awayTeam: "Arsenal",
            fixture: "MCI vs ARS",
            impact: .medium
        ))
    }
    .padding()
    .background(Color.fplBackground)
}
