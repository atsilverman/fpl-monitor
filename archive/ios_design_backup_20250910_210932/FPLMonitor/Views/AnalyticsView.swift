//
//  AnalyticsView.swift
//  FPLMonitor
//
//  Analytics dashboard view
//

import SwiftUI
import Charts

struct AnalyticsView: View {
    @EnvironmentObject private var analyticsManager: AnalyticsManager
    @State private var selectedTimeRange: AnalyticsTimeRange = .week
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Time Range Selector
                    Picker("Time Range", selection: $selectedTimeRange) {
                        ForEach(AnalyticsTimeRange.allCases, id: \.self) { range in
                            Text(range.displayName).tag(range)
                        }
                    }
                    .pickerStyle(SegmentedPickerStyle())
                    .padding(.horizontal)
                    
                    if analyticsManager.isLoading {
                        LoadingView()
                    } else {
                        // Engagement Score
                        EngagementScoreCard(score: analyticsManager.analyticsData.engagementScore)
                        
                        // Notification Stats
                        NotificationStatsCard(stats: analyticsManager.analyticsData.notificationStats)
                        
                        // Activity Chart
                        ActivityChartCard(data: analyticsManager.analyticsData.activityData)
                        
                        // Notification Types
                        NotificationTypesCard(data: analyticsManager.analyticsData.notificationTypesData)
                        
                        // Most Active Hours
                        MostActiveHoursCard(hours: analyticsManager.analyticsData.mostActiveHours)
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("Analytics")
            .navigationBarTitleDisplayMode(.large)
            .onAppear {
                analyticsManager.fetchAnalyticsData(timeRange: selectedTimeRange)
            }
            .onChange(of: selectedTimeRange) { _, newValue in
                analyticsManager.fetchAnalyticsData(timeRange: newValue)
            }
        }
    }
}

struct EngagementScoreCard: View {
    let score: Double
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Engagement Score")
                .font(.fplHeadline)
                .foregroundColor(.fplText)
            
            HStack {
                ZStack {
                    Circle()
                        .stroke(Color.fplBackground, lineWidth: 8)
                        .frame(width: 80, height: 80)
                    
                    Circle()
                        .trim(from: 0, to: score / 100)
                        .stroke(scoreColor, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                        .frame(width: 80, height: 80)
                        .rotationEffect(.degrees(-90))
                    
                    Text("\(Int(score))")
                        .font(.fplTitle)
                        .foregroundColor(.fplText)
                }
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(scoreDescription)
                        .font(.fplBody)
                        .foregroundColor(.fplSubtext)
                    
                    Text("Based on your notification interactions and app usage")
                        .font(.caption)
                        .foregroundColor(.fplSubtext)
                }
                
                Spacer()
            }
        }
        .padding()
        .background(Color.fplCard)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .padding(.horizontal)
    }
    
    private var scoreColor: Color {
        switch score {
        case 0..<30: return .red
        case 30..<60: return .orange
        case 60..<80: return .blue
        default: return .green
        }
    }
    
    private var scoreDescription: String {
        switch score {
        case 0..<30: return "Low Engagement"
        case 30..<60: return "Moderate Engagement"
        case 60..<80: return "Good Engagement"
        default: return "Excellent Engagement"
        }
    }
}

struct NotificationStatsCard: View {
    let stats: AnalyticsNotificationStats
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Notification Stats")
                .font(.fplHeadline)
                .foregroundColor(.fplText)
            
            HStack(spacing: 20) {
                StatItem(title: "Received", value: "\(stats.received)", color: .blue)
                StatItem(title: "Tapped", value: "\(stats.tapped)", color: .green)
                StatItem(title: "Dismissed", value: "\(stats.dismissed)", color: .orange)
                StatItem(title: "Tap Rate", value: "\(Int(stats.tapRate * 100))%", color: .fplPrimary)
            }
        }
        .padding()
        .background(Color.fplCard)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .padding(.horizontal)
    }
}

struct StatItem: View {
    let title: String
    let value: String
    let color: Color
    
    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.fplTitle)
                .foregroundColor(color)
            Text(title)
                .font(.caption)
                .foregroundColor(.fplSubtext)
        }
        .frame(maxWidth: .infinity)
    }
}

struct ActivityChartCard: View {
    let data: [AnalyticsActivityData]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Activity Over Time")
                .font(.fplHeadline)
                .foregroundColor(.fplText)
            
            Chart(data) { item in
                LineMark(
                    x: .value("Date", item.date),
                    y: .value("Notifications", item.notifications)
                )
                .foregroundStyle(Color.fplPrimary)
                .lineStyle(StrokeStyle(lineWidth: 3))
                
                AreaMark(
                    x: .value("Date", item.date),
                    y: .value("Notifications", item.notifications)
                )
                .foregroundStyle(Color.fplPrimary.opacity(0.3))
            }
            .frame(height: 200)
        }
        .padding()
        .background(Color.fplCard)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .padding(.horizontal)
    }
}

struct NotificationTypesCard: View {
    let data: [AnalyticsNotificationTypeData]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Notification Types")
                .font(.fplHeadline)
                .foregroundColor(.fplText)
            
            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 2), spacing: 12) {
                ForEach(data, id: \.type) { item in
                    NotificationTypeItem(data: item)
                }
            }
        }
        .padding()
        .background(Color.fplCard)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .padding(.horizontal)
    }
}

struct NotificationTypeItem: View {
    let data: AnalyticsNotificationTypeData
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(notificationEmoji)
                    .font(.title2)
                Spacer()
                Text("\(data.count)")
                    .font(.fplBody.weight(.semibold))
                    .foregroundColor(.fplText)
            }
            
            Text(notificationTypeName)
                .font(.caption)
                .foregroundColor(.fplSubtext)
            
            Text("\(Int(data.tapRate * 100))% tap rate")
                .font(.caption2)
                .foregroundColor(.fplSubtext)
        }
        .padding(8)
        .background(Color.fplBackground)
        .cornerRadius(8)
    }
    
    private var notificationEmoji: String {
        switch data.type {
        case "goals": return "⚽"
        case "assists": return "🎯"
        case "clean_sheets": return "🛡️"
        case "bonus": return "⭐"
        case "red_cards": return "🔴"
        case "yellow_cards": return "🟡"
        default: return "📊"
        }
    }
    
    private var notificationTypeName: String {
        switch data.type {
        case "goals": return "Goals"
        case "assists": return "Assists"
        case "clean_sheets": return "Clean Sheets"
        case "bonus": return "Bonus Points"
        case "red_cards": return "Red Cards"
        case "yellow_cards": return "Yellow Cards"
        default: return data.type.capitalized
        }
    }
}

struct MostActiveHoursCard: View {
    let hours: [Int]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Most Active Hours")
                .font(.fplHeadline)
                .foregroundColor(.fplText)
            
            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 6), spacing: 8) {
                ForEach(0..<24, id: \.self) { hour in
                    HourIndicator(hour: hour, isActive: hours.contains(hour))
                }
            }
        }
        .padding()
        .background(Color.fplCard)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .padding(.horizontal)
    }
}

struct HourIndicator: View {
    let hour: Int
    let isActive: Bool
    
    var body: some View {
        VStack(spacing: 2) {
            Text("\(hour)")
                .font(.caption2)
                .foregroundColor(isActive ? .white : .fplSubtext)
            
            Rectangle()
                .fill(isActive ? Color.fplPrimary : Color.fplBackground)
                .frame(height: 20)
                .cornerRadius(4)
        }
    }
}

struct LoadingView: View {
    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)
            Text("Loading analytics...")
                .font(.fplBody)
                .foregroundColor(.fplSubtext)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.fplBackground)
    }
}

#Preview {
    AnalyticsView()
        .environmentObject(AnalyticsManager())
}
