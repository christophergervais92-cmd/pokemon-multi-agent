import Foundation

struct CartItem: Identifiable, Equatable {
    let id: String
    let menuItem: MenuItem
    var quantity: Int
    var selectedOptions: [String: [MenuItemOptionChoice]]
    var specialNotes: String?
    
    var unitPrice: Decimal {
        var price = menuItem.price
        for (_, choices) in selectedOptions {
            for choice in choices {
                price += choice.price
            }
        }
        return price
    }
    
    var totalPrice: Decimal {
        return unitPrice * Decimal(quantity)
    }
    
    var totalPriceFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: totalPrice as NSDecimalNumber) ?? "$\(totalPrice)"
    }
    
    var optionsSummary: String {
        var parts: [String] = []
        for (_, choices) in selectedOptions.sorted(by: { $0.key < $1.key }) {
            let names = choices.map { $0.name }
            parts.append(contentsOf: names)
        }
        return parts.joined(separator: ", ")
    }
    
    static func == (lhs: CartItem, rhs: CartItem) -> Bool {
        lhs.id == rhs.id &&
        lhs.menuItem.id == rhs.menuItem.id &&
        lhs.quantity == rhs.quantity &&
        lhs.specialNotes == rhs.specialNotes
    }
}

@MainActor
class CartManager: ObservableObject {
    @Published var items: [CartItem] = []
    @Published var restaurantId: String?
    @Published var restaurantName: String?
    
    var subtotal: Decimal {
        items.reduce(0) { $0 + $1.totalPrice }
    }
    
    var totalFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: subtotal as NSDecimalNumber) ?? "$\(subtotal)"
    }
    
    var itemCount: Int {
        items.reduce(0) { $0 + $1.quantity }
    }
    
    func addItem(_ menuItem: MenuItem, quantity: Int = 1, options: [String: [MenuItemOptionChoice]] = [:], notes: String? = nil, fromRestaurant restaurant: Restaurant) {
        // Check if adding from different restaurant
        if let currentRestaurantId = restaurantId, currentRestaurantId != restaurant.id {
            // Clear cart if from different restaurant
            clearCart()
        }
        
        restaurantId = restaurant.id
        restaurantName = restaurant.name
        
        // Check if item with same options exists
        if let index = items.firstIndex(where: { 
            $0.menuItem.id == menuItem.id && 
            $0.selectedOptions == options &&
            $0.specialNotes == notes
        }) {
            items[index].quantity += quantity
        } else {
            let cartItem = CartItem(
                id: UUID().uuidString,
                menuItem: menuItem,
                quantity: quantity,
                selectedOptions: options,
                specialNotes: notes
            )
            items.append(cartItem)
        }
    }
    
    func updateQuantity(for item: CartItem, quantity: Int) {
        if let index = items.firstIndex(where: { $0.id == item.id }) {
            if quantity <= 0 {
                items.remove(at: index)
                if items.isEmpty {
                    restaurantId = nil
                    restaurantName = nil
                }
            } else {
                items[index].quantity = quantity
            }
        }
    }
    
    func removeItem(_ item: CartItem) {
        items.removeAll { $0.id == item.id }
        if items.isEmpty {
            restaurantId = nil
            restaurantName = nil
        }
    }
    
    func clearCart() {
        items = []
        restaurantId = nil
        restaurantName = nil
    }
}
