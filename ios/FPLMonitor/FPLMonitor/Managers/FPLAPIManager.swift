import Foundation
import Combine

class FPLAPIManager: ObservableObject {
    static let shared = FPLAPIManager()
    
    private let fplBaseURL = "https://fantasy.premierleague.com/api"
    private let backendBaseURL = "http://localhost:8000/api/v1" // Test server URL
    var cancellables = Set<AnyCancellable>()
    
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private init() {}
    
    // MARK: - Manager Search
    
    func searchManager(byName name: String) -> AnyPublisher<[FPLManager], Error> {
        return searchManager(query: name, type: .name)
    }
    
    func searchManager(byID id: Int) -> AnyPublisher<[FPLManager], Error> {
        return searchManager(query: String(id), type: .id)
    }
    
    private func searchManager(query: String, type: SearchType) -> AnyPublisher<[FPLManager], Error> {
        isLoading = true
        errorMessage = nil
        
        // Use backend API for both name and ID search
        guard let url = URL(string: "\(backendBaseURL)/managers/search?query=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") else {
            return Fail(error: APIError.invalidURL)
                .eraseToAnyPublisher()
        }
        
        return URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: ManagerSearchResponse.self, decoder: JSONDecoder())
            .map { response in
                response.managers.map { managerData in
                    FPLManager(
                        id: managerData.id,
                        playerFirstName: managerData.player_first_name ?? "",
                        playerLastName: managerData.player_last_name ?? "",
                        playerName: managerData.player_name ?? "",
                        playerRegionName: managerData.player_region_name ?? "",
                        playerRegionCode: managerData.player_region_code ?? "",
                        summaryOverallPoints: managerData.summary_overall_points ?? 0,
                        summaryOverallRank: managerData.summary_overall_rank ?? 0,
                        summaryEventPoints: managerData.summary_event_points ?? 0,
                        summaryEventRank: managerData.summary_event_rank ?? 0,
                        joinedTime: managerData.joined_time ?? "",
                        startedEvent: managerData.started_event ?? 1,
                        favouriteTeam: managerData.favourite_team ?? 0,
                        leagues: nil
                    )
                }
            }
            .receive(on: DispatchQueue.main)
            .handleEvents(
                receiveCompletion: { completion in
                    self.isLoading = false
                    if case .failure(let error) = completion {
                        self.errorMessage = error.localizedDescription
                    }
                }
            )
            .eraseToAnyPublisher()
    }
    
    private func fetchManagerByID(_ managerID: Int) -> AnyPublisher<[FPLManager], Error> {
        guard let url = URL(string: "\(backendBaseURL)/managers/\(managerID)") else {
            return Fail(error: APIError.invalidURL)
                .eraseToAnyPublisher()
        }
        
        return URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: ManagerData.self, decoder: JSONDecoder())
            .map { managerData in
                [FPLManager(
                    id: managerData.id,
                    playerFirstName: managerData.player_first_name ?? "",
                    playerLastName: managerData.player_last_name ?? "",
                    playerName: managerData.player_name ?? "",
                    playerRegionName: managerData.player_region_name ?? "",
                    playerRegionCode: managerData.player_region_code ?? "",
                    summaryOverallPoints: managerData.summary_overall_points ?? 0,
                    summaryOverallRank: managerData.summary_overall_rank ?? 0,
                    summaryEventPoints: managerData.summary_event_points ?? 0,
                    summaryEventRank: managerData.summary_event_rank ?? 0,
                    joinedTime: managerData.joined_time ?? "",
                    startedEvent: managerData.started_event ?? 1,
                    favouriteTeam: managerData.favourite_team ?? 0,
                    leagues: nil
                )]
            }
            .receive(on: DispatchQueue.main)
            .handleEvents(
                receiveCompletion: { _ in
                    self.isLoading = false
                }
            )
            .eraseToAnyPublisher()
    }
    
    // MARK: - Mini Leagues
    
    func getMiniLeagues(for managerID: Int) -> AnyPublisher<[FPLMiniLeague], Error> {
        isLoading = true
        errorMessage = nil
        
        print("🌐 FPLAPIManager: Fetching leagues for manager ID: \(managerID)")
        
        guard let url = URL(string: "\(backendBaseURL)/managers/\(managerID)/leagues") else {
            print("❌ FPLAPIManager: Invalid URL for manager \(managerID)")
            return Fail(error: APIError.invalidURL)
                .eraseToAnyPublisher()
        }
        
        print("🌐 FPLAPIManager: Making request to: \(url)")
        
        return URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: ManagerLeaguesResponse.self, decoder: JSONDecoder())
            .map { response in
                print("🌐 FPLAPIManager: Received response with \(response.classic.count) classic leagues")
                // Extract mini leagues from the response
                return response.classic.map { leagueData in
                    // Get the current phase data (usually the latest phase)
                    let currentPhase = leagueData.active_phases?.last.map { phase in
                        ActivePhaseData(
                            phase: phase.phase,
                            rank: phase.rank,
                            lastRank: phase.last_rank,
                            total: phase.total,
                            memberCount: phase.rank_count,
                            percentileRank: phase.entry_percentile_rank
                        )
                    }
                    
                    return FPLMiniLeague(
                        id: leagueData.id,
                        name: leagueData.name,
                        shortName: leagueData.short_name ?? leagueData.name,
                        created: leagueData.created,
                        closed: leagueData.closed,
                        rank: leagueData.entry_rank ?? 0,
                        maxEntries: leagueData.max_entries ?? 0,
                        leagueType: leagueData.league_type,
                        scoring: leagueData.scoring,
                        adminEntry: leagueData.admin_entry ?? 0,
                        startEvent: leagueData.start_event,
                        entryCanLeave: leagueData.entry_can_leave ?? true,
                        entryCanAdmin: leagueData.entry_can_admin ?? false,
                        entryCanInvite: leagueData.entry_can_invite ?? false,
                        entryCanInviteAdmin: leagueData.entry_can_invite_admin ?? false,
                        entryRank: leagueData.entry_rank ?? 0,
                        entryLastRank: leagueData.entry_last_rank ?? 0,
                        entryCanName: leagueData.entry_can_name ?? true,
                        memberCount: leagueData.rank_count ?? 0,
                        percentileRank: leagueData.entry_percentile_rank ?? 0,
                        currentPhase: currentPhase
                    )
                }
            }
            .receive(on: DispatchQueue.main)
            .handleEvents(
                receiveCompletion: { completion in
                    self.isLoading = false
                    if case .failure(let error) = completion {
                        self.errorMessage = error.localizedDescription
                    }
                }
            )
            .eraseToAnyPublisher()
    }
    
    // MARK: - League Details
    
    func getLeagueDetails(leagueID: Int) -> AnyPublisher<FPLMiniLeagueDetails, Error> {
        isLoading = true
        errorMessage = nil
        
        guard let url = URL(string: "\(backendBaseURL)/leagues/\(leagueID)") else {
            return Fail(error: APIError.invalidURL)
                .eraseToAnyPublisher()
        }
        
        return URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: LeagueDetailsResponse.self, decoder: JSONDecoder())
            .map { response in
                FPLMiniLeagueDetails(
                    league:                     FPLMiniLeague(
                        id: response.league.id,
                        name: response.league.name,
                        shortName: response.league.short_name ?? response.league.name,
                        created: response.league.created,
                        closed: response.league.closed,
                        rank: response.league.entry_rank ?? 0,
                        maxEntries: response.league.max_entries ?? 0,
                        leagueType: response.league.league_type,
                        scoring: response.league.scoring,
                        adminEntry: response.league.admin_entry ?? 0,
                        startEvent: response.league.start_event,
                        entryCanLeave: response.league.entry_can_leave ?? true,
                        entryCanAdmin: response.league.entry_can_admin ?? false,
                        entryCanInvite: response.league.entry_can_invite ?? false,
                        entryCanInviteAdmin: response.league.entry_can_invite_admin ?? false,
                        entryRank: response.league.entry_rank ?? 0,
                        entryLastRank: response.league.entry_last_rank ?? 0,
                        entryCanName: response.league.entry_can_name ?? true,
                        memberCount: response.league.rank_count ?? 0,
                        percentileRank: response.league.entry_percentile_rank ?? 0,
                        currentPhase: response.league.active_phases?.last.map { phase in
                            ActivePhaseData(
                                phase: phase.phase,
                                rank: phase.rank,
                                lastRank: phase.last_rank,
                                total: phase.total,
                                memberCount: phase.rank_count,
                                percentileRank: phase.entry_percentile_rank
                            )
                        }
                    ),
                    standings: FPLStandingsResponse(
                        results: response.standings.results.map { standing in
                            FPLStanding(
                                id: standing.id,
                                eventTotal: standing.event_total,
                                playerName: standing.player_name,
                                rank: standing.rank,
                                lastRank: standing.last_rank,
                                rankSort: standing.rank_sort,
                                total: standing.total,
                                entry: standing.entry,
                                entryName: standing.entry_name
                            )
                        }
                    )
                )
            }
            .receive(on: DispatchQueue.main)
            .handleEvents(
                receiveCompletion: { completion in
                    self.isLoading = false
                    if case .failure(let error) = completion {
                        self.errorMessage = error.localizedDescription
                    }
                }
            )
            .eraseToAnyPublisher()
    }
    
    // MARK: - League Search
    
    func searchLeagues(query: String) -> AnyPublisher<[FPLMiniLeague], Error> {
        isLoading = true
        errorMessage = nil
        
        guard let url = URL(string: "\(backendBaseURL)/leagues/search?query=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") else {
            return Fail(error: APIError.invalidURL)
                .eraseToAnyPublisher()
        }
        
        return URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: LeagueSearchResponse.self, decoder: JSONDecoder())
            .map { response in
                response.leagues.map { leagueData in
                    FPLMiniLeague(
                        id: leagueData.id,
                        name: leagueData.name,
                        shortName: leagueData.short_name ?? leagueData.name,
                        created: leagueData.created,
                        closed: leagueData.closed,
                        rank: 0, // Not provided in search results
                        maxEntries: leagueData.max_entries ?? 0,
                        leagueType: leagueData.league_type,
                        scoring: leagueData.scoring,
                        adminEntry: leagueData.admin_entry ?? 0,
                        startEvent: leagueData.start_event,
                        entryCanLeave: true, // Default values for search results
                        entryCanAdmin: false,
                        entryCanInvite: false,
                        entryCanInviteAdmin: false,
                        entryRank: 0,
                        entryLastRank: 0,
                        entryCanName: true,
                        memberCount: leagueData.rank_count ?? 0,
                        percentileRank: leagueData.entry_percentile_rank ?? 0,
                        currentPhase: leagueData.active_phases?.last.map { phase in
                            ActivePhaseData(
                                phase: phase.phase,
                                rank: phase.rank,
                                lastRank: phase.last_rank,
                                total: phase.total,
                                memberCount: phase.rank_count,
                                percentileRank: phase.entry_percentile_rank
                            )
                        }
                    )
                }
            }
            .receive(on: DispatchQueue.main)
            .handleEvents(
                receiveCompletion: { completion in
                    self.isLoading = false
                    if case .failure(let error) = completion {
                        self.errorMessage = error.localizedDescription
                    }
                }
            )
            .eraseToAnyPublisher()
    }
    
}

// MARK: - Data Models

struct FPLManager: Codable, Identifiable {
    let id: Int
    let playerFirstName: String
    let playerLastName: String
    let playerName: String
    let playerRegionName: String
    let playerRegionCode: String
    let summaryOverallPoints: Int
    let summaryOverallRank: Int
    let summaryEventPoints: Int
    let summaryEventRank: Int
    let joinedTime: String
    let startedEvent: Int
    let favouriteTeam: Int
    let leagues: FPLManagerLeagues?
}

struct FPLManagerResponse: Codable {
    let id: Int
    let playerFirstName: String
    let playerLastName: String
    let playerName: String
    let playerRegionName: String
    let playerRegionCode: String
    let summaryOverallPoints: Int
    let summaryOverallRank: Int
    let summaryEventPoints: Int
    let summaryEventRank: Int
    let joinedTime: String
    let startedEvent: Int
    let favouriteTeam: Int
    let leagues: FPLManagerLeagues?
}

struct FPLManagerLeagues: Codable {
    let classic: [FPLMiniLeague]?
    let h2h: [FPLMiniLeague]?
}

struct FPLMiniLeague: Codable, Identifiable {
    let id: Int
    let name: String
    let shortName: String
    let created: String
    let closed: Bool
    let rank: Int
    let maxEntries: Int
    let leagueType: String
    let scoring: String
    let adminEntry: Int
    let startEvent: Int
    let entryCanLeave: Bool
    let entryCanAdmin: Bool
    let entryCanInvite: Bool
    let entryCanInviteAdmin: Bool
    let entryRank: Int
    let entryLastRank: Int
    let entryCanName: Bool
    let memberCount: Int
    let percentileRank: Int
    let currentPhase: ActivePhaseData?
}

struct ActivePhaseData: Codable {
    let phase: Int
    let rank: Int
    let lastRank: Int
    let total: Int
    let memberCount: Int
    let percentileRank: Int
}

struct FPLMiniLeagueDetails: Codable {
    let league: FPLMiniLeague
    let standings: FPLStandingsResponse
}

struct FPLStandingsResponse: Codable {
    let results: [FPLStanding]
}

struct FPLStanding: Codable, Identifiable {
    let id: Int
    let eventTotal: Int
    let playerName: String
    let rank: Int
    let lastRank: Int
    let rankSort: Int
    let total: Int
    let entry: Int
    let entryName: String
}

enum SearchType {
    case name
    case id
}

// MARK: - API Response Models

struct ManagerSearchResponse: Codable {
    let managers: [ManagerData]
}

struct ManagerData: Codable {
    let id: Int
    let player_name: String?
    let player_first_name: String?
    let player_last_name: String?
    let player_region_name: String?
    let player_region_code: String?
    let summary_overall_points: Int?
    let summary_overall_rank: Int?
    let summary_event_points: Int?
    let summary_event_rank: Int?
    let joined_time: String?
    let started_event: Int?
    let favourite_team: Int?
}

struct ManagerLeaguesResponse: Codable {
    let classic: [LeagueData]
    let h2h: [LeagueData]
}

struct LeagueSearchResponse: Codable {
    let leagues: [LeagueData]
}

struct LeagueData: Codable {
    let id: Int
    let name: String
    let short_name: String?
    let created: String
    let closed: Bool
    let rank: Int?
    let max_entries: Int?
    let league_type: String
    let scoring: String
    let admin_entry: Int?
    let start_event: Int
    let entry_can_leave: Bool?
    let entry_can_admin: Bool?
    let entry_can_invite: Bool?
    let entry_can_invite_admin: Bool?
    let entry_rank: Int?
    let entry_last_rank: Int?
    let entry_can_name: Bool?
    let rank_count: Int?
    let entry_percentile_rank: Int?
    let active_phases: [ActivePhase]?
}

struct ActivePhase: Codable {
    let phase: Int
    let rank: Int
    let last_rank: Int
    let rank_sort: Int
    let total: Int
    let league_id: Int
    let rank_count: Int
    let entry_percentile_rank: Int
}

struct LeagueDetailsResponse: Codable {
    let league: LeagueData
    let standings: StandingsData
}

struct StandingsData: Codable {
    let results: [StandingData]
}

struct StandingData: Codable {
    let id: Int
    let event_total: Int
    let player_name: String
    let rank: Int
    let last_rank: Int
    let rank_sort: Int
    let total: Int
    let entry: Int
    let entry_name: String
}

