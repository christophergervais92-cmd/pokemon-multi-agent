import SwiftUI

@main
struct FoodDeliveryApp: App {
    @StateObject private var authManager = AuthManager()
    @StateObject private var cartManager = CartManager()
    @StateObject private var locationManager = LocationManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .environmentObject(cartManager)
                .environmentObject(locationManager)
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var authManager: AuthManager
    
    var body: some View {
        Group {
            if authManager.isAuthenticated {
                MainTabView()
            } else {
                LoginView()
            }
        }
        .animation(.easeInOut, value: authManager.isAuthenticated)
    }
}

struct MainTabView: View {
    @State private var selectedTab = 0
    @EnvironmentObject var cartManager: CartManager
    
    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem {
                    Image(systemName: "house.fill")
                    Text("Home")
                }
                .tag(0)
            
            SearchView()
                .tabItem {
                    Image(systemName: "magnifyingglass")
                    Text("Search")
                }
                .tag(1)
            
            OrderHistoryView()
                .tabItem {
                    Image(systemName: "bag.fill")
                    Text("Orders")
                }
                .tag(2)
            
            ProfileView()
                .tabItem {
                    Image(systemName: "person.fill")
                    Text("Profile")
                }
                .tag(3)
        }
        .overlay(alignment: .bottom) {
            if cartManager.items.count > 0 {
                CartFloatingButton()
                    .padding(.bottom, 60)
            }
        }
    }
}

struct CartFloatingButton: View {
    @EnvironmentObject var cartManager: CartManager
    @State private var showCart = false
    
    var body: some View {
        Button {
            showCart = true
        } label: {
            HStack {
                Text("View Cart")
                    .fontWeight(.semibold)
                Spacer()
                Text("\(cartManager.items.count) items")
                Text("•")
                Text(cartManager.totalFormatted)
                    .fontWeight(.bold)
            }
            .foregroundColor(.white)
            .padding()
            .background(Color.orange)
            .cornerRadius(12)
            .padding(.horizontal)
        }
        .sheet(isPresented: $showCart) {
            CartView()
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AuthManager())
        .environmentObject(CartManager())
        .environmentObject(LocationManager())
}
