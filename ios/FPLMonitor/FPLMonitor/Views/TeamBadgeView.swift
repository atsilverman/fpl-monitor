//
//  TeamBadgeView.swift
//  FPLMonitor
//
//  Team badge display component for notifications
//

import SwiftUI

struct TeamBadgeView: View {
    let teamName: String
    let isOwned: Bool
    let size: CGFloat
    let teamAbbreviation: String
    
    init(teamName: String, isOwned: Bool = false, size: CGFloat = 32, teamAbbreviation: String = "") {
        self.teamName = teamName
        self.isOwned = isOwned
        self.size = size
        self.teamAbbreviation = teamAbbreviation.isEmpty ? String(teamName.prefix(3)).uppercased() : teamAbbreviation
    }
    
    var body: some View {
        Group {
            if let image = UIImage(named: badgeImageName) {
                Image(uiImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .onAppear {
                        // Badge loaded successfully
                    }
            } else {
                // Fallback: Show team abbreviation in a rounded rectangle
                Text(teamAbbreviation)
                    .font(.system(size: size * 0.4, weight: .bold))
                    .foregroundColor(.white)
                    .frame(width: size, height: size)
                    .background(Color.blue)
                    .clipShape(RoundedRectangle(cornerRadius: size * 0.2))
                    .onAppear {
                        print("❌ Image not found: \(badgeImageName)")
                        print("Using fallback for team: \(teamName)")
                        
                        // Try alternative names
                        let alternatives = [
                            "\(badgeImageName).png",
                            "\(badgeImageName).jpg", 
                            "\(badgeImageName).jpeg",
                            badgeImageName.replacingOccurrences(of: "_badge", with: ""),
                            badgeImageName.replacingOccurrences(of: "_badge", with: "_logo")
                        ]
                        for alt in alternatives {
                            if UIImage(named: alt) != nil {
                                print("✅ Found alternative: \(alt)")
                                break
                            }
                        }
                    }
            }
        }
        .frame(width: size, height: size)
        .clipShape(RoundedRectangle(cornerRadius: size * 0.2))
    }
    
    private var badgeImageName: String {
        // Map team names to badge file names based on available badges
        let teamMapping: [String: String] = [
            "Arsenal": "Arsenal",
            "Aston Villa": "Aston Villa", 
            "Bournemouth": "Bournemouth",
            "Brentford": "Brentford",
            "Brighton": "Brighton",
            "Burnley": "Burnley",
            "Chelsea": "Chelsea",
            "Crystal Palace": "Crystal Palace",
            "Everton": "Everton",
            "Fulham": "Fulham",
            "Leeds": "Leeds",
            "Liverpool": "Liverpool",
            "Manchester City": "Man City",
            "Man City": "Man City",
            "Manchester United": "Man Utd",
            "Man United": "Man Utd",
            "Newcastle": "Newcastle",
            "Nottingham Forest": "Nott'm Forest",
            "Nott'm Forest": "Nott'm Forest",
            "Tottenham": "Spurs",
            "Spurs": "Spurs",
            "West Ham": "West Ham",
            "Wolves": "Wolves"
        ]
        
        let mappedName = teamMapping[teamName] ?? teamName
        let result = "\(mappedName)_badge"
        return result
    }
}

#Preview {
    VStack(spacing: 20) {
        HStack(spacing: 16) {
            TeamBadgeView(teamName: "Arsenal", isOwned: false)
            TeamBadgeView(teamName: "Manchester City", isOwned: true)
            TeamBadgeView(teamName: "Liverpool", isOwned: false)
            TeamBadgeView(teamName: "Chelsea", isOwned: true)
        }
        
        HStack(spacing: 16) {
            TeamBadgeView(teamName: "Tottenham", isOwned: false, size: 24)
            TeamBadgeView(teamName: "Manchester United", isOwned: true, size: 24)
            TeamBadgeView(teamName: "Newcastle", isOwned: false, size: 24)
            TeamBadgeView(teamName: "West Ham", isOwned: true, size: 24)
        }
    }
    .padding()
    .background(Color(.systemGroupedBackground))
}
