import Foundation
import Combine
import CoreLocation

@MainActor
class OrderTrackingViewModel: ObservableObject {
    @Published var order: Order
    @Published var driverLocation: CLLocationCoordinate2D?
    @Published var estimatedArrival: Int? // minutes
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private var cancellables = Set<AnyCancellable>()
    private let webSocketManager = WebSocketManager.shared
    
    init(order: Order) {
        self.order = order
        setupWebSocket()
    }
    
    private func setupWebSocket() {
        Task {
            if let token = await KeychainHelper.shared.get(forKey: "accessToken") {
                webSocketManager.connect(forOrderId: order.id, token: token)
            }
        }
        
        webSocketManager.eventSubject
            .receive(on: RunLoop.main)
            .sink { [weak self] event in
                self?.handleWebSocketEvent(event)
            }
            .store(in: &cancellables)
    }
    
    private func handleWebSocketEvent(_ event: WebSocketEvent) {
        switch event {
        case .orderStatusUpdate(let orderId, let status):
            if orderId == order.id {
                updateOrderStatus(status)
            }
            
        case .driverLocationUpdate(let orderId, let latitude, let longitude):
            if orderId == order.id {
                driverLocation = CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
            }
            
        case .etaUpdate(let orderId, let eta):
            if orderId == order.id {
                estimatedArrival = eta
            }
            
        case .connected:
            print("WebSocket connected")
            
        case .disconnected:
            print("WebSocket disconnected")
            
        case .error(let error):
            print("WebSocket error: \(error)")
        }
    }
    
    private func updateOrderStatus(_ status: OrderStatus) {
        // Create updated order with new status
        let updatedOrder = Order(
            id: order.id,
            userId: order.userId,
            restaurantId: order.restaurantId,
            restaurant: order.restaurant,
            driverId: order.driverId,
            driver: order.driver,
            status: status,
            subtotal: order.subtotal,
            deliveryFee: order.deliveryFee,
            serviceFee: order.serviceFee,
            tip: order.tip,
            discount: order.discount,
            total: order.total,
            deliveryAddress: order.deliveryAddress,
            deliveryLatitude: order.deliveryLatitude,
            deliveryLongitude: order.deliveryLongitude,
            specialInstructions: order.specialInstructions,
            estimatedDelivery: order.estimatedDelivery,
            items: order.items,
            createdAt: order.createdAt
        )
        order = updatedOrder
    }
    
    func refreshOrder() async {
        isLoading = true
        
        do {
            order = try await APIClient.shared.request(
                endpoint: Endpoints.order(order.id)
            )
            
            // Update driver location if available
            if let driver = order.driver,
               let lat = driver.latitude,
               let lng = driver.longitude {
                driverLocation = CLLocationCoordinate2D(latitude: lat, longitude: lng)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func disconnect() {
        webSocketManager.disconnect()
    }
    
    var statusSteps: [StatusStep] {
        let allSteps: [(OrderStatus, String, String)] = [
            (.confirmed, "Order Confirmed", "Restaurant received your order"),
            (.preparing, "Preparing", "Your food is being prepared"),
            (.readyForPickup, "Ready for Pickup", "Waiting for driver"),
            (.outForDelivery, "Out for Delivery", "Driver is on the way"),
            (.delivered, "Delivered", "Enjoy your meal!")
        ]
        
        return allSteps.map { status, title, subtitle in
            let isCompleted = order.status.progressValue >= status.progressValue
            let isCurrent = order.status == status
            return StatusStep(
                status: status,
                title: title,
                subtitle: subtitle,
                isCompleted: isCompleted,
                isCurrent: isCurrent
            )
        }
    }
}

struct StatusStep: Identifiable {
    let id = UUID()
    let status: OrderStatus
    let title: String
    let subtitle: String
    let isCompleted: Bool
    let isCurrent: Bool
}

extension OrderDriver {
    var latitude: Double? {
        nil // Would come from real driver data
    }
    
    var longitude: Double? {
        nil
    }
}
