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
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Notifications List
                if notificationManager.notifications.isEmpty {
                    EmptyStateView()
                } else {
                    List(notificationManager.notifications) { notification in
                        NotificationCardView(notification: notification)
                            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
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
