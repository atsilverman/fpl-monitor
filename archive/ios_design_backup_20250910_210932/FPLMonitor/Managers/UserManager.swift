import Foundation
import Combine

class UserManager: ObservableObject {
    static let shared = UserManager()
    
    @Published var currentManager: FPLManager?
    @Published var activeLeague: FPLMiniLeague?
    @Published var hasCompletedOnboarding = false
    
    private let userDefaults = UserDefaults.standard
    private let managerKey = "fpl_current_manager"
    private let leagueKey = "fpl_active_league"
    private let onboardingKey = "fpl_onboarding_completed"
    
    private init() {
        loadUserData()
    }
    
    // MARK: - Manager Management
    
    func setManager(_ manager: FPLManager?) {
        currentManager = manager
        saveManager(manager)
    }
    
    func clearManager() {
        currentManager = nil
        userDefaults.removeObject(forKey: managerKey)
    }
    
    private func saveManager(_ manager: FPLManager?) {
        guard let manager = manager else {
            userDefaults.removeObject(forKey: managerKey)
            return
        }
        
        if let data = try? JSONEncoder().encode(manager) {
            userDefaults.set(data, forKey: managerKey)
        }
    }
    
    private func loadManager() -> FPLManager? {
        guard let data = userDefaults.data(forKey: managerKey) else { return nil }
        return try? JSONDecoder().decode(FPLManager.self, from: data)
    }
    
    // MARK: - League Management
    
    func setActiveLeague(_ league: FPLMiniLeague?) {
        activeLeague = league
        saveActiveLeague(league)
    }
    
    func switchLeague(_ league: FPLMiniLeague) {
        setActiveLeague(league)
    }
    
    func clearActiveLeague() {
        activeLeague = nil
        userDefaults.removeObject(forKey: leagueKey)
    }
    
    private func saveActiveLeague(_ league: FPLMiniLeague?) {
        guard let league = league else {
            userDefaults.removeObject(forKey: leagueKey)
            return
        }
        
        if let data = try? JSONEncoder().encode(league) {
            userDefaults.set(data, forKey: leagueKey)
        }
    }
    
    private func loadActiveLeague() -> FPLMiniLeague? {
        guard let data = userDefaults.data(forKey: leagueKey) else { return nil }
        return try? JSONDecoder().decode(FPLMiniLeague.self, from: data)
    }
    
    // MARK: - Onboarding
    
    func completeOnboarding() {
        hasCompletedOnboarding = true
        userDefaults.set(true, forKey: onboardingKey)
    }
    
    func resetOnboarding() {
        hasCompletedOnboarding = false
        userDefaults.set(false, forKey: onboardingKey)
    }
    
    func resetAllData() {
        clearManager()
        clearActiveLeague()
        resetOnboarding()
    }
    
    // MARK: - Data Loading
    
    private func loadUserData() {
        currentManager = loadManager()
        activeLeague = loadActiveLeague()
        hasCompletedOnboarding = userDefaults.bool(forKey: onboardingKey)
        
        print("🔍 UserManager: Loading user data")
        print("🔍 UserManager: hasCompletedOnboarding = \(hasCompletedOnboarding)")
        print("🔍 UserManager: currentManager = \(currentManager?.playerName ?? "nil")")
        print("🔍 UserManager: activeLeague = \(activeLeague?.name ?? "nil")")
        print("🔍 UserManager: onboardingKey value = \(userDefaults.object(forKey: onboardingKey) ?? "nil")")
    }
    
    // MARK: - Convenience Properties
    
    var managerID: Int? {
        return currentManager?.id
    }
    
    var managerName: String? {
        return currentManager?.playerName
    }
    
    var leagueID: Int? {
        return activeLeague?.id
    }
    
    var leagueName: String? {
        return activeLeague?.name
    }
    
    var isLoggedIn: Bool {
        return currentManager != nil
    }
    
    var hasActiveLeague: Bool {
        return activeLeague != nil
    }
    
    // MARK: - User Actions
    
    func logout() {
        clearManager()
        clearActiveLeague()
        resetOnboarding()
    }
    
    func updateManagerInfo() {
        // This would typically fetch fresh data from the API
        // For now, we'll just reload from storage
        loadUserData()
    }
}
