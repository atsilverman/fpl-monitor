import SwiftUI

struct LeagueSwitcherView: View {
    @EnvironmentObject private var userManager: UserManager
    @StateObject private var fplAPI = FPLAPIManager.shared
    @State private var miniLeagues: [FPLMiniLeague] = []
    @State private var isLoading = false
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            VStack {
                if isLoading {
                    ProgressView("Loading leagues...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if miniLeagues.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "person.3.fill")
                            .font(.system(size: 50))
                            .foregroundColor(.secondary)
                        
                        Text("No leagues found")
                            .font(.headline)
                            .foregroundColor(.secondary)
                        
                        Text("This manager might not be in any mini leagues")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List {
                        ForEach(miniLeagues) { league in
                            LeagueRow(
                                league: league,
                                isSelected: userManager.activeLeague?.id == league.id,
                                onSelect: {
                                    selectLeague(league)
                                }
                            )
                        }
                    }
                }
            }
            .navigationTitle("Switch League")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .onAppear {
                loadMiniLeagues()
            }
        }
    }
    
    private func loadMiniLeagues() {
        guard let manager = userManager.currentManager else { return }
        
        isLoading = true
        fplAPI.getMiniLeagues(for: manager.id)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { _ in
                    isLoading = false
                },
                receiveValue: { leagues in
                    miniLeagues = leagues
                    isLoading = false
                }
            )
            .store(in: &fplAPI.cancellables)
    }
    
    private func selectLeague(_ league: FPLMiniLeague) {
        userManager.setActiveLeague(league)
        dismiss()
    }
}

struct LeagueRow: View {
    let league: FPLMiniLeague
    let isSelected: Bool
    let onSelect: () -> Void
    
    var body: some View {
        Button(action: onSelect) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(league.name)
                        .font(.headline)
                        .foregroundColor(.primary)
                    
                    HStack {
                        Text("\(league.memberCount) members")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                        
                        if let currentPhase = league.currentPhase, currentPhase.rank > 0 {
                            Text("• Rank: \(currentPhase.rank)")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                            
                            if currentPhase.percentileRank > 0 {
                                Text("(Top \(100 - currentPhase.percentileRank)%)")
                                    .font(.caption)
                                    .foregroundColor(.fplPrimary)
                            }
                        }
                    }
                    
                    if league.entryCanAdmin {
                        Text("Admin")
                            .font(.caption)
                            .foregroundColor(.fplPrimary)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(Color.fplPrimary.opacity(0.2))
                            .cornerRadius(4)
                    }
                }
                
                Spacer()
                
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.fplPrimary)
                        .font(.title2)
                }
            }
            .padding()
            .background(isSelected ? Color.fplPrimary.opacity(0.1) : Color(.systemGray6))
            .cornerRadius(12)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

#Preview {
    LeagueSwitcherView()
        .environmentObject(UserManager.shared)
}
