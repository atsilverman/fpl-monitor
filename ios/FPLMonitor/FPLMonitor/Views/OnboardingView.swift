import SwiftUI
import UserNotifications
import CoreLocation

struct OnboardingView: View {
    @StateObject private var fplAPI = FPLAPIManager.shared
    @StateObject private var userManager = UserManager.shared
    
    @State private var currentStep = 0
    @State private var searchQuery = ""
    @State private var selectedManager: FPLManager?
    @State private var selectedLeague: FPLMiniLeague?
    @State private var searchResults: [FPLManager] = []
    @State private var miniLeagues: [FPLMiniLeague] = []
    
    let totalSteps = 4
    
    // MARK: - Helper Functions
    
    private func loadMiniLeagues() {
        print("🔍 loadMiniLeagues() called")
        guard let manager = selectedManager else { 
            print("❌ No manager selected for loading leagues")
            return 
        }
        
        print("🔄 Loading leagues for manager: \(manager.playerName) (ID: \(manager.id))")
        
        fplAPI.getMiniLeagues(for: manager.id)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { completion in
                    if case .failure(let error) = completion {
                        print("❌ Failed to load leagues: \(error)")
                    }
                },
                receiveValue: { leagues in
                    print("✅ Loaded \(leagues.count) leagues for \(manager.playerName)")
                    miniLeagues = leagues
                }
            )
            .store(in: &fplAPI.cancellables)
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Progress Bar
            ProgressView(value: Double(currentStep), total: Double(totalSteps))
                .progressViewStyle(LinearProgressViewStyle(tint: Color.fplPrimary))
                .padding(.horizontal)
                .padding(.top)
            
            // Content
            TabView(selection: $currentStep) {
                // Step 1: Welcome
                WelcomeStepView()
                    .tag(0)
                
                // Step 2: Manager Search
                ManagerSearchStepView(
                    searchQuery: $searchQuery,
                    searchResults: $searchResults,
                    selectedManager: $selectedManager,
                    onManagerSelected: loadMiniLeagues
                )
                .tag(1)
                
                // Step 3: League Selection
                LeagueSelectionStepView(
                    selectedManager: selectedManager,
                    miniLeagues: $miniLeagues,
                    selectedLeague: $selectedLeague
                )
                .tag(2)
                
                // Step 4: Permissions
                PermissionsStepView()
                .tag(3)
            }
            .tabViewStyle(PageTabViewStyle(indexDisplayMode: .never))
            
            // Navigation Buttons
            HStack {
                if currentStep > 0 {
                    Button("Back") {
                        withAnimation {
                            currentStep -= 1
                        }
                    }
                    .buttonStyle(SecondaryButtonStyle())
                }
                
                Spacer()
                
                Button(nextButtonTitle) {
                    handleNextButton()
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(!canProceed)
            }
            .padding()
        }
        .background(Color(.systemBackground))
        .onAppear {
            loadUserData()
        }
    }
    
    private var nextButtonTitle: String {
        switch currentStep {
        case 0: return "Get Started"
        case 1: return selectedManager != nil ? "Continue" : "Skip"
        case 2: return "Continue"
        case 3: return "Complete Setup"
        default: return "Next"
        }
    }
    
    private var canProceed: Bool {
        switch currentStep {
        case 0: return true
        case 1: return true // Can skip manager selection
        case 2: return true // Can skip league selection
        case 3: return true // Permissions step
        default: return false
        }
    }
    
    private func handleNextButton() {
        if currentStep < totalSteps - 1 {
            withAnimation {
                currentStep += 1
            }
        } else {
            completeOnboarding()
        }
    }
    
    private func loadUserData() {
        if let manager = userManager.currentManager {
            selectedManager = manager
            currentStep = 2 // Skip to league selection
        }
    }
    
    private func completeOnboarding() {
        userManager.setManager(selectedManager)
        userManager.setActiveLeague(selectedLeague)
        userManager.completeOnboarding()
    }
}

// MARK: - Step Views

struct WelcomeStepView: View {
    var body: some View {
        VStack(spacing: 30) {
            Spacer()
            
            // App Icon/Logo
            Image(systemName: "sportscourt.fill")
                .font(.system(size: 80))
                .foregroundColor(.fplPrimary)
            
            VStack(spacing: 16) {
                Text("Welcome to FPL Monitor")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                    .multilineTextAlignment(.center)
                
                Text("Get instant notifications for your Fantasy Premier League team")
                    .font(.title3)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            VStack(spacing: 12) {
                FeatureRow(icon: "bell.fill", title: "Live Notifications", description: "Goals, assists, clean sheets & more")
                FeatureRow(icon: "chart.line.uptrend.xyaxis", title: "Analytics", description: "Track your performance & engagement")
                FeatureRow(icon: "person.2.fill", title: "Mini Leagues", description: "Stay updated on your leagues")
            }
            
            Spacer()
        }
        .padding()
    }
}

struct ManagerSearchStepView: View {
    @StateObject private var fplAPI = FPLAPIManager.shared
    
    @Binding var searchQuery: String
    @Binding var searchResults: [FPLManager]
    @Binding var selectedManager: FPLManager?
    let onManagerSelected: () -> Void
    
    @State private var searchType: SearchType = .name
    
    var body: some View {
        VStack(spacing: 20) {
            VStack(spacing: 16) {
                Text("Find Your Manager")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Search for your FPL manager to get personalized notifications")
                    .font(.title3)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            // Search Type Picker
            Picker("Search Type", selection: $searchType) {
                Text("By Name").tag(SearchType.name)
                Text("By ID").tag(SearchType.id)
            }
            .pickerStyle(SegmentedPickerStyle())
            
            // Search Field
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                
                TextField(searchType == .name ? "Enter manager name" : "Enter manager ID", text: $searchQuery)
                    .textFieldStyle(PlainTextFieldStyle())
                    .keyboardType(searchType == .id ? .numberPad : .default)
                    .onChange(of: searchQuery) { _, newValue in
                        performSearch()
                    }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
            
            // Search Results
            if fplAPI.isLoading {
                ProgressView("Searching...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if !searchResults.isEmpty {
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(searchResults) { manager in
                            ManagerRow(
                                manager: manager,
                                isSelected: selectedManager?.id == manager.id
                            ) {
                                selectedManager = manager
                                onManagerSelected()
                            }
                        }
                    }
                }
            } else if !searchQuery.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "person.crop.circle.badge.questionmark")
                        .font(.system(size: 50))
                        .foregroundColor(.secondary)
                    
                    Text("No managers found")
                        .font(.headline)
                        .foregroundColor(.secondary)
                    
                    Text("Try a different search term")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            
            Spacer()
        }
        .padding()
    }
    
    private func performSearch() {
        guard !searchQuery.isEmpty else {
            searchResults = []
            return
        }
        
        let publisher = searchType == .name ? 
            fplAPI.searchManager(byName: searchQuery) :
            fplAPI.searchManager(byID: Int(searchQuery) ?? 0)
        
        publisher
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { _ in },
                receiveValue: { results in
                    searchResults = results
                }
            )
            .store(in: &fplAPI.cancellables)
    }
}

struct LeagueSelectionStepView: View {
    @StateObject private var fplAPI = FPLAPIManager.shared
    
    let selectedManager: FPLManager?
    @Binding var miniLeagues: [FPLMiniLeague]
    @Binding var selectedLeague: FPLMiniLeague?
    
    @State private var searchQuery = ""
    @State private var searchResults: [FPLMiniLeague] = []
    @State private var isSearching = false
    
    var body: some View {
        VStack(spacing: 20) {
            headerSection
            searchSection
            managerInfoSection
            searchResultsSection
            leaguesSection
            Spacer()
        }
        .padding()
        .onAppear {
            // Leagues will be loaded when manager is selected in the main view
        }
    }
    
    // MARK: - View Components
    
    private var headerSection: some View {
        VStack(spacing: 16) {
            Text("Select Mini League")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Text("Choose your primary mini league for personalized notifications")
                .font(.title3)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
    }
    
    private var searchSection: some View {
        VStack(spacing: 12) {
            Text("Search for Leagues")
                .font(.headline)
                .frame(maxWidth: .infinity, alignment: .leading)
            
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                
                TextField("Enter league name", text: $searchQuery)
                    .textFieldStyle(PlainTextFieldStyle())
                    .onChange(of: searchQuery) { _, newValue in
                        if !newValue.isEmpty {
                            performLeagueSearch()
                        } else {
                            searchResults = []
                        }
                    }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
    }
    
    @ViewBuilder
    private var managerInfoSection: some View {
        if let manager = selectedManager {
            VStack(spacing: 8) {
                Text("Manager: \(manager.playerName)")
                    .font(.headline)
                    .foregroundColor(.fplPrimary)
                
                Text("ID: \(manager.id)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .padding()
            .background(Color.fplPrimary.opacity(0.1))
            .cornerRadius(12)
        }
    }
    
    @ViewBuilder
    private var searchResultsSection: some View {
        if !searchResults.isEmpty {
            VStack(spacing: 12) {
                Text("Search Results")
                    .font(.headline)
                    .frame(maxWidth: .infinity, alignment: .leading)
                
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(searchResults) { league in
                            OnboardingLeagueRow(
                                league: league,
                                isSelected: selectedLeague?.id == league.id
                            ) {
                                selectedLeague = league
                            }
                        }
                    }
                }
                .frame(maxHeight: 200)
            }
        }
    }
    
    private var leaguesSection: some View {
        VStack(spacing: 12) {
            leaguesHeader
            leaguesContent
        }
    }
    
    private var leaguesHeader: some View {
        Group {
            if !miniLeagues.isEmpty {
                Text("Manager's Leagues")
                    .font(.headline)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                Text("Debug: miniLeagues count = \(miniLeagues.count)")
                    .font(.caption)
                    .foregroundColor(.red)
            }
        }
    }
    
    @ViewBuilder
    private var leaguesContent: some View {
        if fplAPI.isLoading {
            ProgressView("Loading leagues...")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if !miniLeagues.isEmpty {
            ScrollView {
                LazyVStack(spacing: 8) {
                    ForEach(miniLeagues) { league in
                        OnboardingLeagueRow(
                            league: league,
                            isSelected: selectedLeague?.id == league.id
                        ) {
                            selectedLeague = league
                        }
                    }
                }
            }
        } else {
            VStack(spacing: 12) {
                Image(systemName: "person.2.circle")
                    .font(.system(size: 50))
                    .foregroundColor(.secondary)
                
                Text("No leagues found")
                    .font(.headline)
                    .foregroundColor(.secondary)
                
                Text("This manager might not be in any mini leagues")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
    
    
    private func performLeagueSearch() {
        guard !searchQuery.isEmpty else {
            searchResults = []
            return
        }
        
        fplAPI.searchLeagues(query: searchQuery)
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { _ in },
                receiveValue: { results in
                    searchResults = results
                }
            )
            .store(in: &fplAPI.cancellables)
    }
}

// MARK: - Row Views

struct ManagerRow: View {
    let manager: FPLManager
    let isSelected: Bool
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(manager.playerName)
                        .font(.headline)
                        .foregroundColor(.primary)
                    
                    Text("ID: \(manager.id)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    Text("\(manager.playerRegionName) • \(manager.summaryOverallPoints) points")
                        .font(.caption)
                        .foregroundColor(.secondary)
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


struct FeatureRow: View {
    let icon: String
    let title: String
    let description: String
    
    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.fplPrimary)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)
                
                Text(description)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
        }
    }
}

// MARK: - OnboardingLeagueRow

struct OnboardingLeagueRow: View {
    let league: FPLMiniLeague
    let isSelected: Bool
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
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

// MARK: - Button Styles

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundColor(.white)
            .padding()
            .frame(maxWidth: .infinity)
            .background(Color.fplPrimary)
            .cornerRadius(12)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
    }
}

struct SecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundColor(.fplPrimary)
            .padding()
            .frame(maxWidth: .infinity)
            .background(Color.fplPrimary.opacity(0.1))
            .cornerRadius(12)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
    }
}

// MARK: - Permissions Step View

struct PermissionsStepView: View {
    @StateObject private var notificationManager = NotificationManager()
    @State private var locationPermissionGranted = false
    @State private var notificationPermissionGranted = false
    
    var body: some View {
        VStack(spacing: 30) {
            Spacer()
            
            // Header
            VStack(spacing: 16) {
                Text("Enable Notifications")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Get instant alerts for goals, assists, and more")
                    .font(.title3)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            // Permission Cards
            VStack(spacing: 20) {
                PermissionCard(
                    icon: "bell.fill",
                    title: "Push Notifications",
                    description: "Get instant alerts when your players score, assist, or keep clean sheets",
                    isGranted: $notificationPermissionGranted,
                    action: requestNotificationPermission
                )
                
                PermissionCard(
                    icon: "location.fill",
                    title: "Location Access",
                    description: "Automatically adjust notification times based on your timezone",
                    isGranted: $locationPermissionGranted,
                    action: requestLocationPermission
                )
            }
            
            // Benefits
            VStack(spacing: 12) {
                Text("Why we need these permissions:")
                    .font(.headline)
                    .frame(maxWidth: .infinity, alignment: .leading)
                
                BenefitRow(icon: "clock.fill", text: "Notifications arrive at the right time for your timezone")
                BenefitRow(icon: "bell.badge.fill", text: "Never miss important FPL moments")
                BenefitRow(icon: "person.2.fill", text: "Stay updated on your mini league standings")
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
            
            Spacer()
        }
        .padding()
        .onAppear {
            checkCurrentPermissions()
        }
    }
    
    private func checkCurrentPermissions() {
        // Check notification permission
        UNUserNotificationCenter.current().getNotificationSettings { settings in
            DispatchQueue.main.async {
                notificationPermissionGranted = settings.authorizationStatus == .authorized
            }
        }
        
        // Check location permission
        let locationManager = CLLocationManager()
        locationPermissionGranted = locationManager.authorizationStatus == .authorizedWhenInUse
    }
    
    private func requestNotificationPermission() {
        notificationManager.requestNotificationPermission { granted in
            DispatchQueue.main.async {
                notificationPermissionGranted = granted
            }
        }
    }
    
    private func requestLocationPermission() {
        let locationManager = CLLocationManager()
        locationManager.requestWhenInUseAuthorization()
        
        // Check permission after a short delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            locationPermissionGranted = locationManager.authorizationStatus == .authorizedWhenInUse
        }
    }
}

struct PermissionCard: View {
    let icon: String
    let title: String
    let description: String
    @Binding var isGranted: Bool
    let action: () -> Void
    
    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(isGranted ? .green : .fplPrimary)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                
                Text(description)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            if isGranted {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
                    .font(.title2)
            } else {
                Button("Allow") {
                    action()
                }
                .buttonStyle(PermissionButtonStyle())
            }
        }
        .padding()
        .background(isGranted ? Color.green.opacity(0.1) : Color(.systemGray6))
        .cornerRadius(12)
    }
}

struct BenefitRow: View {
    let icon: String
    let text: String
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(.fplPrimary)
                .frame(width: 20)
            
            Text(text)
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            Spacer()
        }
    }
}

struct PermissionButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline)
            .fontWeight(.medium)
            .foregroundColor(.white)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Color.fplPrimary)
            .cornerRadius(8)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
    }
}

#Preview {
    OnboardingView()
}
