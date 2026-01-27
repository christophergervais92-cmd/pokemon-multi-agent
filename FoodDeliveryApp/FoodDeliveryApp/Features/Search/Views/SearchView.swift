import SwiftUI

struct SearchView: View {
    @StateObject private var viewModel = SearchViewModel()
    @FocusState private var isSearchFocused: Bool
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Search Bar
                HStack(spacing: 12) {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(.gray)
                    
                    TextField("Search restaurants, cuisines, dishes...", text: $viewModel.searchQuery)
                        .focused($isSearchFocused)
                        .submitLabel(.search)
                    
                    if !viewModel.searchQuery.isEmpty {
                        Button {
                            viewModel.searchQuery = ""
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.gray)
                        }
                    }
                }
                .padding(12)
                .background(Color(.systemGray6))
                .cornerRadius(12)
                .padding()
                
                if viewModel.searchQuery.isEmpty {
                    // Recent Searches & Popular
                    ScrollView {
                        VStack(alignment: .leading, spacing: 24) {
                            // Recent Searches
                            if !viewModel.recentSearches.isEmpty {
                                VStack(alignment: .leading, spacing: 12) {
                                    HStack {
                                        Text("Recent Searches")
                                            .font(.headline)
                                        Spacer()
                                        Button("Clear") {
                                            viewModel.clearRecentSearches()
                                        }
                                        .font(.subheadline)
                                        .foregroundStyle(.orange)
                                    }
                                    
                                    ForEach(viewModel.recentSearches, id: \.self) { search in
                                        Button {
                                            viewModel.searchQuery = search
                                        } label: {
                                            HStack {
                                                Image(systemName: "clock")
                                                    .foregroundStyle(.gray)
                                                Text(search)
                                                    .foregroundStyle(.primary)
                                                Spacer()
                                                Image(systemName: "arrow.up.left")
                                                    .foregroundStyle(.gray)
                                            }
                                            .padding(.vertical, 8)
                                        }
                                    }
                                }
                            }
                            
                            // Popular Categories
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Popular Categories")
                                    .font(.headline)
                                
                                LazyVGrid(columns: [
                                    GridItem(.flexible()),
                                    GridItem(.flexible())
                                ], spacing: 12) {
                                    ForEach(RestaurantCategory.all.dropFirst(), id: \.id) { category in
                                        Button {
                                            viewModel.searchQuery = category.name
                                        } label: {
                                            HStack {
                                                Text(category.icon)
                                                    .font(.title2)
                                                Text(category.name)
                                                    .fontWeight(.medium)
                                            }
                                            .frame(maxWidth: .infinity)
                                            .padding()
                                            .background(Color(.systemGray6))
                                            .cornerRadius(12)
                                        }
                                        .buttonStyle(PlainButtonStyle())
                                    }
                                }
                            }
                        }
                        .padding()
                    }
                } else {
                    // Search Results
                    if viewModel.isLoading {
                        ProgressView()
                            .padding(.top, 40)
                        Spacer()
                    } else if viewModel.searchResults.isEmpty {
                        VStack(spacing: 16) {
                            Image(systemName: "magnifyingglass")
                                .font(.system(size: 50))
                                .foregroundStyle(.gray)
                            
                            Text("No results found")
                                .font(.headline)
                            
                            Text("Try searching for something else")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .padding(.top, 60)
                        Spacer()
                    } else {
                        ScrollView {
                            LazyVStack(spacing: 16) {
                                ForEach(viewModel.searchResults) { restaurant in
                                    NavigationLink(value: restaurant) {
                                        RestaurantCard(restaurant: restaurant)
                                    }
                                    .buttonStyle(PlainButtonStyle())
                                }
                            }
                            .padding()
                        }
                    }
                }
            }
            .navigationTitle("Search")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: Restaurant.self) { restaurant in
                RestaurantDetailView(restaurant: restaurant)
            }
            .onAppear {
                isSearchFocused = true
            }
        }
    }
}

#Preview {
    SearchView()
        .environmentObject(CartManager())
}
