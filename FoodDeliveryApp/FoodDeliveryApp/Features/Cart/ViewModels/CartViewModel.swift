import Foundation
import Combine

// The CartManager already handles all cart functionality
// This file provides any additional cart-related utilities

extension CartManager {
    func canCheckout(minimumOrder: Decimal) -> Bool {
        subtotal >= minimumOrder
    }
    
    func getCartSummary() -> CartSummary {
        CartSummary(
            itemCount: itemCount,
            subtotal: subtotal,
            restaurantId: restaurantId,
            restaurantName: restaurantName
        )
    }
}

struct CartSummary {
    let itemCount: Int
    let subtotal: Decimal
    let restaurantId: String?
    let restaurantName: String?
    
    var subtotalFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: subtotal as NSDecimalNumber) ?? "$\(subtotal)"
    }
}
