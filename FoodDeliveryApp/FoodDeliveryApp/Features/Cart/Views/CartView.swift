import SwiftUI

struct CartView: View {
    @EnvironmentObject var cartManager: CartManager
    @Environment(\.dismiss) var dismiss
    @State private var showCheckout = false
    
    var body: some View {
        NavigationStack {
            if cartManager.items.isEmpty {
                EmptyCartView()
            } else {
                ScrollView {
                    VStack(spacing: 16) {
                        // Restaurant Header
                        if let restaurantName = cartManager.restaurantName {
                            HStack {
                                Image(systemName: "storefront")
                                    .foregroundStyle(.orange)
                                Text(restaurantName)
                                    .font(.headline)
                                Spacer()
                            }
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(12)
                        }
                        
                        // Cart Items
                        VStack(spacing: 0) {
                            ForEach(cartManager.items) { item in
                                CartItemRow(item: item)
                                
                                if item.id != cartManager.items.last?.id {
                                    Divider()
                                        .padding(.leading, 16)
                                }
                            }
                        }
                        .background(Color(.systemBackground))
                        .cornerRadius(12)
                        
                        // Add More Items Button
                        Button {
                            dismiss()
                        } label: {
                            HStack {
                                Image(systemName: "plus.circle")
                                Text("Add more items")
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(12)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                    .padding()
                }
                .safeAreaInset(edge: .bottom) {
                    // Checkout Button
                    VStack(spacing: 0) {
                        Divider()
                        
                        VStack(spacing: 12) {
                            HStack {
                                Text("Subtotal")
                                Spacer()
                                Text(cartManager.totalFormatted)
                                    .fontWeight(.semibold)
                            }
                            .font(.subheadline)
                            
                            Button {
                                showCheckout = true
                            } label: {
                                Text("Go to Checkout")
                                    .fontWeight(.semibold)
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(Color.orange)
                                    .foregroundColor(.white)
                                    .cornerRadius(12)
                            }
                        }
                        .padding()
                        .background(Color(.systemBackground))
                    }
                }
                .navigationDestination(isPresented: $showCheckout) {
                    CheckoutView()
                }
            }
        }
        .navigationTitle("Cart")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Close") {
                    dismiss()
                }
            }
            
            if !cartManager.items.isEmpty {
                ToolbarItem(placement: .destructiveAction) {
                    Button("Clear") {
                        cartManager.clearCart()
                    }
                    .foregroundStyle(.red)
                }
            }
        }
    }
}

struct EmptyCartView: View {
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "cart")
                .font(.system(size: 60))
                .foregroundStyle(.gray)
            
            Text("Your cart is empty")
                .font(.title2)
                .fontWeight(.semibold)
            
            Text("Add items from a restaurant to get started")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            
            Button {
                dismiss()
            } label: {
                Text("Browse Restaurants")
                    .fontWeight(.semibold)
                    .padding()
                    .background(Color.orange)
                    .foregroundColor(.white)
                    .cornerRadius(12)
            }
        }
        .padding()
    }
}

struct CartItemRow: View {
    let item: CartItem
    @EnvironmentObject var cartManager: CartManager
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Item Image
            if let imageUrl = item.menuItem.imageUrl {
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
            }
            
            // Item Details
            VStack(alignment: .leading, spacing: 4) {
                Text(item.menuItem.name)
                    .font(.headline)
                
                if !item.optionsSummary.isEmpty {
                    Text(item.optionsSummary)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                
                if let notes = item.specialNotes, !notes.isEmpty {
                    Text("Note: \(notes)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .italic()
                }
                
                Text(item.totalPriceFormatted)
                    .font(.subheadline)
                    .fontWeight(.semibold)
            }
            
            Spacer()
            
            // Quantity Controls
            VStack(spacing: 8) {
                Button {
                    cartManager.updateQuantity(for: item, quantity: item.quantity + 1)
                } label: {
                    Image(systemName: "plus.circle.fill")
                        .foregroundStyle(.orange)
                }
                
                Text("\(item.quantity)")
                    .font(.headline)
                    .frame(minWidth: 24)
                
                Button {
                    cartManager.updateQuantity(for: item, quantity: item.quantity - 1)
                } label: {
                    Image(systemName: item.quantity == 1 ? "trash.circle.fill" : "minus.circle.fill")
                        .foregroundStyle(item.quantity == 1 ? .red : .orange)
                }
            }
        }
        .padding()
    }
}

#Preview {
    CartView()
        .environmentObject(CartManager())
}
