import SwiftUI

struct LeagueStandingsView: View {
    @EnvironmentObject private var userManager: UserManager
    @StateObject private var fplAPI = FPLAPIManager.shared
    @State private var leagueDetails: FPLMiniLeagueDetails?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showingSettings = false
    @State private var scrollOffset: CGFloat = 0
    
    let league: FPLMiniLeague
    
    var body: some View {
        NavigationView {
            ZStack(alignment: .top) {
                VStack {
                    if isLoading {
                        ProgressView("Loading standings...")
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else if let errorMessage = errorMessage {
                        VStack(spacing: 16) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.system(size: 50))
                                .foregroundColor(.red)
                            
                            Text("Error loading standings")
                                .font(.headline)
                                .foregroundColor(.fplText)
                            
                            Text(errorMessage)
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .multilineTextAlignment(.center)
                            
                            Button("Retry") {
                                loadLeagueDetails()
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else if let details = leagueDetails {
                        ScrollView {
                            LazyVStack(spacing: 0) {
                                // Invisible spacer to create scroll offset
                                Color.clear
                                    .frame(height: 1)
                                    .id("top")
                                
                                // League Header
                                LeagueHeaderView(league: details.league)
                                    .padding()
                                    .background(Color(.systemGray6))
                                
                                // Standings List
                                LazyVStack(spacing: 0) {
                                    ForEach(Array(details.standings.results.enumerated()), id: \.element.id) { index, standing in
                                        StandingRowView(
                                            standing: standing,
                                            rank: index + 1,
                                            isCurrentUser: standing.entry == userManager.currentManager?.id
                                        )
                                        .padding(.horizontal, 16)
                                        .padding(.vertical, 8)
                                    }
                                }
                                .background(Color.fplAppBackground)
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
                    } else {
                        VStack(spacing: 16) {
                            Image(systemName: "person.3.fill")
                                .font(.system(size: 50))
                                .foregroundColor(.secondary)
                            
                            Text("No standings available")
                                .font(.headline)
                                .foregroundColor(.secondary)
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    }
                }
                
                // Custom Morphing Header
                MorphingHeaderView(
                    title: league.name,
                    scrollOffset: scrollOffset,
                    showingSettings: $showingSettings
                )
            }
            .background(Color.fplAppBackground)
            .onAppear {
                loadLeagueDetails()
            }
            .sheet(isPresented: $showingSettings) {
                SettingsView()
                    .environmentObject(userManager)
            }
        }
    }
    
    private func loadLeagueDetails() {
        isLoading = true
        errorMessage = nil
        
        fplAPI.getLeagueDetails(leagueID: league.id)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { completion in
                    isLoading = false
                    if case .failure(let error) = completion {
                        errorMessage = error.localizedDescription
                    }
                },
                receiveValue: { details in
                    leagueDetails = details
                    isLoading = false
                }
            )
            .store(in: &fplAPI.cancellables)
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

struct LeagueHeaderView: View {
    let league: FPLMiniLeague
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(league.name)
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.fplText)
                    
                    if let currentPhase = league.currentPhase {
                        Text("\(league.memberCount) members • Phase \(currentPhase.phase)")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    } else {
                        Text("\(league.memberCount) members")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    if let currentPhase = league.currentPhase, currentPhase.rank > 0 {
                        Text("Your Rank")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        Text("\(currentPhase.rank)")
                            .font(.title)
                            .fontWeight(.bold)
                            .foregroundColor(.fplPrimary)
                        
                        if currentPhase.percentileRank > 0 {
                            Text("Top \(100 - currentPhase.percentileRank)%")
                                .font(.caption)
                                .foregroundColor(.fplPrimary)
                        }
                    }
                }
            }
            
            // League Type and Scoring
            HStack {
                Label(league.leagueType.uppercased(), systemImage: "tag")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Label(league.scoring.uppercased(), systemImage: "chart.bar")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
    }
}

struct StandingRowView: View {
    let standing: FPLStanding
    let rank: Int
    let isCurrentUser: Bool
    
    var body: some View {
        HStack {
            // Rank
            Text("\(rank)")
                .font(.headline)
                .fontWeight(.bold)
                .foregroundColor(isCurrentUser ? .fplPrimary : .primary)
                .frame(width: 30, alignment: .leading)
            
            // Player Info
            VStack(alignment: .leading, spacing: 2) {
                Text(standing.playerName)
                    .font(.headline)
                    .foregroundColor(isCurrentUser ? .fplPrimary : .primary)
                
                Text(standing.entryName)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            // Points
            VStack(alignment: .trailing, spacing: 2) {
                Text("\(standing.total)")
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(isCurrentUser ? .fplPrimary : .primary)
                
                Text("Total")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            // Event Points
            VStack(alignment: .trailing, spacing: 2) {
                Text("\(standing.eventTotal)")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(.secondary)
                
                Text("GW")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .frame(width: 50, alignment: .trailing)
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 12)
        .background(isCurrentUser ? Color.fplPrimary.opacity(0.1) : Color.clear)
        .cornerRadius(8)
    }
}

#Preview {
    LeagueStandingsView(league: FPLMiniLeague(
        id: 1,
        name: "Test League",
        shortName: "Test",
        created: "2024-01-01",
        closed: false,
        rank: 1,
        maxEntries: 100,
        leagueType: "x",
        scoring: "c",
        adminEntry: 1,
        startEvent: 1,
        entryCanLeave: true,
        entryCanAdmin: true,
        entryCanInvite: true,
        entryCanInviteAdmin: true,
        entryRank: 1,
        entryLastRank: 1,
        entryCanName: true,
        memberCount: 50,
        percentileRank: 10,
        currentPhase: ActivePhaseData(
            phase: 1,
            rank: 1,
            lastRank: 1,
            total: 100,
            memberCount: 50,
            percentileRank: 10
        )
    ))
    .environmentObject(UserManager.shared)
}
