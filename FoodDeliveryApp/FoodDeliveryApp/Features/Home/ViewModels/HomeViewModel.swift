import Foundation
import Combine
import CoreLocation

@MainActor
class HomeViewModel: ObservableObject {
    @Published var restaurants: [Restaurant] = []
    @Published var featuredRestaurants: [Restaurant] = []
    @Published var selectedCategory: RestaurantCategory = RestaurantCategory.all.first!
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var searchQuery = ""
    @Published var sortBy: SortOption = .rating
    
    private var cancellables = Set<AnyCancellable>()
    private var currentPage = 0
    private var hasMore = true
    private let pageSize = 20
    
    enum SortOption: String, CaseIterable {
        case rating = "rating"
        case deliveryTime = "deliveryTime"
        case distance = "distance"
        case deliveryFee = "deliveryFee"
        
        var displayName: String {
            switch self {
            case .rating: return "Top Rated"
            case .deliveryTime: return "Fastest"
            case .distance: return "Nearest"
            case .deliveryFee: return "Lowest Fee"
            }
        }
    }
    
    init() {
        setupSearchDebounce()
    }
    
    private func setupSearchDebounce() {
        $searchQuery
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .removeDuplicates()
            .sink { [weak self] _ in
                Task {
                    await self?.refreshRestaurants()
                }
            }
            .store(in: &cancellables)
    }
    
    func loadRestaurants(userLocation: CLLocation? = nil) async {
        guard !isLoading else { return }
        
        isLoading = true
        errorMessage = nil
        
        do {
            var queryParams: [String: String] = [
                "sortBy": sortBy.rawValue,
                "limit": String(pageSize),
                "offset": String(currentPage * pageSize)
            ]
            
            if selectedCategory.id != "all" {
                queryParams["category"] = selectedCategory.name
            }
            
            if !searchQuery.isEmpty {
                queryParams["search"] = searchQuery
            }
            
            if let location = userLocation {
                queryParams["latitude"] = String(location.coordinate.latitude)
                queryParams["longitude"] = String(location.coordinate.longitude)
            }
            
            struct RestaurantsResponse: Decodable {
                let restaurants: [Restaurant]
                let total: Int
                let hasMore: Bool
            }
            
            let response: RestaurantsResponse = try await APIClient.shared.request(
                endpoint: Endpoints.restaurants,
                queryParams: queryParams
            )
            
            if currentPage == 0 {
                restaurants = response.restaurants
            } else {
                restaurants.append(contentsOf: response.restaurants)
            }
            
            hasMore = response.hasMore
            
            // Get featured (top rated) for carousel
            if currentPage == 0 {
                featuredRestaurants = Array(restaurants.filter { $0.rating >= 4.5 }.prefix(5))
            }
        } catch {
            errorMessage = error.localizedDescription
            // Use preview data for demo
            if currentPage == 0 {
                restaurants = Restaurant.previews
                featuredRestaurants = Array(Restaurant.previews.prefix(3))
            }
        }
        
        isLoading = false
    }
    
    func refreshRestaurants() async {
        currentPage = 0
        hasMore = true
        await loadRestaurants()
    }
    
    func loadMoreIfNeeded(currentItem: Restaurant) async {
        guard hasMore, !isLoading else { return }
        
        let thresholdIndex = restaurants.index(restaurants.endIndex, offsetBy: -5)
        if let itemIndex = restaurants.firstIndex(where: { $0.id == currentItem.id }),
           itemIndex >= thresholdIndex {
            currentPage += 1
            await loadRestaurants()
        }
    }
    
    func selectCategory(_ category: RestaurantCategory) {
        selectedCategory = category
        Task {
            await refreshRestaurants()
        }
    }
    
    func setSortOption(_ option: SortOption) {
        sortBy = option
        Task {
            await refreshRestaurants()
        }
    }
}
