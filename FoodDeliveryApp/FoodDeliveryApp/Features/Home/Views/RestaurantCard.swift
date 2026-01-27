import SwiftUI

struct RestaurantCard: View {
    let restaurant: Restaurant
    
    var body: some View {
        HStack(spacing: 12) {
            // Restaurant Image
            AsyncImage(url: URL(string: restaurant.imageUrl ?? "")) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                case .failure:
                    placeholderImage
                case .empty:
                    placeholderImage
                @unknown default:
                    placeholderImage
                }
            }
            .frame(width: 100, height: 100)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            
            // Restaurant Info
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(restaurant.name)
                        .font(.headline)
                        .lineLimit(1)
                    
                    Spacer()
                    
                    if !restaurant.isOpen {
                        Text("Closed")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundStyle(.red)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.red.opacity(0.1))
                            .cornerRadius(4)
                    }
                }
                
                Text(restaurant.category)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                
                HStack(spacing: 8) {
                    // Rating
                    HStack(spacing: 2) {
                        Image(systemName: "star.fill")
                            .foregroundStyle(.yellow)
                        Text(String(format: "%.1f", restaurant.rating))
                            .fontWeight(.medium)
                        Text("(\(restaurant.reviewCount))")
                            .foregroundStyle(.secondary)
                    }
                    .font(.caption)
                    
                    Text("•")
                        .foregroundStyle(.secondary)
                    
                    // Delivery Time
                    HStack(spacing: 2) {
                        Image(systemName: "clock")
                            .foregroundStyle(.secondary)
                        Text(restaurant.deliveryTimeText)
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
                
                // Delivery Fee
                Text(restaurant.deliveryFeeText)
                    .font(.caption)
                    .foregroundStyle(restaurant.deliveryFee == 0 ? .green : .secondary)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 8, x: 0, y: 2)
    }
    
    private var placeholderImage: some View {
        Rectangle()
            .fill(Color(.systemGray5))
            .overlay {
                Image(systemName: "fork.knife")
                    .foregroundStyle(.gray)
            }
    }
}

#Preview {
    VStack(spacing: 16) {
        RestaurantCard(restaurant: .preview)
        RestaurantCard(restaurant: Restaurant.previews[1])
    }
    .padding()
    .background(Color(.systemGray6))
}
