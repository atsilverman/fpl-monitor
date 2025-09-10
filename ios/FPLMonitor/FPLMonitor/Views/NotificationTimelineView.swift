//
//  NotificationTimelineView.swift
//  FPLMonitor
//
//  Main notifications timeline view
//

import SwiftUI

struct NotificationTimelineView: View {
    @EnvironmentObject private var notificationManager: NotificationManager
    @EnvironmentObject private var analyticsManager: AnalyticsManager
    @State private var selectedFilter: NotificationType?
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Filter Bar
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        FilterButton(
                            title: "All",
                            isSelected: selectedFilter == nil,
                            action: { selectedFilter = nil }
                        )
                        
                        ForEach(NotificationType.allCases, id: \.self) { type in
                            FilterButton(
                                title: type.displayName,
                                isSelected: selectedFilter == type,
                                action: { selectedFilter = type }
                            )
                        }
                    }
                    .padding(.horizontal)
                }
                .padding(.vertical, 8)
                .background(Color.fplBackground)
                
                // Notifications List
                if notificationManager.notifications.isEmpty {
                    EmptyStateView()
                } else {
                    List(filteredNotifications) { notification in
                        NotificationCardView(notification: notification)
                            .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                            .listRowSeparator(.hidden)
                            .onTapGesture {
                                analyticsManager.trackEvent(.notificationTapped, properties: [
                                    "notification_type": notification.type.rawValue,
                                    "player": notification.player
                                ])
                            }
                    }
                    .listStyle(PlainListStyle())
                    .refreshable {
                        notificationManager.refreshNotifications()
                    }
                }
            }
            .navigationTitle("FPL Notifications")
            .navigationBarTitleDisplayMode(.large)
        }
        .onAppear {
            analyticsManager.trackEvent(.appOpen)
        }
    }
    
    private var filteredNotifications: [FPLNotification] {
        if let selectedFilter = selectedFilter {
            return notificationManager.notifications.filter { $0.type == selectedFilter }
        }
        return notificationManager.notifications
    }
}

struct FilterButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.fplCaption)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(isSelected ? Color.fplPrimary : Color.fplCard)
                .foregroundColor(isSelected ? .white : .fplText)
                .cornerRadius(20)
                .shadow(color: .black.opacity(0.1), radius: 2, x: 0, y: 1)
        }
    }
}

struct EmptyStateView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "bell.slash")
                .font(.system(size: 60))
                .foregroundColor(.fplSubtext)
            
            Text("No Notifications Yet")
                .font(.fplHeadline)
                .foregroundColor(.fplText)
            
            Text("You'll receive FPL notifications here when players in your team perform well!")
                .font(.fplBody)
                .foregroundColor(.fplSubtext)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.fplBackground)
    }
}

#Preview {
    NotificationTimelineView()
        .environmentObject(NotificationManager())
        .environmentObject(AnalyticsManager())
}
