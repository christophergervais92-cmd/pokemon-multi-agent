import Foundation
import Combine

enum WebSocketEvent {
    case orderStatusUpdate(orderId: String, status: OrderStatus)
    case driverLocationUpdate(orderId: String, latitude: Double, longitude: Double)
    case etaUpdate(orderId: String, eta: Int)
    case connected
    case disconnected
    case error(Error)
}

@MainActor
class WebSocketManager: ObservableObject {
    static let shared = WebSocketManager()
    
    @Published var isConnected = false
    @Published var currentOrderId: String?
    
    private var webSocketTask: URLSessionWebSocketTask?
    private var session: URLSession
    private var pingTimer: Timer?
    
    let eventSubject = PassthroughSubject<WebSocketEvent, Never>()
    
    private init() {
        self.session = URLSession(configuration: .default)
    }
    
    func connect(forOrderId orderId: String, token: String) {
        disconnect()
        
        let baseURL = ProcessInfo.processInfo.environment["WS_BASE_URL"] ?? "ws://localhost:3000"
        guard let url = URL(string: "\(baseURL)/orders/\(orderId)?token=\(token)") else {
            return
        }
        
        currentOrderId = orderId
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        
        isConnected = true
        eventSubject.send(.connected)
        
        receiveMessage()
        startPing()
    }
    
    func disconnect() {
        pingTimer?.invalidate()
        pingTimer = nil
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        currentOrderId = nil
        isConnected = false
        eventSubject.send(.disconnected)
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            Task { @MainActor in
                guard let self = self else { return }
                
                switch result {
                case .success(let message):
                    switch message {
                    case .string(let text):
                        self.handleMessage(text)
                    case .data(let data):
                        if let text = String(data: data, encoding: .utf8) {
                            self.handleMessage(text)
                        }
                    @unknown default:
                        break
                    }
                    self.receiveMessage()
                    
                case .failure(let error):
                    self.isConnected = false
                    self.eventSubject.send(.error(error))
                    self.eventSubject.send(.disconnected)
                    
                    // Attempt reconnect after 3 seconds
                    if let orderId = self.currentOrderId {
                        Task {
                            try? await Task.sleep(nanoseconds: 3_000_000_000)
                            if let token = await KeychainHelper.shared.get(forKey: "accessToken") {
                                self.connect(forOrderId: orderId, token: token)
                            }
                        }
                    }
                }
            }
        }
    }
    
    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else {
            return
        }
        
        switch type {
        case "order_status":
            if let orderId = json["orderId"] as? String,
               let statusString = json["status"] as? String,
               let status = OrderStatus(rawValue: statusString) {
                eventSubject.send(.orderStatusUpdate(orderId: orderId, status: status))
            }
            
        case "driver_location":
            if let orderId = json["orderId"] as? String,
               let lat = json["latitude"] as? Double,
               let lng = json["longitude"] as? Double {
                eventSubject.send(.driverLocationUpdate(orderId: orderId, latitude: lat, longitude: lng))
            }
            
        case "eta_update":
            if let orderId = json["orderId"] as? String,
               let eta = json["eta"] as? Int {
                eventSubject.send(.etaUpdate(orderId: orderId, eta: eta))
            }
            
        default:
            break
        }
    }
    
    private func startPing() {
        pingTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            self?.webSocketTask?.sendPing { error in
                if let error = error {
                    print("Ping failed: \(error)")
                }
            }
        }
    }
    
    func send(_ message: String) {
        webSocketTask?.send(.string(message)) { error in
            if let error = error {
                print("WebSocket send error: \(error)")
            }
        }
    }
}
