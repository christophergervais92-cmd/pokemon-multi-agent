import Foundation

@MainActor
class OrdersViewModel: ObservableObject {
    @Published var activeOrders: [Order] = []
    @Published var pastOrders: [Order] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    func loadOrders() async {
        isLoading = true
        
        do {
            let orders: [Order] = try await APIClient.shared.request(endpoint: Endpoints.orders)
            
            activeOrders = orders.filter { $0.status.isActive }
            pastOrders = orders.filter { !$0.status.isActive }
        } catch {
            errorMessage = error.localizedDescription
            
            // Demo data
            activeOrders = [Order.preview]
            pastOrders = []
        }
        
        isLoading = false
    }
    
    func reorder(_ order: Order) async -> [ReorderItem]? {
        do {
            let items: [ReorderItem] = try await APIClient.shared.request(
                endpoint: "\(Endpoints.order(order.id))/reorder",
                method: .POST
            )
            return items
        } catch {
            errorMessage = "Failed to reorder"
            return nil
        }
    }
}

struct ReorderItem: Decodable {
    let menuItemId: String
    let name: String
    let quantity: Int
    let selectedOptions: [[String: String]]?
    let specialNotes: String?
}
