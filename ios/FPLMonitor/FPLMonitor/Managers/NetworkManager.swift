//
//  NetworkManager.swift
//  FPLMonitor
//
//  Handles network configuration and reduces socket-related errors
//

import Foundation
import Network

class NetworkManager: ObservableObject {
    static let shared = NetworkManager()
    
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "NetworkMonitor")
    
    @Published var isConnected = false
    @Published var connectionType: NWInterface.InterfaceType?
    
    private init() {
        startMonitoring()
    }
    
    private func startMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isConnected = path.status == .satisfied
                self?.connectionType = path.availableInterfaces.first?.type
            }
        }
        monitor.start(queue: queue)
    }
    
    deinit {
        monitor.cancel()
    }
    
    // MARK: - URLSession Configuration
    
    static func createOptimizedURLSession() -> URLSession {
        let config = URLSessionConfiguration.default
        
        // Basic configuration
        config.timeoutIntervalForRequest = 30.0
        config.timeoutIntervalForResource = 60.0
        config.waitsForConnectivity = true
        config.allowsCellularAccess = true
        config.httpMaximumConnectionsPerHost = 6
        config.requestCachePolicy = .useProtocolCachePolicy
        
        // Connection pooling and keep-alive settings
        // Note: httpShouldUsePipelining is deprecated in iOS 18.4, using HTTP/2 and HTTP/3 instead
        config.httpMaximumConnectionsPerHost = 4
        
        // Headers to reduce socket configuration issues
        config.httpAdditionalHeaders = [
            "User-Agent": "FPLMonitor-iOS/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        ]
        
        // Create URLSession with custom delegate to handle socket errors gracefully
        let delegate = NetworkSessionDelegate()
        return URLSession(configuration: config, delegate: delegate, delegateQueue: nil)
    }
}

// MARK: - URLSessionDelegate

class NetworkSessionDelegate: NSObject, URLSessionDelegate {
    
    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        // Handle SSL/TLS challenges
        completionHandler(.performDefaultHandling, nil)
    }
    
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        // Handle completion and any socket-related errors gracefully
        if let error = error {
            // Log socket errors but don't treat them as critical failures
            if error.localizedDescription.contains("SO_NOWAKEFROMSLEEP") {
                // This is a known iOS socket configuration issue - not critical
                print("🔧 NetworkManager: Socket configuration warning (non-critical): \(error.localizedDescription)")
            } else {
                print("❌ NetworkManager: Network error: \(error.localizedDescription)")
            }
        }
    }
    
    func urlSession(_ session: URLSession, task: URLSessionTask, didFinishCollecting metrics: URLSessionTaskMetrics) {
        // Log network performance metrics for debugging
        if !metrics.transactionMetrics.isEmpty {
            let duration = metrics.taskInterval.duration
            print("🌐 NetworkManager: Request completed in \(duration)s")
        }
    }
}
