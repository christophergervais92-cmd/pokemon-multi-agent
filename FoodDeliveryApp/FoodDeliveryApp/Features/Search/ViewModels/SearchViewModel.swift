import Foundation
import Combine

@MainActor
class SearchViewModel: ObservableObject {
    @Published var searchQuery = ""
    @Published var searchResults: [Restaurant] = []
    @Published var recentSearches: [String] = []
    @Published var isLoading = false
    
    private var cancellables = Set<AnyCancellable>()
    private let recentSearchesKey = "recentSearches"
    
    init() {
        loadRecentSearches()
        setupSearchDebounce()
    }
    
    private func setupSearchDebounce() {
        $searchQuery
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .removeDuplicates()
            .sink { [weak self] query in
                Task {
                    await self?.search(query: query)
                }
            }
            .store(in: &cancellables)
    }
    
    func search(query: String) async {
        guard !query.isEmpty else {
            searchResults = []
            return
        }
        
        isLoading = true
        
        do {
            struct SearchResponse: Decodable {
                let restaurants: [Restaurant]
                let total: Int
                let hasMore: Bool
            }
            
            let response: SearchResponse = try await APIClient.shared.request(
                endpoint: Endpoints.restaurants,
                queryParams: ["search": query, "limit": "20"]
            )
            
            searchResults = response.restaurants
            saveRecentSearch(query)
        } catch {
            // Use filtered preview data for demo
            searchResults = Restaurant.previews.filter {
                $0.name.localizedCaseInsensitiveContains(query) ||
                $0.category.localizedCaseInsensitiveContains(query)
            }
        }
        
        isLoading = false
    }
    
    private func loadRecentSearches() {
        recentSearches = UserDefaults.standard.stringArray(forKey: recentSearchesKey) ?? []
    }
    
    private func saveRecentSearch(_ query: String) {
        var searches = recentSearches
        searches.removeAll { $0.lowercased() == query.lowercased() }
        searches.insert(query, at: 0)
        searches = Array(searches.prefix(10))
        recentSearches = searches
        UserDefaults.standard.set(searches, forKey: recentSearchesKey)
    }
    
    func clearRecentSearches() {
        recentSearches = []
        UserDefaults.standard.removeObject(forKey: recentSearchesKey)
    }
}
