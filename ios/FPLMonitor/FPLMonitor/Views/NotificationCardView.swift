//
//  NotificationCardView.swift
//  FPLMonitor
//
//  Individual notification card component - Modern compact design
//

import SwiftUI

struct NotificationCardView: View {
    let notification: FPLNotification
    @State private var isPressed = false
    
    var body: some View {
        HStack(spacing: 16) {
            // Left side: Player details only
            VStack(alignment: .leading, spacing: 6) {
                playerInfoView
                badgesView
            }
            
            Spacer()
            
            // Right side: Points and time
            VStack(alignment: .trailing, spacing: 6) {
                // Point change (primary) with enhanced contrast
                HStack(spacing: 6) {
                    ZStack {
                        Circle()
                            .fill(notification.pointsChange > 0 ? 
                                  Color.green.opacity(0.2) : 
                                  Color.red.opacity(0.2))
                            .frame(width: 24, height: 24)
                        
                        Image(systemName: notification.pointsChange > 0 ? "arrow.up.circle.fill" : "arrow.down.circle.fill")
                            .font(.caption)
                            .foregroundColor(notification.pointsChange > 0 ? .green : .red)
                    }
                    
                    Text("\(notification.pointsChange > 0 ? "+" : "")\(notification.pointsChange)")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(notification.pointsChange > 0 ? .green : notification.pointsChange < 0 ? .red : .primary)
                }
                
                // Total points (secondary)
                Text("\(notification.totalPoints) pts")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 16)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.fplCard)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(
                    notification.isRead ? Color.clear : Color.fplCardBorder, 
                    lineWidth: 1
                )
        )
        .shadow(
            color: Color.black.opacity(0.08), 
            radius: 4, 
            x: 0, 
            y: 2
        )
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
    
    // MARK: - Computed Views
    
    private var playerInfoView: some View {
        HStack(spacing: 6) {
            Text(notification.player)
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(.primary)
                .lineLimit(1)
            
            if notification.isOwned {
                OwnedBadge()
            }
        }
    }
    
    private var badgesView: some View {
        HStack(spacing: 6) {
            Text(notification.pointsCategory)
                .font(.caption)
                .foregroundColor(.white)
                .padding(.horizontal, 8)
                .padding(.vertical, 2)
                .background(notification.type.accentColor)
                .cornerRadius(6)
            
            TSBadge(
                percentage: notification.overallOwnership,
                isOwned: notification.isOwned
            )
        }
    }
}

struct TSBadge: View {
    let percentage: Double
    let isOwned: Bool
    
    var body: some View {
        HStack(spacing: 3) {
            if isOwned {
                Image(systemName: "person.2.fill")
                    .font(.caption2)
                    .foregroundColor(.gray)
            }
            
            Text("TSB")
                .font(.caption2.weight(.medium))
                .foregroundColor(.gray)
            
            Text("\(Int(percentage))%")
                .font(.caption2.weight(.bold))
                .foregroundColor(.gray)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(Color.gray.opacity(0.2))
        .cornerRadius(8)
    }
}


struct OwnedBadge: View {
    var body: some View {
        HStack(spacing: 2) {
            Image(systemName: "star.fill")
                .font(.caption2)
            Text("OWNED")
                .font(.caption2.weight(.bold))
        }
        .foregroundColor(.white)
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(Color.blue)
        .cornerRadius(6)
    }
}


#Preview {
    VStack(spacing: 16) {
        // Owned player - Goal (Forest Green)
        NotificationCardView(notification: FPLNotification(
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
            timestamp: Date(),
            homeTeam: "Manchester City",
            awayTeam: "Arsenal",
            fixture: "MCI vs ARS",
            impact: .high
        ))
        
        // Non-owned player - Assist (Ocean Blue)
        NotificationCardView(notification: FPLNotification(
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
            isOwned: false,
            timestamp: Calendar.current.date(byAdding: .hour, value: -2, to: Date()) ?? Date(),
            homeTeam: "Manchester City",
            awayTeam: "Arsenal",
            fixture: "MCI vs ARS",
            impact: .medium
        ))
        
        // Owned player - Clean Sheet (Purple)
        NotificationCardView(notification: FPLNotification(
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
            isOwned: true,
            timestamp: Calendar.current.date(byAdding: .day, value: -1, to: Date()) ?? Date(),
            homeTeam: "Liverpool",
            awayTeam: "Chelsea",
            fixture: "LIV vs CHE",
            impact: .medium
        ))
        
        // Non-owned player - Red Card (Red)
        NotificationCardView(notification: FPLNotification(
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
            timestamp: Calendar.current.date(byAdding: .day, value: -2, to: Date()) ?? Date(),
            homeTeam: "Barcelona",
            awayTeam: "Real Madrid",
            fixture: "BAR vs RMA",
            impact: .high
        ))
    }
    .padding()
    .background(Color(.systemGroupedBackground))
}
