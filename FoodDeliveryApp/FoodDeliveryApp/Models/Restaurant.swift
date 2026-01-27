import Foundation
import CoreLocation

struct Restaurant: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let description: String?
    let imageUrl: String?
    let coverImageUrl: String?
    let category: String
    let rating: Double
    let reviewCount: Int
    let deliveryTimeMin: Int
    let deliveryTimeMax: Int
    let deliveryFee: Decimal
    let minimumOrder: Decimal
    let latitude: Double
    let longitude: Double
    let address: String
    let isOpen: Bool
    let openingTime: String?
    let closingTime: String?
    
    var deliveryTimeText: String {
        "\(deliveryTimeMin)-\(deliveryTimeMax) min"
    }
    
    var deliveryFeeText: String {
        if deliveryFee == 0 {
            return "Free Delivery"
        }
        return "$\(deliveryFee) Delivery"
    }
    
    var location: CLLocation {
        CLLocation(latitude: latitude, longitude: longitude)
    }
    
    func distance(from userLocation: CLLocation) -> Double {
        return location.distance(from: userLocation) / 1000 // km
    }
    
    static let preview = Restaurant(
        id: "1",
        name: "Pizza Palace",
        description: "The best pizza in town with fresh ingredients",
        imageUrl: "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400",
        coverImageUrl: "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800",
        category: "Pizza",
        rating: 4.5,
        reviewCount: 234,
        deliveryTimeMin: 20,
        deliveryTimeMax: 35,
        deliveryFee: 2.99,
        minimumOrder: 15.00,
        latitude: 37.7749,
        longitude: -122.4194,
        address: "123 Main St, San Francisco, CA",
        isOpen: true,
        openingTime: "10:00",
        closingTime: "22:00"
    )
    
    static let previews: [Restaurant] = [
        preview,
        Restaurant(
            id: "2",
            name: "Sushi Master",
            description: "Authentic Japanese sushi and ramen",
            imageUrl: "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=400",
            coverImageUrl: nil,
            category: "Japanese",
            rating: 4.8,
            reviewCount: 567,
            deliveryTimeMin: 25,
            deliveryTimeMax: 40,
            deliveryFee: 3.99,
            minimumOrder: 20.00,
            latitude: 37.7849,
            longitude: -122.4094,
            address: "456 Oak St, San Francisco, CA",
            isOpen: true,
            openingTime: "11:00",
            closingTime: "23:00"
        ),
        Restaurant(
            id: "3",
            name: "Burger Joint",
            description: "Juicy burgers and crispy fries",
            imageUrl: "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400",
            coverImageUrl: nil,
            category: "Burgers",
            rating: 4.3,
            reviewCount: 189,
            deliveryTimeMin: 15,
            deliveryTimeMax: 25,
            deliveryFee: 0,
            minimumOrder: 10.00,
            latitude: 37.7649,
            longitude: -122.4294,
            address: "789 Pine St, San Francisco, CA",
            isOpen: true,
            openingTime: "10:00",
            closingTime: "00:00"
        )
    ]
}

struct RestaurantCategory: Identifiable, Equatable {
    let id: String
    let name: String
    let icon: String
    
    static let all: [RestaurantCategory] = [
        RestaurantCategory(id: "all", name: "All", icon: "square.grid.2x2"),
        RestaurantCategory(id: "pizza", name: "Pizza", icon: "🍕"),
        RestaurantCategory(id: "burgers", name: "Burgers", icon: "🍔"),
        RestaurantCategory(id: "sushi", name: "Sushi", icon: "🍣"),
        RestaurantCategory(id: "chinese", name: "Chinese", icon: "🥡"),
        RestaurantCategory(id: "mexican", name: "Mexican", icon: "🌮"),
        RestaurantCategory(id: "indian", name: "Indian", icon: "🍛"),
        RestaurantCategory(id: "thai", name: "Thai", icon: "🍜"),
        RestaurantCategory(id: "healthy", name: "Healthy", icon: "🥗"),
        RestaurantCategory(id: "dessert", name: "Dessert", icon: "🍰")
    ]
}
