//
//  LeagueView.swift
//  FPLMonitor
//
//  Standings view showing all leagues with rank changes
//

import SwiftUI

struct LeagueView: View {
    @EnvironmentObject private var userManager: UserManager
    @StateObject private var fplAPI = FPLAPIManager.shared
    @State private var allLeagues: [FPLMiniLeague] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationView {
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
                            loadAllLeagues()
                        }
                        .buttonStyle(.borderedProminent)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if allLeagues.isEmpty {
                    VStack(spacing: 20) {
                        Image(systemName: "person.3.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.secondary)
                        
                        Text("No Leagues Found")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundColor(.fplText)
                        
                        Text("This manager might not be in any mini leagues")
                            .font(.body)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    // All leagues standings
                    List {
                        ForEach(allLeagues) { league in
                            LeagueStandingsRowView(league: league)
                                .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)
                        }
                    }
                    .listStyle(PlainListStyle())
                    .refreshable {
                        loadAllLeagues()
                    }
                }
            }
            .navigationTitle("Standings")
            .navigationBarTitleDisplayMode(.large)
            .onAppear {
                loadAllLeagues()
            }
        }
    }
    
    private func loadAllLeagues() {
        guard let manager = userManager.currentManager else {
            errorMessage = "No manager selected"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        fplAPI.getMiniLeagues(for: manager.id)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { completion in
                    isLoading = false
                    if case .failure(let error) = completion {
                        errorMessage = error.localizedDescription
                    }
                },
                receiveValue: { leagues in
                    allLeagues = leagues
                    isLoading = false
                }
            )
            .store(in: &fplAPI.cancellables)
    }
}

// MARK: - League Standings Row View

struct LeagueStandingsRowView: View {
    let league: FPLMiniLeague
    
    var body: some View {
        HStack(spacing: 16) {
            // League Info
            VStack(alignment: .leading, spacing: 4) {
                Text(league.name)
                    .font(.headline)
                    .fontWeight(.semibold)
                    .foregroundColor(.fplText)
                    .lineLimit(2)
                
                Text("\(league.memberCount) members")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            // Rank and Change
            VStack(alignment: .trailing, spacing: 4) {
                HStack(spacing: 8) {
                    // Current Rank
                    Text("\(league.rank)")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.fplPrimary)
                    
                    // Rank Change Indicator
                    RankChangeIndicator(
                        currentRank: league.rank,
                        lastRank: league.entryLastRank
                    )
                }
                
                // Rank Change Text
                RankChangeText(
                    currentRank: league.rank,
                    lastRank: league.entryLastRank
                )
            }
        }
        .padding(.vertical, 12)
        .padding(.horizontal, 16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.fplCard)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.fplBackground, lineWidth: 1)
                )
        )
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
}

// MARK: - Rank Change Indicator

struct RankChangeIndicator: View {
    let currentRank: Int
    let lastRank: Int
    
    var body: some View {
        if lastRank > 0 && currentRank != lastRank {
            Image(systemName: currentRank < lastRank ? "arrow.up" : "arrow.down")
                .font(.title3)
                .fontWeight(.bold)
                .foregroundColor(currentRank < lastRank ? .green : .red)
        } else {
            Image(systemName: "minus")
                .font(.title3)
                .fontWeight(.bold)
                .foregroundColor(.secondary)
        }
    }
}

// MARK: - Rank Change Text

struct RankChangeText: View {
    let currentRank: Int
    let lastRank: Int
    
    var body: some View {
        if lastRank > 0 && currentRank != lastRank {
            let change = lastRank - currentRank
            Text(change > 0 ? "+\(change)" : "\(change)")
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(change > 0 ? .green : .red)
        } else {
            Text("No change")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}

#Preview {
    let sampleLeagues = [
        FPLMiniLeague(
            id: 1,
            name: "Fantasy Football League",
            shortName: "FFL",
            created: "2024-01-01",
            closed: false,
            rank: 5,
            maxEntries: 100,
            leagueType: "x",
            scoring: "c",
            adminEntry: 1,
            startEvent: 1,
            entryCanLeave: true,
            entryCanAdmin: true,
            entryCanInvite: true,
            entryCanInviteAdmin: true,
            entryRank: 5,
            entryLastRank: 8,
            entryCanName: true,
            memberCount: 50,
            percentileRank: 10,
            currentPhase: ActivePhaseData(
                phase: 1,
                rank: 5,
                lastRank: 8,
                total: 100,
                memberCount: 50,
                percentileRank: 10
            )
        ),
        FPLMiniLeague(
            id: 2,
            name: "Premier League Champions",
            shortName: "PLC",
            created: "2024-01-15",
            closed: false,
            rank: 12,
            maxEntries: 200,
            leagueType: "x",
            scoring: "c",
            adminEntry: 2,
            startEvent: 1,
            entryCanLeave: true,
            entryCanAdmin: false,
            entryCanInvite: true,
            entryCanInviteAdmin: false,
            entryRank: 12,
            entryLastRank: 10,
            entryCanName: true,
            memberCount: 150,
            percentileRank: 25,
            currentPhase: ActivePhaseData(
                phase: 1,
                rank: 12,
                lastRank: 10,
                total: 200,
                memberCount: 150,
                percentileRank: 25
            )
        ),
        FPLMiniLeague(
            id: 3,
            name: "Work League",
            shortName: "Work",
            created: "2024-02-01",
            closed: false,
            rank: 3,
            maxEntries: 20,
            leagueType: "x",
            scoring: "c",
            adminEntry: 3,
            startEvent: 1,
            entryCanLeave: true,
            entryCanAdmin: true,
            entryCanInvite: true,
            entryCanInviteAdmin: true,
            entryRank: 3,
            entryLastRank: 3,
            entryCanName: true,
            memberCount: 15,
            percentileRank: 5,
            currentPhase: ActivePhaseData(
                phase: 1,
                rank: 3,
                lastRank: 3,
                total: 20,
                memberCount: 15,
                percentileRank: 5
            )
        )
    ]
    
    let userManager = UserManager.shared
    let manager = FPLManager(
        id: 12345,
        playerFirstName: "Test",
        playerLastName: "Manager",
        playerName: "Test Manager",
        playerRegionName: "England",
        playerRegionCode: "EN",
        summaryOverallPoints: 1500,
        summaryOverallRank: 50000,
        summaryEventPoints: 65,
        summaryEventRank: 25000,
        joinedTime: "2024-01-01T00:00:00Z",
        startedEvent: 1,
        favouriteTeam: 11,
        leagues: FPLManagerLeagues(
            classic: sampleLeagues,
            h2h: []
        )
    )
    return LeagueView()
        .environmentObject(userManager)
        .onAppear {
            userManager.setManager(manager)
        }
}
