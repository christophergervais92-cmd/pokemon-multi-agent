import SwiftUI
import MapKit

struct OrderTrackingView: View {
    let order: Order
    @StateObject private var viewModel: OrderTrackingViewModel
    @Environment(\.dismiss) var dismiss
    @State private var showOrderDetails = false
    
    init(order: Order) {
        self.order = order
        self._viewModel = StateObject(wrappedValue: OrderTrackingViewModel(order: order))
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Map
            MapTrackingView(
                deliveryLocation: deliveryCoordinate,
                driverLocation: viewModel.driverLocation,
                restaurantLocation: nil
            )
            .frame(height: 300)
            .ignoresSafeArea(edges: .top)
            
            // Order Status Card
            ScrollView {
                VStack(spacing: 20) {
                    // ETA Card
                    if viewModel.order.status.isActive {
                        ETACard(
                            estimatedTime: viewModel.estimatedArrival ?? minutesUntilDelivery,
                            status: viewModel.order.status
                        )
                    }
                    
                    // Driver Info (if assigned)
                    if let driver = viewModel.order.driver, viewModel.order.status == .outForDelivery {
                        DriverCard(driver: driver)
                    }
                    
                    // Status Timeline
                    StatusTimelineView(steps: viewModel.statusSteps)
                    
                    // Order Summary Button
                    Button {
                        showOrderDetails = true
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(viewModel.order.restaurant?.name ?? "Restaurant")
                                    .font(.headline)
                                Text("\(viewModel.order.items.count) items • \(viewModel.order.totalFormatted)")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
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
                    
                    // Help Button
                    Button {
                        // Open support
                    } label: {
                        HStack {
                            Image(systemName: "questionmark.circle")
                            Text("Need help with your order?")
                        }
                        .foregroundStyle(.orange)
                    }
                    .padding(.top, 8)
                }
                .padding()
            }
        }
        .navigationTitle("Track Order")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showOrderDetails) {
            OrderDetailsSheet(order: viewModel.order)
        }
        .refreshable {
            await viewModel.refreshOrder()
        }
        .onDisappear {
            viewModel.disconnect()
        }
    }
    
    private var deliveryCoordinate: CLLocationCoordinate2D? {
        guard let lat = viewModel.order.deliveryLatitude,
              let lng = viewModel.order.deliveryLongitude else {
            return nil
        }
        return CLLocationCoordinate2D(latitude: lat, longitude: lng)
    }
    
    private var minutesUntilDelivery: Int {
        guard let estimated = viewModel.order.estimatedDelivery else { return 30 }
        let minutes = Calendar.current.dateComponents([.minute], from: Date(), to: estimated).minute ?? 30
        return max(0, minutes)
    }
}

struct MapTrackingView: View {
    let deliveryLocation: CLLocationCoordinate2D?
    let driverLocation: CLLocationCoordinate2D?
    let restaurantLocation: CLLocationCoordinate2D?
    
    @State private var cameraPosition: MapCameraPosition = .automatic
    
    var body: some View {
        Map(position: $cameraPosition) {
            // Delivery Location
            if let delivery = deliveryLocation {
                Annotation("Delivery", coordinate: delivery) {
                    Image(systemName: "house.fill")
                        .foregroundStyle(.white)
                        .padding(8)
                        .background(Color.green)
                        .clipShape(Circle())
                }
            }
            
            // Driver Location
            if let driver = driverLocation {
                Annotation("Driver", coordinate: driver) {
                    Image(systemName: "car.fill")
                        .foregroundStyle(.white)
                        .padding(8)
                        .background(Color.orange)
                        .clipShape(Circle())
                }
            }
            
            // Restaurant Location
            if let restaurant = restaurantLocation {
                Annotation("Restaurant", coordinate: restaurant) {
                    Image(systemName: "fork.knife")
                        .foregroundStyle(.white)
                        .padding(8)
                        .background(Color.red)
                        .clipShape(Circle())
                }
            }
        }
        .mapStyle(.standard)
        .onAppear {
            updateCameraPosition()
        }
        .onChange(of: driverLocation) { _, _ in
            updateCameraPosition()
        }
    }
    
    private func updateCameraPosition() {
        var coordinates: [CLLocationCoordinate2D] = []
        
        if let delivery = deliveryLocation {
            coordinates.append(delivery)
        }
        if let driver = driverLocation {
            coordinates.append(driver)
        }
        
        guard !coordinates.isEmpty else { return }
        
        if coordinates.count == 1 {
            cameraPosition = .region(MKCoordinateRegion(
                center: coordinates[0],
                span: MKCoordinateSpan(latitudeDelta: 0.02, longitudeDelta: 0.02)
            ))
        } else {
            let minLat = coordinates.map { $0.latitude }.min()!
            let maxLat = coordinates.map { $0.latitude }.max()!
            let minLng = coordinates.map { $0.longitude }.min()!
            let maxLng = coordinates.map { $0.longitude }.max()!
            
            let center = CLLocationCoordinate2D(
                latitude: (minLat + maxLat) / 2,
                longitude: (minLng + maxLng) / 2
            )
            
            let span = MKCoordinateSpan(
                latitudeDelta: (maxLat - minLat) * 1.5 + 0.01,
                longitudeDelta: (maxLng - minLng) * 1.5 + 0.01
            )
            
            cameraPosition = .region(MKCoordinateRegion(center: center, span: span))
        }
    }
}

struct ETACard: View {
    let estimatedTime: Int
    let status: OrderStatus
    
    var body: some View {
        VStack(spacing: 8) {
            Text(status == .delivered ? "Delivered!" : "Estimated Arrival")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            
            if status != .delivered {
                Text("\(estimatedTime) min")
                    .font(.system(size: 48, weight: .bold))
                    .foregroundStyle(.orange)
            } else {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 48))
                    .foregroundStyle(.green)
            }
            
            Text(status.displayName)
                .font(.headline)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 4)
    }
}

struct DriverCard: View {
    let driver: OrderDriver
    
    var body: some View {
        HStack(spacing: 12) {
            // Driver Avatar
            if let avatarUrl = driver.avatarUrl {
                AsyncImage(url: URL(string: avatarUrl)) { image in
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                } placeholder: {
                    Circle()
                        .fill(Color(.systemGray5))
                }
                .frame(width: 50, height: 50)
                .clipShape(Circle())
            } else {
                Circle()
                    .fill(Color(.systemGray5))
                    .frame(width: 50, height: 50)
                    .overlay {
                        Image(systemName: "person.fill")
                            .foregroundStyle(.gray)
                    }
            }
            
            // Driver Info
            VStack(alignment: .leading, spacing: 4) {
                Text(driver.name)
                    .font(.headline)
                
                HStack(spacing: 4) {
                    Image(systemName: "star.fill")
                        .foregroundStyle(.yellow)
                        .font(.caption)
                    Text(String(format: "%.1f", driver.rating))
                        .font(.caption)
                    Text("•")
                        .foregroundStyle(.secondary)
                    Text(driver.vehicleType)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            
            Spacer()
            
            // Call Button
            Button {
                if let url = URL(string: "tel:\(driver.phone)") {
                    UIApplication.shared.open(url)
                }
            } label: {
                Image(systemName: "phone.fill")
                    .foregroundStyle(.white)
                    .padding(12)
                    .background(Color.green)
                    .clipShape(Circle())
            }
            
            // Message Button
            Button {
                // Open chat
            } label: {
                Image(systemName: "message.fill")
                    .foregroundStyle(.white)
                    .padding(12)
                    .background(Color.orange)
                    .clipShape(Circle())
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 4)
    }
}

struct StatusTimelineView: View {
    let steps: [StatusStep]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(steps.enumerated()), id: \.element.id) { index, step in
                HStack(alignment: .top, spacing: 16) {
                    // Timeline indicator
                    VStack(spacing: 0) {
                        Circle()
                            .fill(step.isCompleted ? Color.orange : Color(.systemGray4))
                            .frame(width: 24, height: 24)
                            .overlay {
                                if step.isCompleted {
                                    Image(systemName: "checkmark")
                                        .font(.caption)
                                        .fontWeight(.bold)
                                        .foregroundStyle(.white)
                                }
                            }
                        
                        if index < steps.count - 1 {
                            Rectangle()
                                .fill(step.isCompleted ? Color.orange : Color(.systemGray4))
                                .frame(width: 2, height: 40)
                        }
                    }
                    
                    // Step content
                    VStack(alignment: .leading, spacing: 4) {
                        Text(step.title)
                            .font(.headline)
                            .foregroundStyle(step.isCurrent ? .orange : (step.isCompleted ? .primary : .secondary))
                        
                        Text(step.subtitle)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.bottom, index < steps.count - 1 ? 24 : 0)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 8, x: 0, y: 4)
    }
}

struct OrderDetailsSheet: View {
    let order: Order
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            List {
                Section("Order #\(String(order.id.prefix(8)))") {
                    Text("Placed \(order.createdAtFormatted)")
                        .foregroundStyle(.secondary)
                }
                
                Section("Items") {
                    ForEach(order.items) { item in
                        HStack {
                            Text("\(item.quantity)x")
                                .foregroundStyle(.secondary)
                            Text(item.name)
                            Spacer()
                            Text(item.totalPriceFormatted)
                        }
                    }
                }
                
                Section("Delivery Address") {
                    Text(order.deliveryAddress.formatted)
                }
                
                Section("Payment") {
                    HStack {
                        Text("Subtotal")
                        Spacer()
                        Text(formatCurrency(order.subtotal))
                    }
                    
                    HStack {
                        Text("Delivery Fee")
                        Spacer()
                        Text(formatCurrency(order.deliveryFee))
                    }
                    
                    HStack {
                        Text("Service Fee")
                        Spacer()
                        Text(formatCurrency(order.serviceFee))
                    }
                    
                    if order.tip > 0 {
                        HStack {
                            Text("Tip")
                            Spacer()
                            Text(formatCurrency(order.tip))
                        }
                    }
                    
                    HStack {
                        Text("Total")
                            .fontWeight(.bold)
                        Spacer()
                        Text(order.totalFormatted)
                            .fontWeight(.bold)
                    }
                }
            }
            .navigationTitle("Order Details")
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
    
    private func formatCurrency(_ value: Decimal) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: value as NSDecimalNumber) ?? "$\(value)"
    }
}

#Preview {
    NavigationStack {
        OrderTrackingView(order: .preview)
    }
}
