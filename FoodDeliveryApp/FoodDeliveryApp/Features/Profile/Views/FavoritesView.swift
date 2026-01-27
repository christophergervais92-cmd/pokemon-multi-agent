import SwiftUI

struct FavoritesView: View {
    @StateObject private var viewModel = ProfileViewModel()
    
    var body: some View {
        Group {
            if viewModel.favoriteRestaurants.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "heart")
                        .font(.system(size: 60))
                        .foregroundStyle(.gray)
                    
                    Text("No favorites yet")
                        .font(.title2)
                        .fontWeight(.semibold)
                    
                    Text("Save your favorite restaurants for quick access")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding()
            } else {
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(viewModel.favoriteRestaurants) { restaurant in
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
        .navigationTitle("Favorites")
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Restaurant.self) { restaurant in
            RestaurantDetailView(restaurant: restaurant)
        }
        .task {
            await viewModel.loadFavorites()
        }
    }
}

#Preview {
    NavigationStack {
        FavoritesView()
            .environmentObject(CartManager())
    }
}
