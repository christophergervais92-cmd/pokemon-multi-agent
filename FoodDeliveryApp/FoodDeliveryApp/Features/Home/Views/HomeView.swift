import SwiftUI

struct HomeView: View {
    @StateObject private var viewModel = HomeViewModel()
    @EnvironmentObject var locationManager: LocationManager
    @State private var showSortOptions = false
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 0) {
                    // Location Header
                    LocationHeaderView()
                    
                    // Search Bar
                    SearchBarView(text: $viewModel.searchQuery)
                        .padding(.horizontal)
                        .padding(.bottom, 16)
                    
                    // Category Filter
                    CategoryFilterView(
                        categories: RestaurantCategory.all,
                        selectedCategory: viewModel.selectedCategory,
                        onSelect: viewModel.selectCategory
                    )
                    .padding(.bottom, 16)
                    
                    // Featured Restaurants Carousel
                    if !viewModel.featuredRestaurants.isEmpty && viewModel.searchQuery.isEmpty {
                        FeaturedCarouselView(restaurants: viewModel.featuredRestaurants)
                            .padding(.bottom, 24)
                    }
                    
                    // Sort Options
                    HStack {
                        Text("Restaurants")
                            .font(.title2)
                            .fontWeight(.bold)
                        
                        Spacer()
                        
                        Button {
                            showSortOptions = true
                        } label: {
                            HStack(spacing: 4) {
                                Text(viewModel.sortBy.displayName)
                                    .font(.subheadline)
                                Image(systemName: "chevron.down")
                                    .font(.caption)
                            }
                            .foregroundStyle(.orange)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 12)
                    
                    // Restaurant List
                    if viewModel.isLoading && viewModel.restaurants.isEmpty {
                        LoadingRestaurantsView()
                    } else if viewModel.restaurants.isEmpty {
                        EmptyStateView(
                            icon: "fork.knife",
                            title: "No restaurants found",
                            message: "Try adjusting your filters or search query"
                        )
                        .padding(.top, 40)
                    } else {
                        LazyVStack(spacing: 16) {
                            ForEach(viewModel.restaurants) { restaurant in
                                NavigationLink(value: restaurant) {
                                    RestaurantCard(restaurant: restaurant)
                                }
                                .buttonStyle(PlainButtonStyle())
                                .onAppear {
                                    Task {
                                        await viewModel.loadMoreIfNeeded(currentItem: restaurant)
                                    }
                                }
                            }
                            
                            if viewModel.isLoading {
                                ProgressView()
                                    .padding()
                            }
                        }
                        .padding(.horizontal)
                    }
                }
                .padding(.bottom, 100) // Space for cart button
            }
            .navigationDestination(for: Restaurant.self) { restaurant in
                RestaurantDetailView(restaurant: restaurant)
            }
            .refreshable {
                await viewModel.refreshRestaurants()
            }
            .confirmationDialog("Sort By", isPresented: $showSortOptions) {
                ForEach(HomeViewModel.SortOption.allCases, id: \.self) { option in
                    Button(option.displayName) {
                        viewModel.setSortOption(option)
                    }
                }
            }
            .task {
                await viewModel.loadRestaurants(userLocation: locationManager.currentLocation)
            }
        }
    }
}

struct LocationHeaderView: View {
    @EnvironmentObject var locationManager: LocationManager
    @State private var showAddressPicker = false
    
    var body: some View {
        Button {
            showAddressPicker = true
        } label: {
            HStack {
                Image(systemName: "location.fill")
                    .foregroundStyle(.orange)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text("Deliver to")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    
                    HStack(spacing: 4) {
                        Text(locationManager.currentAddress ?? "Set delivery address")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundStyle(.primary)
                            .lineLimit(1)
                        
                        Image(systemName: "chevron.down")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                
                Spacer()
            }
            .padding()
            .background(Color(.systemBackground))
        }
        .sheet(isPresented: $showAddressPicker) {
            AddressPickerView()
        }
    }
}

struct SearchBarView: View {
    @Binding var text: String
    @FocusState private var isFocused: Bool
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.gray)
            
            TextField("Search restaurants or dishes", text: $text)
                .focused($isFocused)
            
            if !text.isEmpty {
                Button {
                    text = ""
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.gray)
                }
            }
        }
        .padding(12)
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

struct CategoryFilterView: View {
    let categories: [RestaurantCategory]
    let selectedCategory: RestaurantCategory
    let onSelect: (RestaurantCategory) -> Void
    
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                ForEach(categories) { category in
                    CategoryChip(
                        category: category,
                        isSelected: category.id == selectedCategory.id,
                        onTap: { onSelect(category) }
                    )
                }
            }
            .padding(.horizontal)
        }
    }
}

struct CategoryChip: View {
    let category: RestaurantCategory
    let isSelected: Bool
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 6) {
                if category.icon.count == 1 {
                    Text(category.icon)
                } else {
                    Image(systemName: category.icon)
                }
                Text(category.name)
                    .font(.subheadline)
                    .fontWeight(.medium)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(isSelected ? Color.orange : Color(.systemGray6))
            .foregroundColor(isSelected ? .white : .primary)
            .cornerRadius(20)
        }
    }
}

struct FeaturedCarouselView: View {
    let restaurants: [Restaurant]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Featured")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.horizontal)
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 16) {
                    ForEach(restaurants) { restaurant in
                        NavigationLink(value: restaurant) {
                            FeaturedRestaurantCard(restaurant: restaurant)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
                .padding(.horizontal)
            }
        }
    }
}

struct FeaturedRestaurantCard: View {
    let restaurant: Restaurant
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Image
            AsyncImage(url: URL(string: restaurant.coverImageUrl ?? restaurant.imageUrl ?? "")) { image in
                image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
            } placeholder: {
                Rectangle()
                    .fill(Color(.systemGray5))
                    .overlay {
                        Image(systemName: "photo")
                            .foregroundStyle(.gray)
                    }
            }
            .frame(width: 280, height: 140)
            .clipped()
            
            // Details
            VStack(alignment: .leading, spacing: 4) {
                Text(restaurant.name)
                    .font(.headline)
                    .lineLimit(1)
                
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .foregroundStyle(.yellow)
                        .font(.caption)
                    Text(String(format: "%.1f", restaurant.rating))
                        .font(.caption)
                        .fontWeight(.medium)
                    Text("(\(restaurant.reviewCount))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text("•")
                        .foregroundStyle(.secondary)
                    Text(restaurant.deliveryTimeText)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(12)
        }
        .frame(width: 280)
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 4)
    }
}

struct LoadingRestaurantsView: View {
    var body: some View {
        VStack(spacing: 16) {
            ForEach(0..<3, id: \.self) { _ in
                RestaurantCardSkeleton()
            }
        }
        .padding(.horizontal)
    }
}

struct RestaurantCardSkeleton: View {
    @State private var isAnimating = false
    
    var body: some View {
        HStack(spacing: 12) {
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemGray5))
                .frame(width: 100, height: 100)
            
            VStack(alignment: .leading, spacing: 8) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(height: 20)
                    .frame(maxWidth: 150)
                
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(height: 14)
                    .frame(maxWidth: 100)
                
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(height: 14)
                    .frame(maxWidth: 80)
            }
            
            Spacer()
        }
        .opacity(isAnimating ? 0.5 : 1)
        .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: isAnimating)
        .onAppear {
            isAnimating = true
        }
    }
}

struct EmptyStateView: View {
    let icon: String
    let title: String
    let message: String
    
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 50))
                .foregroundStyle(.gray)
            
            Text(title)
                .font(.headline)
            
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
    }
}

#Preview {
    HomeView()
        .environmentObject(AuthManager())
        .environmentObject(CartManager())
        .environmentObject(LocationManager())
}
