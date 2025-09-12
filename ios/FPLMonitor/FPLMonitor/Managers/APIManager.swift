//
//  APIManager.swift
//  FPLMonitor
//
//  Manages API communication with the FPL backend
//

import Foundation
import Combine

class APIManager: ObservableObject {
    let baseURL = "http://localhost:8000/api/v1" // Local proxy (forwards to production)
    private var cancellables = Set<AnyCancellable>()
    
    // Custom URLSession configuration to handle socket options gracefully
    private lazy var urlSession: URLSession = NetworkManager.createOptimizedURLSession()
    
    // MARK: - Fetch Notifications
    func fetchNotifications(completion: @escaping (Result<[FPLNotification], Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/notifications") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        urlSession.dataTask(with: url) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            
            do {
                let notifications = try JSONDecoder().decode([FPLNotification].self, from: data)
                completion(.success(notifications))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    // MARK: - Fetch User Preferences
    func fetchUserPreferences(completion: @escaping (Result<UserPreferences, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/user-preferences") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        urlSession.dataTask(with: url) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            
            do {
                let preferences = try JSONDecoder().decode(UserPreferences.self, from: data)
                completion(.success(preferences))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    // MARK: - Save User Preferences
    func saveUserPreferences(_ preferences: UserPreferences, completion: @escaping (Result<Void, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/user-preferences") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            request.httpBody = try JSONEncoder().encode(preferences)
        } catch {
            completion(.failure(error))
            return
        }
        
        urlSession.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            completion(.success(()))
        }.resume()
    }
    
    // MARK: - Register Device Token
    func registerDeviceToken(_ token: String, completion: @escaping (Result<Void, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/device-tokens") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let deviceTokenData = ["device_token": token, "platform": "ios"]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: deviceTokenData)
        } catch {
            completion(.failure(error))
            return
        }
        
        urlSession.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            completion(.success(()))
        }.resume()
    }
    
    // MARK: - Fetch Analytics Data
    func fetchAnalyticsData(timeRange: AnalyticsTimeRange, completion: @escaping (Result<AnalyticsData, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/analytics/data?time_range=\(timeRange.rawValue)") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        urlSession.dataTask(with: url) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            
            do {
                let analyticsData = try JSONDecoder().decode(AnalyticsData.self, from: data)
                completion(.success(analyticsData))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    // MARK: - Track Analytics Event
    func trackEvent(_ event: AnalyticsEvent, completion: @escaping (Result<Void, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/analytics/events") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            request.httpBody = try JSONEncoder().encode(event)
        } catch {
            completion(.failure(error))
            return
        }
        
        urlSession.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            completion(.success(()))
        }.resume()
    }
}

// MARK: - API Errors
enum APIError: Error, LocalizedError {
    case invalidURL
    case noData
    case decodingError
    case networkError
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .noData:
            return "No data received"
        case .decodingError:
            return "Failed to decode data"
        case .networkError:
            return "Network error occurred"
        }
    }
}
