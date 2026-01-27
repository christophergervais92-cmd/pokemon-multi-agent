import SwiftUI

struct CheckoutView: View {
    @StateObject private var viewModel = CheckoutViewModel()
    @EnvironmentObject var cartManager: CartManager
    @Environment(\.dismiss) var dismiss
    
    @State private var showAddressPicker = false
    @State private var showPaymentPicker = false
    @State private var showCustomTip = false
    @State private var customTipAmount = ""
    @State private var showOrderConfirmation = false
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Delivery Address
                CheckoutSection(title: "Delivery Address", icon: "location.fill") {
                    Button {
                        showAddressPicker = true
                    } label: {
                        HStack {
                            if let address = viewModel.selectedAddress {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(address.label)
                                        .font(.headline)
                                    Text(address.oneLine)
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                            } else {
                                Text("Select delivery address")
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
                }
                
                // Payment Method
                CheckoutSection(title: "Payment Method", icon: "creditcard.fill") {
                    Button {
                        showPaymentPicker = true
                    } label: {
                        HStack {
                            if let payment = viewModel.selectedPaymentMethod {
                                HStack(spacing: 12) {
                                    Image(systemName: payment.icon)
                                        .font(.title2)
                                    
                                    Text(payment.displayName)
                                        .font(.headline)
                                }
                            } else {
                                Text("Select payment method")
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
                }
                
                // Order Summary
                CheckoutSection(title: "Order Summary", icon: "bag.fill") {
                    VStack(spacing: 12) {
                        ForEach(cartManager.items) { item in
                            HStack {
                                Text("\(item.quantity)x")
                                    .foregroundStyle(.secondary)
                                Text(item.menuItem.name)
                                Spacer()
                                Text(item.totalPriceFormatted)
                            }
                            .font(.subheadline)
                        }
                    }
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
                
                // Tip
                CheckoutSection(title: "Add a Tip", icon: "heart.fill") {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 12) {
                            ForEach(viewModel.tipOptions) { option in
                                TipButton(
                                    option: option,
                                    isSelected: option.isCustom ? showCustomTip : viewModel.tip == option.amount,
                                    onTap: {
                                        if option.isCustom {
                                            showCustomTip = true
                                        } else {
                                            showCustomTip = false
                                            viewModel.tip = option.amount
                                        }
                                    }
                                )
                            }
                        }
                    }
                    
                    if showCustomTip {
                        HStack {
                            Text("$")
                            TextField("Amount", text: $customTipAmount)
                                .keyboardType(.decimalPad)
                                .onChange(of: customTipAmount) { _, newValue in
                                    if let amount = Decimal(string: newValue) {
                                        viewModel.tip = amount
                                    }
                                }
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                        .padding(.top, 8)
                    }
                }
                
                // Special Instructions
                CheckoutSection(title: "Special Instructions", icon: "text.bubble.fill") {
                    TextField("Add delivery instructions...", text: $viewModel.specialInstructions, axis: .vertical)
                        .lineLimit(2...4)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                }
                
                // Price Breakdown
                CheckoutSection(title: "Price Details", icon: "dollarsign.circle.fill") {
                    VStack(spacing: 12) {
                        PriceRow(label: "Subtotal", value: cartManager.subtotal)
                        PriceRow(label: "Delivery Fee", value: viewModel.deliveryFee)
                        PriceRow(label: "Service Fee", value: viewModel.calculateServiceFee(subtotal: cartManager.subtotal))
                        if viewModel.tip > 0 {
                            PriceRow(label: "Tip", value: viewModel.tip)
                        }
                        Divider()
                        PriceRow(label: "Total", value: viewModel.calculateTotal(subtotal: cartManager.subtotal), isTotal: true)
                    }
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                }
                
                // Error Message
                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal)
                }
            }
            .padding()
            .padding(.bottom, 100)
        }
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 0) {
                Divider()
                
                Button {
                    Task {
                        let success = await viewModel.placeOrder(cartManager: cartManager)
                        if success {
                            showOrderConfirmation = true
                        }
                    }
                } label: {
                    HStack {
                        if viewModel.isPlacingOrder {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text("Place Order")
                                .fontWeight(.semibold)
                            Spacer()
                            Text(formatCurrency(viewModel.calculateTotal(subtotal: cartManager.subtotal)))
                                .fontWeight(.bold)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(canPlaceOrder ? Color.orange : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                .disabled(!canPlaceOrder || viewModel.isPlacingOrder)
                .padding()
                .background(Color(.systemBackground))
            }
        }
        .navigationTitle("Checkout")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showAddressPicker) {
            AddressPickerView(
                addresses: viewModel.addresses,
                selectedAddress: $viewModel.selectedAddress
            )
        }
        .sheet(isPresented: $showPaymentPicker) {
            PaymentPickerView(
                paymentMethods: viewModel.paymentMethods,
                selectedMethod: $viewModel.selectedPaymentMethod
            )
        }
        .fullScreenCover(isPresented: $showOrderConfirmation) {
            if let order = viewModel.createdOrder {
                OrderConfirmationView(order: order)
            }
        }
        .task {
            await viewModel.loadData()
        }
    }
    
    private var canPlaceOrder: Bool {
        viewModel.selectedAddress != nil && viewModel.selectedPaymentMethod != nil
    }
    
    private func formatCurrency(_ value: Decimal) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: value as NSDecimalNumber) ?? "$\(value)"
    }
}

struct CheckoutSection<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: () -> Content
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .foregroundStyle(.orange)
                Text(title)
                    .font(.headline)
            }
            
            content()
        }
    }
}

struct TipButton: View {
    let option: TipOption
    let isSelected: Bool
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            Text(option.label)
                .font(.subheadline)
                .fontWeight(.medium)
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
                .background(isSelected ? Color.orange : Color(.systemGray6))
                .foregroundColor(isSelected ? .white : .primary)
                .cornerRadius(20)
        }
    }
}

struct PriceRow: View {
    let label: String
    let value: Decimal
    var isTotal: Bool = false
    
    var body: some View {
        HStack {
            Text(label)
                .fontWeight(isTotal ? .bold : .regular)
            Spacer()
            Text(formatCurrency(value))
                .fontWeight(isTotal ? .bold : .regular)
        }
        .font(isTotal ? .headline : .subheadline)
    }
    
    private func formatCurrency(_ value: Decimal) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: value as NSDecimalNumber) ?? "$\(value)"
    }
}

struct AddressPickerView: View {
    let addresses: [Address]
    @Binding var selectedAddress: Address?
    @Environment(\.dismiss) var dismiss
    @State private var showAddAddress = false
    
    var body: some View {
        NavigationStack {
            List {
                ForEach(addresses) { address in
                    Button {
                        selectedAddress = address
                        dismiss()
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(address.label)
                                        .font(.headline)
                                    if address.isDefault {
                                        Text("Default")
                                            .font(.caption)
                                            .padding(.horizontal, 6)
                                            .padding(.vertical, 2)
                                            .background(Color.orange.opacity(0.2))
                                            .foregroundStyle(.orange)
                                            .cornerRadius(4)
                                    }
                                }
                                Text(address.formatted)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                            
                            Spacer()
                            
                            if selectedAddress?.id == address.id {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(.orange)
                            }
                        }
                    }
                    .buttonStyle(PlainButtonStyle())
                }
                
                Button {
                    showAddAddress = true
                } label: {
                    HStack {
                        Image(systemName: "plus.circle.fill")
                            .foregroundStyle(.orange)
                        Text("Add New Address")
                    }
                }
            }
            .navigationTitle("Select Address")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .sheet(isPresented: $showAddAddress) {
                AddAddressView()
            }
        }
    }
}

struct PaymentPickerView: View {
    let paymentMethods: [PaymentMethod]
    @Binding var selectedMethod: PaymentMethod?
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            List {
                ForEach(paymentMethods) { method in
                    Button {
                        selectedMethod = method
                        dismiss()
                    } label: {
                        HStack {
                            Image(systemName: method.icon)
                                .font(.title2)
                                .frame(width: 40)
                            
                            VStack(alignment: .leading, spacing: 4) {
                                Text(method.displayName)
                                    .font(.headline)
                                if method.isDefault {
                                    Text("Default")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            
                            Spacer()
                            
                            if selectedMethod?.id == method.id {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(.orange)
                            }
                        }
                    }
                    .buttonStyle(PlainButtonStyle())
                }
                
                Button {
                    // Add new payment method
                } label: {
                    HStack {
                        Image(systemName: "plus.circle.fill")
                            .foregroundStyle(.orange)
                        Text("Add Payment Method")
                    }
                }
            }
            .navigationTitle("Payment Method")
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
}

struct AddAddressView: View {
    @Environment(\.dismiss) var dismiss
    @State private var label = "Home"
    @State private var street = ""
    @State private var apartment = ""
    @State private var city = ""
    @State private var state = ""
    @State private var zipCode = ""
    @State private var isDefault = false
    
    var body: some View {
        NavigationStack {
            Form {
                Section("Address Label") {
                    Picker("Label", selection: $label) {
                        Text("Home").tag("Home")
                        Text("Work").tag("Work")
                        Text("Other").tag("Other")
                    }
                    .pickerStyle(.segmented)
                }
                
                Section("Address Details") {
                    TextField("Street Address", text: $street)
                    TextField("Apt, Suite, Building (optional)", text: $apartment)
                    TextField("City", text: $city)
                    TextField("State", text: $state)
                    TextField("ZIP Code", text: $zipCode)
                        .keyboardType(.numberPad)
                }
                
                Section {
                    Toggle("Set as default address", isOn: $isDefault)
                }
            }
            .navigationTitle("New Address")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        // Save address
                        dismiss()
                    }
                    .disabled(street.isEmpty || city.isEmpty || state.isEmpty || zipCode.isEmpty)
                }
            }
        }
    }
}

struct OrderConfirmationView: View {
    let order: Order
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()
                
                // Success Animation
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 80))
                    .foregroundStyle(.green)
                
                Text("Order Placed!")
                    .font(.title)
                    .fontWeight(.bold)
                
                Text("Your order #\(String(order.id.prefix(8))) has been confirmed")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                
                // Estimated Time
                VStack(spacing: 8) {
                    Text("Estimated Delivery")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    
                    if let eta = order.estimatedDeliveryFormatted {
                        Text(eta)
                            .font(.title2)
                            .fontWeight(.semibold)
                    }
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(Color(.systemGray6))
                .cornerRadius(12)
                .padding(.horizontal)
                
                Spacer()
                
                // Actions
                VStack(spacing: 12) {
                    NavigationLink {
                        OrderTrackingView(order: order)
                    } label: {
                        Text("Track Order")
                            .fontWeight(.semibold)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.orange)
                            .foregroundColor(.white)
                            .cornerRadius(12)
                    }
                    
                    Button {
                        dismiss()
                    } label: {
                        Text("Back to Home")
                            .fontWeight(.medium)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(.systemGray6))
                            .foregroundColor(.primary)
                            .cornerRadius(12)
                    }
                }
                .padding()
            }
            .navigationBarBackButtonHidden(true)
        }
    }
}

#Preview {
    NavigationStack {
        CheckoutView()
            .environmentObject(CartManager())
    }
}
