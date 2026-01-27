import Foundation
import Combine

@MainActor
class RestaurantViewModel: ObservableObject {
    @Published var restaurant: Restaurant
    @Published var menuSections: [MenuSection] = []
    @Published var isLoading = false
    @Published var isFavorite = false
    @Published var errorMessage: String?
    
    init(restaurant: Restaurant) {
        self.restaurant = restaurant
    }
    
    func loadMenu() async {
        isLoading = true
        
        do {
            struct MenuCategory: Decodable {
                let category: String
                let items: [MenuItem]
            }
            
            let categories: [MenuCategory] = try await APIClient.shared.request(
                endpoint: Endpoints.restaurantMenu(restaurant.id)
            )
            
            menuSections = categories.map { MenuSection(id: $0.category, name: $0.category, items: $0.items) }
        } catch {
            // Use preview data for demo
            menuSections = [
                MenuSection(id: "Popular", name: "Popular Items", items: [MenuItem.preview]),
                MenuSection(id: "Pizza", name: "Pizza", items: MenuItem.previews),
                MenuSection(id: "Salads", name: "Salads", items: [MenuItem.previews[2]])
            ]
        }
        
        isLoading = false
    }
    
    func loadFullRestaurant() async {
        do {
            struct RestaurantResponse: Decodable {
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
                let isFavorite: Bool?
                let menuItems: [MenuItem]?
            }
            
            let response: RestaurantResponse = try await APIClient.shared.request(
                endpoint: Endpoints.restaurant(restaurant.id)
            )
            
            isFavorite = response.isFavorite ?? false
            
            // Group menu items by category
            if let items = response.menuItems {
                let grouped = Dictionary(grouping: items, by: { $0.category })
                menuSections = grouped.map { MenuSection(id: $0.key, name: $0.key, items: $0.value) }
                    .sorted { $0.name < $1.name }
            }
        } catch {
            // Already have basic restaurant info
            await loadMenu()
        }
    }
    
    func toggleFavorite() async {
        do {
            struct FavoriteResponse: Decodable {
                let isFavorite: Bool
            }
            
            let response: FavoriteResponse = try await APIClient.shared.request(
                endpoint: Endpoints.toggleFavorite(restaurant.id),
                method: .POST
            )
            
            isFavorite = response.isFavorite
        } catch {
            // Toggle locally for demo
            isFavorite.toggle()
        }
    }
}
