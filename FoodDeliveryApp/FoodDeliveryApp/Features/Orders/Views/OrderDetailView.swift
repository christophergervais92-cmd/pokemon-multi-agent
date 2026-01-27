import SwiftUI

struct OrderDetailView: View {
    let order: Order
    @State private var showRatingSheet = false
    @State private var hasRated = false
    @EnvironmentObject var cartManager: CartManager
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Status Header
                OrderStatusHeader(order: order)
                
                // Restaurant Info
                NavigationLink(value: order.restaurant) {
                    HStack {
                        if let imageUrl = order.restaurant?.imageUrl {
                            AsyncImage(url: URL(string: imageUrl)) { image in
                                image
                                    .resizable()
                                    .aspectRatio(contentMode: .fill)
                            } placeholder: {
                                Rectangle()
                                    .fill(Color(.systemGray5))
                            }
                            .frame(width: 50, height: 50)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text(order.restaurant?.name ?? "Restaurant")
                                .font(.headline)
                            Text("View restaurant")
                                .font(.caption)
                                .foregroundStyle(.orange)
                        }
                        
                        Spacer()
                        
                        Image(systemName: "chevron.right")
                            .foregroundStyle(.gray)
                    }
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
                .buttonStyle(PlainButtonStyle())
                
                // Order Items
                VStack(alignment: .leading, spacing: 12) {
                    Text("Items Ordered")
                        .font(.headline)
                    
                    VStack(spacing: 0) {
                        ForEach(order.items) { item in
                            HStack {
                                Text("\(item.quantity)x")
                                    .foregroundStyle(.secondary)
                                    .frame(width: 30, alignment: .leading)
                                
                                Text(item.name)
                                
                                Spacer()
                                
                                Text(item.totalPriceFormatted)
                            }
                            .padding(.vertical, 8)
                            
                            if item.id != order.items.last?.id {
                                Divider()
                            }
                        }
                    }
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
                
                // Delivery Address
                VStack(alignment: .leading, spacing: 12) {
                    Text("Delivered To")
                        .font(.headline)
                    
                    HStack {
                        Image(systemName: "location.fill")
                            .foregroundStyle(.orange)
                        Text(order.deliveryAddress.formatted)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
                
                // Price Breakdown
                VStack(alignment: .leading, spacing: 12) {
                    Text("Payment Summary")
                        .font(.headline)
                    
                    VStack(spacing: 8) {
                        PriceRow(label: "Subtotal", value: order.subtotal)
                        PriceRow(label: "Delivery Fee", value: order.deliveryFee)
                        PriceRow(label: "Service Fee", value: order.serviceFee)
                        if order.tip > 0 {
                            PriceRow(label: "Tip", value: order.tip)
                        }
                        if order.discount > 0 {
                            PriceRow(label: "Discount", value: -order.discount)
                        }
                        Divider()
                        PriceRow(label: "Total", value: order.total, isTotal: true)
                    }
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
                
                // Rate Order (if delivered and not rated)
                if order.status == .delivered && !hasRated {
                    Button {
                        showRatingSheet = true
                    } label: {
                        HStack {
                            Image(systemName: "star")
                            Text("Rate this order")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.orange)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                    }
                }
                
                // Reorder Button
                Button {
                    // Reorder logic
                } label: {
                    HStack {
                        Image(systemName: "arrow.clockwise")
                        Text("Reorder")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color(.systemGray6))
                    .foregroundColor(.primary)
                    .cornerRadius(12)
                }
                
                // Help
                Button {
                    // Help action
                } label: {
                    HStack {
                        Image(systemName: "questionmark.circle")
                        Text("Get help with this order")
                    }
                    .foregroundStyle(.orange)
                }
                .padding(.top, 8)
            }
            .padding()
        }
        .navigationTitle("Order #\(String(order.id.prefix(8)))")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showRatingSheet) {
            RateOrderSheet(order: order, hasRated: $hasRated)
        }
    }
}

struct OrderStatusHeader: View {
    let order: Order
    
    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: order.status == .delivered ? "checkmark.circle.fill" : "xmark.circle.fill")
                .font(.system(size: 50))
                .foregroundStyle(order.status == .delivered ? .green : .red)
            
            Text(order.status == .delivered ? "Order Delivered" : "Order Cancelled")
                .font(.title2)
                .fontWeight(.bold)
            
            Text(order.createdAtFormatted)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(16)
    }
}

struct RateOrderSheet: View {
    let order: Order
    @Binding var hasRated: Bool
    @Environment(\.dismiss) var dismiss
    
    @State private var rating = 0
    @State private var comment = ""
    @State private var isSubmitting = false
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                // Restaurant Info
                VStack(spacing: 8) {
                    Text("How was your order from")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    
                    Text(order.restaurant?.name ?? "Restaurant")
                        .font(.title2)
                        .fontWeight(.bold)
                }
                .padding(.top)
                
                // Star Rating
                HStack(spacing: 8) {
                    ForEach(1...5, id: \.self) { star in
                        Button {
                            rating = star
                        } label: {
                            Image(systemName: star <= rating ? "star.fill" : "star")
                                .font(.system(size: 40))
                                .foregroundStyle(star <= rating ? .yellow : .gray)
                        }
                    }
                }
                
                // Rating Label
                if rating > 0 {
                    Text(ratingLabel)
                        .font(.headline)
                        .foregroundStyle(.orange)
                }
                
                // Comment
                VStack(alignment: .leading, spacing: 8) {
                    Text("Leave a comment (optional)")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    
                    TextField("Share your experience...", text: $comment, axis: .vertical)
                        .lineLimit(3...6)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                }
                .padding(.horizontal)
                
                Spacer()
                
                // Submit Button
                Button {
                    submitRating()
                } label: {
                    HStack {
                        if isSubmitting {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text("Submit Review")
                                .fontWeight(.semibold)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(rating > 0 ? Color.orange : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                .disabled(rating == 0 || isSubmitting)
                .padding()
            }
            .navigationTitle("Rate Order")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }
    
    private var ratingLabel: String {
        switch rating {
        case 1: return "Poor"
        case 2: return "Fair"
        case 3: return "Good"
        case 4: return "Very Good"
        case 5: return "Excellent!"
        default: return ""
        }
    }
    
    private func submitRating() {
        isSubmitting = true
        
        Task {
            // API call would go here
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            
            hasRated = true
            dismiss()
        }
    }
}

#Preview {
    NavigationStack {
        OrderDetailView(order: .preview)
            .environmentObject(CartManager())
    }
}
