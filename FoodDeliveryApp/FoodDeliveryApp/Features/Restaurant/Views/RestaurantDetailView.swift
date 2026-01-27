import SwiftUI

struct RestaurantDetailView: View {
    let restaurant: Restaurant
    @StateObject private var viewModel: RestaurantViewModel
    @EnvironmentObject var cartManager: CartManager
    @Environment(\.dismiss) var dismiss
    
    @State private var selectedItem: MenuItem?
    @State private var showInfo = false
    
    init(restaurant: Restaurant) {
        self.restaurant = restaurant
        self._viewModel = StateObject(wrappedValue: RestaurantViewModel(restaurant: restaurant))
    }
    
    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                // Header Image
                RestaurantHeaderView(
                    restaurant: restaurant,
                    isFavorite: viewModel.isFavorite,
                    onFavoriteToggle: {
                        Task { await viewModel.toggleFavorite() }
                    },
                    onInfoTap: { showInfo = true }
                )
                
                // Restaurant Info
                RestaurantInfoBar(restaurant: restaurant)
                
                // Menu
                if viewModel.isLoading {
                    ProgressView()
                        .padding(.top, 40)
                } else if viewModel.menuSections.isEmpty {
                    EmptyStateView(
                        icon: "menucard",
                        title: "Menu unavailable",
                        message: "This restaurant's menu is currently unavailable"
                    )
                    .padding(.top, 40)
                } else {
                    LazyVStack(spacing: 0, pinnedViews: [.sectionHeaders]) {
                        ForEach(viewModel.menuSections) { section in
                            Section {
                                ForEach(section.items) { item in
                                    MenuItemRow(item: item) {
                                        selectedItem = item
                                    }
                                    
                                    if item.id != section.items.last?.id {
                                        Divider()
                                            .padding(.leading, 16)
                                    }
                                }
                            } header: {
                                MenuSectionHeader(title: section.name)
                            }
                        }
                    }
                }
            }
            .padding(.bottom, 100) // Space for cart button
        }
        .ignoresSafeArea(edges: .top)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "arrow.left")
                        .fontWeight(.semibold)
                        .foregroundStyle(.white)
                        .padding(10)
                        .background(.black.opacity(0.5))
                        .clipShape(Circle())
                }
            }
        }
        .sheet(item: $selectedItem) { item in
            ItemCustomizationSheet(
                item: item,
                restaurant: restaurant
            )
        }
        .sheet(isPresented: $showInfo) {
            RestaurantInfoSheet(restaurant: restaurant)
        }
        .task {
            await viewModel.loadFullRestaurant()
        }
    }
}

struct RestaurantHeaderView: View {
    let restaurant: Restaurant
    let isFavorite: Bool
    let onFavoriteToggle: () -> Void
    let onInfoTap: () -> Void
    
    var body: some View {
        ZStack(alignment: .bottomLeading) {
            // Cover Image
            AsyncImage(url: URL(string: restaurant.coverImageUrl ?? restaurant.imageUrl ?? "")) { image in
                image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
            } placeholder: {
                Rectangle()
                    .fill(Color(.systemGray4))
            }
            .frame(height: 200)
            .clipped()
            
            // Gradient Overlay
            LinearGradient(
                colors: [.clear, .black.opacity(0.7)],
                startPoint: .top,
                endPoint: .bottom
            )
            
            // Restaurant Name and Actions
            HStack(alignment: .bottom) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(restaurant.name)
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundStyle(.white)
                    
                    Text(restaurant.category)
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.9))
                }
                
                Spacer()
                
                HStack(spacing: 12) {
                    Button(action: onFavoriteToggle) {
                        Image(systemName: isFavorite ? "heart.fill" : "heart")
                            .foregroundStyle(isFavorite ? .red : .white)
                            .font(.title3)
                            .padding(10)
                            .background(.white.opacity(0.2))
                            .clipShape(Circle())
                    }
                    
                    Button(action: onInfoTap) {
                        Image(systemName: "info.circle")
                            .foregroundStyle(.white)
                            .font(.title3)
                            .padding(10)
                            .background(.white.opacity(0.2))
                            .clipShape(Circle())
                    }
                }
            }
            .padding()
        }
    }
}

struct RestaurantInfoBar: View {
    let restaurant: Restaurant
    
    var body: some View {
        HStack(spacing: 24) {
            // Rating
            VStack(spacing: 4) {
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .foregroundStyle(.yellow)
                    Text(String(format: "%.1f", restaurant.rating))
                        .fontWeight(.semibold)
                }
                Text("\(restaurant.reviewCount) reviews")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            
            Divider()
                .frame(height: 40)
            
            // Delivery Time
            VStack(spacing: 4) {
                HStack(spacing: 4) {
                    Image(systemName: "clock")
                        .foregroundStyle(.orange)
                    Text(restaurant.deliveryTimeText)
                        .fontWeight(.semibold)
                }
                Text("Delivery")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            
            Divider()
                .frame(height: 40)
            
            // Delivery Fee
            VStack(spacing: 4) {
                Text(restaurant.deliveryFeeText)
                    .fontWeight(.semibold)
                    .foregroundStyle(restaurant.deliveryFee == 0 ? .green : .primary)
                Text("Fee")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(Color(.systemBackground))
    }
}

struct MenuSectionHeader: View {
    let title: String
    
    var body: some View {
        HStack {
            Text(title)
                .font(.title3)
                .fontWeight(.bold)
            Spacer()
        }
        .padding()
        .background(Color(.systemBackground))
    }
}

struct MenuItemRow: View {
    let item: MenuItem
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(item.name)
                            .font(.headline)
                        
                        if item.isPopular {
                            Text("Popular")
                                .font(.caption2)
                                .fontWeight(.medium)
                                .foregroundStyle(.orange)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.orange.opacity(0.1))
                                .cornerRadius(4)
                        }
                    }
                    
                    if let description = item.description {
                        Text(description)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    
                    Text(item.priceFormatted)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                Spacer()
                
                if let imageUrl = item.imageUrl {
                    AsyncImage(url: URL(string: imageUrl)) { image in
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    } placeholder: {
                        Rectangle()
                            .fill(Color(.systemGray5))
                    }
                    .frame(width: 80, height: 80)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
            .padding()
        }
        .buttonStyle(PlainButtonStyle())
    }
}

struct RestaurantInfoSheet: View {
    let restaurant: Restaurant
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            List {
                Section("About") {
                    if let description = restaurant.description {
                        Text(description)
                    }
                }
                
                Section("Location") {
                    HStack {
                        Image(systemName: "mappin.circle.fill")
                            .foregroundStyle(.red)
                        Text(restaurant.address)
                    }
                }
                
                Section("Hours") {
                    HStack {
                        Image(systemName: "clock.fill")
                            .foregroundStyle(.orange)
                        if let open = restaurant.openingTime, let close = restaurant.closingTime {
                            Text("\(open) - \(close)")
                        } else {
                            Text("Hours not available")
                        }
                    }
                    
                    HStack {
                        Text("Status")
                        Spacer()
                        Text(restaurant.isOpen ? "Open" : "Closed")
                            .foregroundStyle(restaurant.isOpen ? .green : .red)
                    }
                }
                
                Section("Delivery") {
                    HStack {
                        Text("Delivery Time")
                        Spacer()
                        Text(restaurant.deliveryTimeText)
                    }
                    
                    HStack {
                        Text("Delivery Fee")
                        Spacer()
                        Text(restaurant.deliveryFeeText)
                    }
                    
                    HStack {
                        Text("Minimum Order")
                        Spacer()
                        Text("$\(restaurant.minimumOrder)")
                    }
                }
            }
            .navigationTitle(restaurant.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}

#Preview {
    NavigationStack {
        RestaurantDetailView(restaurant: .preview)
            .environmentObject(CartManager())
    }
}
