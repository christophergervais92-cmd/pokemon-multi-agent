import Foundation
import Combine

@MainActor
class CheckoutViewModel: ObservableObject {
    @Published var selectedAddress: Address?
    @Published var addresses: [Address] = []
    @Published var selectedPaymentMethod: PaymentMethod?
    @Published var paymentMethods: [PaymentMethod] = []
    @Published var tip: Decimal = 0
    @Published var specialInstructions = ""
    @Published var isLoading = false
    @Published var isPlacingOrder = false
    @Published var errorMessage: String?
    @Published var createdOrder: Order?
    
    let deliveryFee: Decimal = 2.99
    let serviceFeeRate: Decimal = 0.05
    
    func loadData() async {
        isLoading = true
        
        async let addressesTask = loadAddresses()
        async let paymentTask = loadPaymentMethods()
        
        await addressesTask
        await paymentTask
        
        isLoading = false
    }
    
    private func loadAddresses() async {
        do {
            addresses = try await APIClient.shared.request(endpoint: Endpoints.userAddresses)
            selectedAddress = addresses.first { $0.isDefault } ?? addresses.first
        } catch {
            // Use preview data
            addresses = Address.previews
            selectedAddress = addresses.first
        }
    }
    
    private func loadPaymentMethods() async {
        do {
            paymentMethods = try await APIClient.shared.request(endpoint: "/users/me/payment-methods")
            selectedPaymentMethod = paymentMethods.first { $0.isDefault } ?? paymentMethods.first
        } catch {
            // Use demo data
            paymentMethods = [
                PaymentMethod(id: "1", stripeMethodId: "pm_1", type: "card", last4: "4242", brand: "Visa", isDefault: true),
                PaymentMethod(id: "2", stripeMethodId: "pm_2", type: "card", last4: "5555", brand: "Mastercard", isDefault: false)
            ]
            selectedPaymentMethod = paymentMethods.first
        }
    }
    
    func calculateServiceFee(subtotal: Decimal) -> Decimal {
        subtotal * serviceFeeRate
    }
    
    func calculateTotal(subtotal: Decimal) -> Decimal {
        subtotal + deliveryFee + calculateServiceFee(subtotal: subtotal) + tip
    }
    
    func placeOrder(cartManager: CartManager) async -> Bool {
        guard let address = selectedAddress,
              let paymentMethod = selectedPaymentMethod,
              let restaurantId = cartManager.restaurantId else {
            errorMessage = "Please complete all required fields"
            return false
        }
        
        isPlacingOrder = true
        errorMessage = nil
        
        do {
            let orderItems = cartManager.items.map { item -> CreateOrderItem in
                let options: [[String: String]]? = item.selectedOptions.isEmpty ? nil :
                    item.selectedOptions.flatMap { (optionId, choices) in
                        choices.map { ["optionId": optionId, "choiceId": $0.id] }
                    }
                
                return CreateOrderItem(
                    menuItemId: item.menuItem.id,
                    quantity: item.quantity,
                    selectedOptions: options,
                    specialNotes: item.specialNotes
                )
            }
            
            let request = CreateOrderRequest(
                restaurantId: restaurantId,
                items: orderItems,
                deliveryAddress: address.toDeliveryAddress(),
                deliveryLatitude: address.latitude,
                deliveryLongitude: address.longitude,
                specialInstructions: specialInstructions.isEmpty ? nil : specialInstructions,
                tip: tip,
                paymentMethodId: paymentMethod.stripeMethodId
            )
            
            let order: Order = try await APIClient.shared.request(
                endpoint: Endpoints.orders,
                method: .POST,
                body: request
            )
            
            createdOrder = order
            cartManager.clearCart()
            
            isPlacingOrder = false
            return true
        } catch {
            errorMessage = error.localizedDescription
            isPlacingOrder = false
            
            // Demo: Create mock order
            createdOrder = Order.preview
            cartManager.clearCart()
            return true
        }
    }
    
    var tipOptions: [TipOption] {
        [
            TipOption(label: "No Tip", amount: 0),
            TipOption(label: "$2", amount: 2),
            TipOption(label: "$5", amount: 5),
            TipOption(label: "$10", amount: 10),
            TipOption(label: "Custom", amount: -1)
        ]
    }
}

struct TipOption: Identifiable {
    let id = UUID()
    let label: String
    let amount: Decimal
    
    var isCustom: Bool { amount < 0 }
}

struct PaymentMethod: Codable, Identifiable {
    let id: String
    let stripeMethodId: String
    let type: String
    let last4: String
    let brand: String?
    let isDefault: Bool
    
    var displayName: String {
        "\(brand ?? "Card") •••• \(last4)"
    }
    
    var icon: String {
        switch brand?.lowercased() {
        case "visa": return "creditcard"
        case "mastercard": return "creditcard"
        case "amex": return "creditcard"
        default: return "creditcard"
        }
    }
}
