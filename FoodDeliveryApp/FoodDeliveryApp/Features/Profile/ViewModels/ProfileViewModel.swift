import Foundation

@MainActor
class ProfileViewModel: ObservableObject {
    @Published var addresses: [Address] = []
    @Published var paymentMethods: [PaymentMethod] = []
    @Published var favoriteRestaurants: [Restaurant] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    func loadAddresses() async {
        do {
            addresses = try await APIClient.shared.request(endpoint: Endpoints.userAddresses)
        } catch {
            addresses = Address.previews
        }
    }
    
    func loadPaymentMethods() async {
        do {
            paymentMethods = try await APIClient.shared.request(endpoint: "/users/me/payment-methods")
        } catch {
            paymentMethods = [
                PaymentMethod(id: "1", stripeMethodId: "pm_1", type: "card", last4: "4242", brand: "Visa", isDefault: true)
            ]
        }
    }
    
    func loadFavorites() async {
        do {
            favoriteRestaurants = try await APIClient.shared.request(endpoint: Endpoints.favorites)
        } catch {
            favoriteRestaurants = []
        }
    }
    
    func deleteAddress(_ address: Address) async {
        do {
            try await APIClient.shared.requestNoResponse(
                endpoint: Endpoints.deleteAddress(address.id),
                method: .DELETE
            )
            addresses.removeAll { $0.id == address.id }
        } catch {
            errorMessage = "Failed to delete address"
        }
    }
    
    func setDefaultAddress(_ address: Address) async {
        do {
            let updated: Address = try await APIClient.shared.request(
                endpoint: "\(Endpoints.deleteAddress(address.id))/default",
                method: .PUT
            )
            
            // Update local state
            for i in addresses.indices {
                if addresses[i].id == address.id {
                    addresses[i] = updated
                } else if addresses[i].isDefault {
                    // Remove default from other
                    addresses[i] = Address(
                        id: addresses[i].id,
                        userId: addresses[i].userId,
                        label: addresses[i].label,
                        street: addresses[i].street,
                        apartment: addresses[i].apartment,
                        city: addresses[i].city,
                        state: addresses[i].state,
                        zipCode: addresses[i].zipCode,
                        latitude: addresses[i].latitude,
                        longitude: addresses[i].longitude,
                        isDefault: false
                    )
                }
            }
        } catch {
            errorMessage = "Failed to set default address"
        }
    }
}
