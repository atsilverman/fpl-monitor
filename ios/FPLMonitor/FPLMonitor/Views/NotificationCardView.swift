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
            // Left side: Player details (with small badge inline)
            VStack(alignment: .leading, spacing: 6) {
                playerInfoView
                badgesView
            }
            .padding(.leading, 11)
            
            Spacer()
            
            // Right side: Points and score category
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
                
                // Score category below points
                Text(notification.pointsCategory)
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(.black)
                
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
            color: Color.black.opacity(0.05), 
            radius: 2, 
            x: 0, 
            y: 1
        )
        .overlay(
            // Color tab on the left edge
            HStack {
                        Rectangle()
                            .fill(notification.pointsChange > 0 ? 
                                  Color.green.opacity(0.2) : 
                                  notification.pointsChange < 0 ? 
                                  Color.red.opacity(0.2) : 
                                  Color.gray)
                    .frame(width: 11)
                
                Spacer()
            }
            .clipShape(RoundedRectangle(cornerRadius: 16))
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
            
            // Small team badge after player name
            TeamBadgeView(
                teamName: notification.team, 
                isOwned: notification.isOwned, 
                size: 18, 
                teamAbbreviation: notification.teamAbbreviation
            )
            
            if notification.isOwned {
                OwnedBadge()
            }
        }
    }
    
    private var badgesView: some View {
        HStack(spacing: 6) {
            TSBadge(
                percentage: notification.overallOwnership,
                isOwned: notification.isOwned
            )
            
            Text("|")
                .font(.caption2)
                .foregroundColor(.gray)
            
            Text("\(notification.totalPoints) pts")
                .font(.caption2)
                .foregroundColor(.gray)
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
    }
}


struct OwnedBadge: View {
    var body: some View {
        Image(systemName: "star.square.fill")
            .font(.system(size: 19))
            .foregroundStyle(.yellow)
    }
}


#Preview {
    VStack(spacing: 16) {
        // Owned player - Goal (Forest Green) - Real data: Erling Haaland
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
            totalPoints: 24,
            overallOwnership: 32.2,
            isOwned: true,
            timestamp: Date(),
            homeTeam: "Manchester City",
            awayTeam: "Arsenal",
            fixture: "MCI vs ARS",
            impact: .high
        ))
        
        // Non-owned player - Assist (Ocean Blue) - Real data: João Pedro
        NotificationCardView(notification: FPLNotification(
            title: "🎯 Assist!",
            body: "João Pedro provided an assist",
            type: .assists,
            player: "João Pedro",
            team: "Chelsea",
            teamAbbreviation: "CHE",
            points: 3,
            pointsChange: +3,
            pointsCategory: "Assist",
            totalPoints: 26,
            overallOwnership: 63.8,
            isOwned: false,
            timestamp: Calendar.current.date(byAdding: .hour, value: -2, to: Date()) ?? Date(),
            homeTeam: "Chelsea",
            awayTeam: "Arsenal",
            fixture: "CHE vs ARS",
            impact: .medium
        ))
        
        // Owned player - Clean Sheet (Purple) - Real data: Riccardo Calafiori
        NotificationCardView(notification: FPLNotification(
            title: "🛡️ Clean Sheet!",
            body: "Riccardo Calafiori kept a clean sheet",
            type: .cleanSheets,
            player: "Riccardo Calafiori",
            team: "Arsenal",
            teamAbbreviation: "ARS",
            points: 4,
            pointsChange: +4,
            pointsCategory: "Clean Sheet",
            totalPoints: 28,
            overallOwnership: 11.3,
            isOwned: true,
            timestamp: Calendar.current.date(byAdding: .day, value: -1, to: Date()) ?? Date(),
            homeTeam: "Arsenal",
            awayTeam: "Chelsea",
            fixture: "ARS vs CHE",
            impact: .medium
        ))
        
        // Non-owned player - Red Card (Red) - Real data: Trevoh Chalobah
        NotificationCardView(notification: FPLNotification(
            title: "🔴 Red Card",
            body: "Trevoh Chalobah received a red card",
            type: .redCards,
            player: "Trevoh Chalobah",
            team: "Chelsea",
            teamAbbreviation: "CHE",
            points: -3,
            pointsChange: -3,
            pointsCategory: "Red Card",
            totalPoints: 27,
            overallOwnership: 6.5,
            isOwned: false,
            timestamp: Calendar.current.date(byAdding: .day, value: -2, to: Date()) ?? Date(),
            homeTeam: "Chelsea",
            awayTeam: "Arsenal",
            fixture: "CHE vs ARS",
            impact: .high
        ))
    }
    .padding()
    .background(Color(.systemGroupedBackground))
}
