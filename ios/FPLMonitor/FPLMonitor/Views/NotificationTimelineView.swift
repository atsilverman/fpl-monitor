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
    @State private var isShowingTimestamps = false
    @State private var dragOffset: CGFloat = 0
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Notifications List
                if notificationManager.notifications.isEmpty {
                    EmptyStateView()
                } else {
                    List(notificationManager.notifications) { notification in
                        NotificationCardView(
                            notification: notification,
                            isShowingTimestamps: $isShowingTimestamps,
                            dragOffset: $dragOffset
                        )
                        .listRowInsets(EdgeInsets(top: 4.6, leading: 16, bottom: 4.6, trailing: 16))
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
                    .background(Color.fplAppBackground)
                    .refreshable {
                        notificationManager.refreshNotifications()
                    }
                    .gesture(
                        DragGesture()
                            .onChanged { value in
                                if value.translation.width < 0 {
                                    dragOffset = max(value.translation.width, -100)
                                }
                            }
                            .onEnded { value in
                                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                                    if value.translation.width < -50 {
                                        isShowingTimestamps = true
                                        dragOffset = -80
                                    } else {
                                        isShowingTimestamps = false
                                        dragOffset = 0
                                    }
                                }
                            }
                    )
                }
            }
            .background(Color.fplAppBackground)
            .navigationTitle("Timeline")
            .navigationBarTitleDisplayMode(.large)
        }
        .background(Color.fplAppBackground)
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
        .background(Color.fplAppBackground)
    }
}

#Preview {
    NotificationTimelineView()
        .environmentObject(NotificationManager())
        .environmentObject(AnalyticsManager())
}
