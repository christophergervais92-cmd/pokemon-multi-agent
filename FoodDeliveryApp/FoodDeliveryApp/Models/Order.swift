import Foundation

enum OrderStatus: String, Codable, CaseIterable {
    case pending = "PENDING"
    case confirmed = "CONFIRMED"
    case preparing = "PREPARING"
    case readyForPickup = "READY_FOR_PICKUP"
    case outForDelivery = "OUT_FOR_DELIVERY"
    case delivered = "DELIVERED"
    case cancelled = "CANCELLED"
    
    var displayName: String {
        switch self {
        case .pending: return "Pending"
        case .confirmed: return "Confirmed"
        case .preparing: return "Preparing"
        case .readyForPickup: return "Ready for Pickup"
        case .outForDelivery: return "Out for Delivery"
        case .delivered: return "Delivered"
        case .cancelled: return "Cancelled"
        }
    }
    
    var icon: String {
        switch self {
        case .pending: return "clock"
        case .confirmed: return "checkmark.circle"
        case .preparing: return "flame"
        case .readyForPickup: return "bag"
        case .outForDelivery: return "car"
        case .delivered: return "checkmark.circle.fill"
        case .cancelled: return "xmark.circle"
        }
    }
    
    var progressValue: Double {
        switch self {
        case .pending: return 0.1
        case .confirmed: return 0.25
        case .preparing: return 0.5
        case .readyForPickup: return 0.7
        case .outForDelivery: return 0.85
        case .delivered: return 1.0
        case .cancelled: return 0
        }
    }
    
    var isActive: Bool {
        switch self {
        case .pending, .confirmed, .preparing, .readyForPickup, .outForDelivery:
            return true
        case .delivered, .cancelled:
            return false
        }
    }
}

struct Order: Codable, Identifiable, Equatable {
    let id: String
    let userId: String
    let restaurantId: String
    let restaurant: OrderRestaurant?
    let driverId: String?
    let driver: OrderDriver?
    let status: OrderStatus
    let subtotal: Decimal
    let deliveryFee: Decimal
    let serviceFee: Decimal
    let tip: Decimal
    let discount: Decimal
    let total: Decimal
    let deliveryAddress: DeliveryAddress
    let deliveryLatitude: Double?
    let deliveryLongitude: Double?
    let specialInstructions: String?
    let estimatedDelivery: Date?
    let items: [OrderItem]
    let createdAt: Date
    
    var totalFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: total as NSDecimalNumber) ?? "$\(total)"
    }
    
    var createdAtFormatted: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: createdAt)
    }
    
    var estimatedDeliveryFormatted: String? {
        guard let date = estimatedDelivery else { return nil }
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
    
    static func == (lhs: Order, rhs: Order) -> Bool {
        lhs.id == rhs.id && lhs.status == rhs.status
    }
    
    static let preview = Order(
        id: "1",
        userId: "1",
        restaurantId: "1",
        restaurant: OrderRestaurant(id: "1", name: "Pizza Palace", imageUrl: nil),
        driverId: "1",
        driver: OrderDriver(id: "1", name: "Mike", phone: "+1234567890", avatarUrl: nil, vehicleType: "Car", rating: 4.9),
        status: .outForDelivery,
        subtotal: 34.97,
        deliveryFee: 2.99,
        serviceFee: 1.50,
        tip: 5.00,
        discount: 0,
        total: 44.46,
        deliveryAddress: DeliveryAddress(street: "123 Main St", apartment: "Apt 4B", city: "San Francisco", state: "CA", zipCode: "94102"),
        deliveryLatitude: 37.7749,
        deliveryLongitude: -122.4194,
        specialInstructions: "Leave at door",
        estimatedDelivery: Date().addingTimeInterval(1800),
        items: [
            OrderItem(id: "1", menuItemId: "1", name: "Margherita Pizza", quantity: 2, unitPrice: 14.99, totalPrice: 29.98, selectedOptions: nil, specialNotes: nil),
            OrderItem(id: "2", menuItemId: "3", name: "Caesar Salad", quantity: 1, unitPrice: 9.99, totalPrice: 9.99, selectedOptions: nil, specialNotes: nil)
        ],
        createdAt: Date()
    )
}

struct OrderRestaurant: Codable, Equatable {
    let id: String
    let name: String
    let imageUrl: String?
}

struct OrderDriver: Codable, Equatable {
    let id: String
    let name: String
    let phone: String
    let avatarUrl: String?
    let vehicleType: String
    let rating: Double
}

struct OrderItem: Codable, Identifiable, Equatable {
    let id: String
    let menuItemId: String
    let name: String
    let quantity: Int
    let unitPrice: Decimal
    let totalPrice: Decimal
    let selectedOptions: [[String: String]]?
    let specialNotes: String?
    
    var totalPriceFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: totalPrice as NSDecimalNumber) ?? "$\(totalPrice)"
    }
}

struct DeliveryAddress: Codable, Equatable {
    let street: String
    let apartment: String?
    let city: String
    let state: String
    let zipCode: String
    
    var formatted: String {
        var address = street
        if let apt = apartment, !apt.isEmpty {
            address += ", \(apt)"
        }
        address += "\n\(city), \(state) \(zipCode)"
        return address
    }
    
    var oneLine: String {
        var address = street
        if let apt = apartment, !apt.isEmpty {
            address += ", \(apt)"
        }
        return address
    }
}

struct CreateOrderRequest: Encodable {
    let restaurantId: String
    let items: [CreateOrderItem]
    let deliveryAddress: DeliveryAddress
    let deliveryLatitude: Double?
    let deliveryLongitude: Double?
    let specialInstructions: String?
    let tip: Decimal
    let paymentMethodId: String
}

struct CreateOrderItem: Encodable {
    let menuItemId: String
    let quantity: Int
    let selectedOptions: [[String: String]]?
    let specialNotes: String?
}
