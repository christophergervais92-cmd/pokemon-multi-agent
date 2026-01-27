import SwiftUI

struct OrderHistoryView: View {
    @StateObject private var viewModel = OrdersViewModel()
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    // Active Orders
                    if !viewModel.activeOrders.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Active Orders")
                                .font(.title2)
                                .fontWeight(.bold)
                                .padding(.horizontal)
                            
                            ForEach(viewModel.activeOrders) { order in
                                NavigationLink(value: order) {
                                    ActiveOrderCard(order: order)
                                }
                                .buttonStyle(PlainButtonStyle())
                            }
                            .padding(.horizontal)
                        }
                    }
                    
                    // Past Orders
                    VStack(alignment: .leading, spacing: 12) {
                        Text(viewModel.activeOrders.isEmpty ? "Your Orders" : "Past Orders")
                            .font(.title2)
                            .fontWeight(.bold)
                            .padding(.horizontal)
                        
                        if viewModel.isLoading {
                            ProgressView()
                                .padding(.top, 40)
                        } else if viewModel.pastOrders.isEmpty && viewModel.activeOrders.isEmpty {
                            EmptyOrdersView()
                        } else {
                            ForEach(viewModel.pastOrders) { order in
                                NavigationLink(value: order) {
                                    PastOrderCard(order: order)
                                }
                                .buttonStyle(PlainButtonStyle())
                            }
                            .padding(.horizontal)
                        }
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("Orders")
            .navigationDestination(for: Order.self) { order in
                if order.status.isActive {
                    OrderTrackingView(order: order)
                } else {
                    OrderDetailView(order: order)
                }
            }
            .refreshable {
                await viewModel.loadOrders()
            }
            .task {
                await viewModel.loadOrders()
            }
        }
    }
}

struct ActiveOrderCard: View {
    let order: Order
    
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                // Restaurant Info
                VStack(alignment: .leading, spacing: 4) {
                    Text(order.restaurant?.name ?? "Restaurant")
                        .font(.headline)
                    
                    Text(order.status.displayName)
                        .font(.subheadline)
                        .foregroundStyle(.orange)
                }
                
                Spacer()
                
                // ETA
                if let eta = order.estimatedDeliveryFormatted {
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("ETA")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(eta)
                            .font(.headline)
                            .foregroundStyle(.orange)
                    }
                }
            }
            
            // Progress Bar
            ProgressView(value: order.status.progressValue)
                .tint(.orange)
            
            // Items Preview
            HStack {
                Text("\(order.items.count) items")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                
                Spacer()
                
                Text("Track Order")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundStyle(.orange)
                
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 4)
    }
}

struct PastOrderCard: View {
    let order: Order
    
    var body: some View {
        HStack(spacing: 12) {
            // Restaurant Image
            if let imageUrl = order.restaurant?.imageUrl {
                AsyncImage(url: URL(string: imageUrl)) { image in
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                } placeholder: {
                    Rectangle()
                        .fill(Color(.systemGray5))
                }
                .frame(width: 60, height: 60)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            } else {
                Rectangle()
                    .fill(Color(.systemGray5))
                    .frame(width: 60, height: 60)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .overlay {
                        Image(systemName: "fork.knife")
                            .foregroundStyle(.gray)
                    }
            }
            
            VStack(alignment: .leading, spacing: 4) {
                Text(order.restaurant?.name ?? "Restaurant")
                    .font(.headline)
                
                Text("\(order.items.count) items • \(order.totalFormatted)")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                
                HStack(spacing: 4) {
                    Image(systemName: order.status == .delivered ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .foregroundStyle(order.status == .delivered ? .green : .red)
                        .font(.caption)
                    
                    Text(order.status.displayName)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    
                    Text("•")
                        .foregroundStyle(.secondary)
                    
                    Text(order.createdAtFormatted)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            
            Spacer()
            
            Image(systemName: "chevron.right")
                .foregroundStyle(.gray)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 4, x: 0, y: 2)
    }
}

struct EmptyOrdersView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "bag")
                .font(.system(size: 60))
                .foregroundStyle(.gray)
            
            Text("No orders yet")
                .font(.title2)
                .fontWeight(.semibold)
            
            Text("When you place your first order, it will appear here")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .padding(.top, 40)
    }
}

#Preview {
    OrderHistoryView()
        .environmentObject(CartManager())
}
