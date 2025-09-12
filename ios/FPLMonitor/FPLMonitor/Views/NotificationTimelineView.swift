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
    @State private var showingSettings = false
    @State private var scrollOffset: CGFloat = 0
    
    var body: some View {
        NavigationView {
            ZStack(alignment: .top) {
                // Notifications List
                if notificationManager.notifications.isEmpty {
                    EmptyStateView()
                } else {
                    ScrollViewReader { proxy in
                        ScrollView {
                            LazyVStack(spacing: 0) {
                                // Invisible spacer to create scroll offset
                                Color.clear
                                    .frame(height: 1)
                                    .id("top")
                                
                                ForEach(notificationManager.notifications) { notification in
                                    NotificationCardView(
                                        notification: notification,
                                        isShowingTimestamps: $isShowingTimestamps,
                                        dragOffset: $dragOffset
                                    )
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 4.6)
                                    .onTapGesture {
                                        analyticsManager.trackEvent(.notificationTapped, properties: [
                                            "notification_type": notification.type.rawValue,
                                            "player": notification.player
                                        ])
                                    }
                                }
                            }
                            .background(
                                GeometryReader { geometry in
                                    Color.clear
                                        .preference(key: ScrollOffsetPreferenceKey.self, value: geometry.frame(in: .named("scroll")).minY)
                                }
                            )
                        }
                        .coordinateSpace(name: "scroll")
                        .onPreferenceChange(ScrollOffsetPreferenceKey.self) { value in
                            scrollOffset = value
                        }
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
                
                // Custom Morphing Header
                MorphingHeaderView(
                    title: "Timeline",
                    scrollOffset: scrollOffset,
                    showingSettings: $showingSettings
                )
            }
            .background(Color.fplAppBackground)
        }
        .background(Color.fplAppBackground)
        .onAppear {
            analyticsManager.trackEvent(.appOpen)
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView()
                .environmentObject(notificationManager)
                .environmentObject(analyticsManager)
        }
    }
}

// MARK: - Scroll Offset Preference Key
private struct ScrollOffsetPreferenceKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

// MARK: - Morphing Header View
private struct MorphingHeaderView: View {
    let title: String
    let scrollOffset: CGFloat
    @Binding var showingSettings: Bool
    
    private var isScrolled: Bool {
        scrollOffset < -50
    }
    
    private var headerHeight: CGFloat {
        isScrolled ? 44 : 96
    }
    
    private var titleScale: CGFloat {
        isScrolled ? 0.8 : 1.0
    }
    
    private var accountButtonScale: CGFloat {
        isScrolled ? 0.8 : 1.0
    }
    
    private var titleFont: Font {
        isScrolled ? .title2.weight(.semibold) : .largeTitle.weight(.bold)
    }
    
    private var accountButtonFont: Font {
        isScrolled ? .title3 : .title2
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Status bar background
            Rectangle()
                .fill(Color.fplAppBackground)
                .frame(height: 0)
            
            // Header content
            ZStack {
                // Background
                Rectangle()
                    .fill(Color.fplAppBackground)
                    .frame(height: headerHeight)
                
                HStack {
                    // Title
                    Text(title)
                        .font(titleFont)
                        .foregroundColor(.fplText)
                        .scaleEffect(titleScale)
                        .animation(.spring(response: 0.3, dampingFraction: 0.8), value: isScrolled)
                    
                    Spacer()
                    
                    // Account button
                    Button(action: {
                        showingSettings = true
                    }) {
                        Image(systemName: "person.crop.circle.fill")
                            .font(accountButtonFont)
                            .foregroundColor(.fplText)
                    }
                    .scaleEffect(accountButtonScale)
                    .animation(.spring(response: 0.3, dampingFraction: 0.8), value: isScrolled)
                }
                .padding(.horizontal, 20)
                .frame(height: headerHeight)
            }
        }
        .background(Color.fplAppBackground)
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
