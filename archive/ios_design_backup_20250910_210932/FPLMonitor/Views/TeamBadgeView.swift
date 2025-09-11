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
                        print("✅ Successfully loaded badge: \(badgeImageName)")
                    }
            } else {
                // Fallback: Show team abbreviation in a circle
                Text(teamAbbreviation)
                    .font(.system(size: size * 0.4, weight: .bold))
                    .foregroundColor(.white)
                    .frame(width: size, height: size)
                    .background(Color.blue)
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
        .clipShape(Circle())
        .overlay(
            Circle()
                .stroke(
                    isOwned ? Color.white.opacity(0.4) : Color.gray.opacity(0.3),
                    lineWidth: 1.5
                )
        )
        .shadow(
            color: isOwned ? Color.black.opacity(0.3) : Color.black.opacity(0.1),
            radius: 2,
            x: 0,
            y: 1
        )
    }
    
    private var badgeImageName: String {
        // Convert team name to standardized badge file name
        let normalizedName = teamName.lowercased()
            .replacingOccurrences(of: " ", with: "_")
            .replacingOccurrences(of: "'", with: "")
            .replacingOccurrences(of: "manchester city", with: "man_city")
            .replacingOccurrences(of: "manchester united", with: "man_utd")
            .replacingOccurrences(of: "man city", with: "man_city")
            .replacingOccurrences(of: "man utd", with: "man_utd")
            .replacingOccurrences(of: "nottingham forest", with: "nottingham_forest")
            .replacingOccurrences(of: "nott'm forest", with: "nottingham_forest")
            .replacingOccurrences(of: "tottenham", with: "tottenham")
            .replacingOccurrences(of: "spurs", with: "tottenham")
            .replacingOccurrences(of: "west ham", with: "west_ham")
            .replacingOccurrences(of: "crystal palace", with: "crystal_palace")
            .replacingOccurrences(of: "aston villa", with: "aston_villa")
        
        let result = "\(normalizedName)_badge"
        print("Team: '\(teamName)' -> Badge: '\(result)'")
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
