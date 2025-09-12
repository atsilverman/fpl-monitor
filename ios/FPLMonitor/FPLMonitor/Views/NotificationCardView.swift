//
//  NotificationCardView.swift
//  FPLMonitor
//
//  Individual notification card component - Modern compact design
//

import SwiftUI

struct NotificationCardView: View {
    let notification: FPLNotification
    @Binding var isShowingTimestamps: Bool
    @Binding var dragOffset: CGFloat
    @State private var isPressed = false
    
    var body: some View {
        ZStack {
            // Main card content
            HStack(spacing: 8) {
                // Left side: Player details (with small badge inline) - pushed to left edge
                VStack(alignment: .leading, spacing: 6) {
                    playerInfoView
                    badgesView
                }
                .padding(.leading, 4)
                
                Spacer()
                
                // Right side: Points/Price and category - pushed to right edge
                VStack(alignment: .trailing, spacing: 2) {
                    if notification.type == .priceChanges {
                        // Price change display - just arrow and text
                        VStack(alignment: .trailing, spacing: 4) {
                            let priceChange = notification.priceChange ?? 0.0
                            
                            Image(systemName: priceChange > 0 ? "arrow.up.circle.fill" : "arrow.down.circle.fill")
                                .font(.system(size: 15))
                                .foregroundColor(priceChange > 0 ? .green : .red)
                                .shadow(color: .black.opacity(0.1), radius: 1, x: 0, y: 1)
                            
                            Text(priceChange > 0 ? "Price Rise" : "Price Fall")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(.fplText)
                        }
                    } else {
                        // Gameplay points display
                        HStack(alignment: .center, spacing: 6) {
                            Image(systemName: notification.pointsChange > 0 ? "arrow.up.circle.fill" : "arrow.down.circle.fill")
                                .font(.system(size: 15))
                                .foregroundColor(notification.pointsChange > 0 ? .green : .red)
                                .offset(y: 1)
                                .shadow(color: .black.opacity(0.1), radius: 1, x: 0, y: 1)
                            
                            Text("\(notification.pointsChange > 0 ? "+" : "")\(notification.pointsChange)")
                                .font(.system(size: 20, weight: .bold))
                                .foregroundColor(notification.pointsChange > 0 ? .green : notification.pointsChange < 0 ? .red : .fplText)
                                .shadow(color: .black.opacity(0.1), radius: 1, x: 0, y: 1)
                        }
                        
                        // Score category below points
                        Text(notification.pointsCategory)
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.fplText)
                    }
                }
                .padding(.trailing, 4)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12.8)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.fplCard)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.fplCardBorder, lineWidth: 1)
                    )
            )
            .shadow(
                color: Color.black.opacity(0.05), 
                radius: 2, 
                x: 0, 
                y: 1
            )
            .overlay(
                // Color tab on the right edge with gradient extending quarter way
                GeometryReader { geometry in
                    HStack {
                        Spacer()
                        
                        Rectangle()
                            .fill(
                                LinearGradient(
                                    gradient: Gradient(colors: [gradientStartColor, gradientEndColor]),
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: geometry.size.width * 0.20)
                    }
                }
                .clipShape(RoundedRectangle(cornerRadius: 16))
            )
            .offset(x: dragOffset)
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
            
            // Timestamp overlay - appears underneath when swiped
            if isShowingTimestamps {
                HStack {
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 2) {
                        Text(formatTimestamp(notification.timestamp))
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(.secondary)
                    }
                    .padding(.trailing, 4) // Align with main card's right edge
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(Color.fplCard.opacity(0.9))
                )
                .offset(x: dragOffset)
            }
        }
        .scaleEffect(isPressed ? 0.98 : 1.0)
        .animation(.easeInOut(duration: 0.1), value: isPressed)
    }
    
    // MARK: - Helper Functions
    
    private func formatTimestamp(_ timestamp: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: timestamp)
    }
    
    private var gradientStartColor: Color {
        let changeValue = getChangeValue()
        if changeValue > 0 {
            return Color.green.opacity(0.0)
        } else if changeValue < 0 {
            return Color.red.opacity(0.0)
        } else {
            return Color.gray.opacity(0.0)
        }
    }
    
    private var gradientEndColor: Color {
        let changeValue = getChangeValue()
        if changeValue > 0 {
            return Color.green.opacity(0.15)
        } else if changeValue < 0 {
            return Color.red.opacity(0.15)
        } else {
            return Color.gray.opacity(0.15)
        }
    }
    
    private func getChangeValue() -> Double {
        if notification.type == .priceChanges {
            return notification.priceChange ?? 0.0
        } else {
            return Double(notification.pointsChange)
        }
    }
    
    // MARK: - Computed Views
    
    private var playerInfoView: some View {
        HStack(spacing: 6) {
            Text(notification.player)
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(.fplText)
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
            if notification.type == .priceChanges {
                // Price information for price change notifications
                if let playerPrice = notification.playerPrice, playerPrice > 0 {
                    Text("£\(String(format: "%.1f", playerPrice))")
                        .font(.caption2)
                        .fontWeight(.bold)
                        .foregroundColor(.fplText)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.gray.opacity(0.1))
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                }
                
                Text("|")
                    .font(.caption2)
                    .foregroundColor(.gray)
                
                // TSB - now without background
                HStack(spacing: 3) {
                    Image(systemName: "person.2.fill")
                        .font(.caption2)
                        .foregroundColor(.gray)
                    
                    Text("\(Int(notification.overallOwnership))%")
                        .font(.caption2)
                        .foregroundColor(.gray)
                }
            } else {
                // Gameplay points information
                Text("\(notification.gameweekPoints) pts")
                    .font(.caption2)
                    .fontWeight(.bold)
                    .foregroundColor(.fplText)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.gray.opacity(0.1))
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                
                Text("|")
                    .font(.caption2)
                    .foregroundColor(.gray)
                
                // TSB - now without background
                HStack(spacing: 3) {
                    Image(systemName: "person.2.fill")
                        .font(.caption2)
                        .foregroundColor(.gray)
                    
                    Text("\(Int(notification.overallOwnership))%")
                        .font(.caption2)
                        .foregroundColor(.gray)
                }
            }
        }
    }
}

struct TSBadge: View {
    let percentage: Double
    
    var body: some View {
        HStack(spacing: 3) {
            // Person icon and percentage - show ownership percentage
            Image(systemName: "person.2.fill")
                .font(.caption2)
                .foregroundColor(.fplText)
            
            Text("\(Int(percentage))%")
                .font(.caption2.weight(.bold))
                .foregroundColor(.fplText)
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(Color.gray.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 4))
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
        // Show first 4 realistic notifications
        ForEach(Array(RealisticNotificationData.sampleNotifications.prefix(4))) { notification in
            NotificationCardView(
                notification: notification,
                isShowingTimestamps: .constant(false),
                dragOffset: .constant(0)
            )
        }
    }
    .padding()
    .background(Color(.systemGroupedBackground))
}
