import Foundation

struct MenuItem: Codable, Identifiable, Equatable {
    let id: String
    let restaurantId: String
    let name: String
    let description: String?
    let price: Decimal
    let imageUrl: String?
    let category: String
    let isAvailable: Bool
    let isPopular: Bool
    let options: [MenuItemOption]?
    
    var priceFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: price as NSDecimalNumber) ?? "$\(price)"
    }
    
    static let preview = MenuItem(
        id: "1",
        restaurantId: "1",
        name: "Margherita Pizza",
        description: "Fresh tomatoes, mozzarella cheese, basil, and olive oil",
        price: 14.99,
        imageUrl: "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400",
        category: "Pizza",
        isAvailable: true,
        isPopular: true,
        options: [
            MenuItemOption(
                id: "size",
                name: "Size",
                type: .single,
                required: true,
                maxSelect: nil,
                choices: [
                    MenuItemOptionChoice(id: "small", name: "Small (10\")", price: 0),
                    MenuItemOptionChoice(id: "medium", name: "Medium (12\")", price: 3),
                    MenuItemOptionChoice(id: "large", name: "Large (14\")", price: 5)
                ]
            ),
            MenuItemOption(
                id: "toppings",
                name: "Extra Toppings",
                type: .multiple,
                required: false,
                maxSelect: 5,
                choices: [
                    MenuItemOptionChoice(id: "pepperoni", name: "Pepperoni", price: 1.50),
                    MenuItemOptionChoice(id: "mushrooms", name: "Mushrooms", price: 1),
                    MenuItemOptionChoice(id: "olives", name: "Olives", price: 1),
                    MenuItemOptionChoice(id: "bacon", name: "Bacon", price: 2)
                ]
            )
        ]
    )
    
    static let previews: [MenuItem] = [
        preview,
        MenuItem(
            id: "2",
            restaurantId: "1",
            name: "Pepperoni Pizza",
            description: "Classic pepperoni with mozzarella cheese",
            price: 16.99,
            imageUrl: "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=400",
            category: "Pizza",
            isAvailable: true,
            isPopular: true,
            options: nil
        ),
        MenuItem(
            id: "3",
            restaurantId: "1",
            name: "Caesar Salad",
            description: "Crisp romaine lettuce with parmesan and croutons",
            price: 9.99,
            imageUrl: nil,
            category: "Salads",
            isAvailable: true,
            isPopular: false,
            options: nil
        )
    ]
}

struct MenuItemOption: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let type: OptionType
    let required: Bool
    let maxSelect: Int?
    let choices: [MenuItemOptionChoice]
    
    enum OptionType: String, Codable {
        case single
        case multiple
    }
}

struct MenuItemOptionChoice: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let price: Decimal
    
    var priceText: String {
        if price == 0 {
            return ""
        }
        return "+$\(price)"
    }
}

struct MenuSection: Identifiable {
    let id: String
    let name: String
    let items: [MenuItem]
}
