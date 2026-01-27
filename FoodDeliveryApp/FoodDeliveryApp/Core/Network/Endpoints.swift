import Foundation

enum Endpoints {
    // MARK: - Auth
    static let register = "/auth/register"
    static let login = "/auth/login"
    static let verifyOTP = "/auth/verify-otp"
    static let refreshToken = "/auth/refresh"
    static let logout = "/auth/logout"
    
    // MARK: - Restaurants
    static let restaurants = "/restaurants"
    static func restaurant(_ id: String) -> String { "/restaurants/\(id)" }
    static func restaurantMenu(_ id: String) -> String { "/restaurants/\(id)/menu" }
    
    // MARK: - Orders
    static let orders = "/orders"
    static func order(_ id: String) -> String { "/orders/\(id)" }
    static func rateOrder(_ id: String) -> String { "/orders/\(id)/rate" }
    
    // MARK: - Payments
    static let createPaymentIntent = "/payments/create-intent"
    
    // MARK: - User
    static let currentUser = "/users/me"
    static let userAddresses = "/users/me/addresses"
    static func deleteAddress(_ id: String) -> String { "/users/me/addresses/\(id)" }
    static let userPaymentMethods = "/users/me/payment-methods"
    static let favorites = "/users/me/favorites"
    static func toggleFavorite(_ restaurantId: String) -> String { "/users/me/favorites/\(restaurantId)" }
}
