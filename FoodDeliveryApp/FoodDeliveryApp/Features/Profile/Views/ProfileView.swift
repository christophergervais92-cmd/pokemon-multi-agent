import SwiftUI

struct ProfileView: View {
    @EnvironmentObject var authManager: AuthManager
    @State private var showLogoutConfirmation = false
    
    var body: some View {
        NavigationStack {
            List {
                // User Header
                Section {
                    HStack(spacing: 16) {
                        // Avatar
                        if let avatarUrl = authManager.currentUser?.avatarUrl {
                            AsyncImage(url: URL(string: avatarUrl)) { image in
                                image
                                    .resizable()
                                    .aspectRatio(contentMode: .fill)
                            } placeholder: {
                                Circle()
                                    .fill(Color(.systemGray5))
                            }
                            .frame(width: 60, height: 60)
                            .clipShape(Circle())
                        } else {
                            Circle()
                                .fill(Color.orange)
                                .frame(width: 60, height: 60)
                                .overlay {
                                    Text(authManager.currentUser?.name.prefix(1).uppercased() ?? "?")
                                        .font(.title)
                                        .fontWeight(.bold)
                                        .foregroundStyle(.white)
                                }
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text(authManager.currentUser?.name ?? "User")
                                .font(.headline)
                            
                            Text(authManager.currentUser?.email ?? "")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        
                        Spacer()
                        
                        NavigationLink {
                            EditProfileView()
                        } label: {
                            Image(systemName: "pencil.circle.fill")
                                .font(.title2)
                                .foregroundStyle(.orange)
                        }
                    }
                    .padding(.vertical, 8)
                }
                
                // Account
                Section("Account") {
                    NavigationLink {
                        AddressesView()
                    } label: {
                        ProfileRow(icon: "location.fill", title: "Addresses", color: .blue)
                    }
                    
                    NavigationLink {
                        PaymentMethodsView()
                    } label: {
                        ProfileRow(icon: "creditcard.fill", title: "Payment Methods", color: .green)
                    }
                    
                    NavigationLink {
                        FavoritesView()
                    } label: {
                        ProfileRow(icon: "heart.fill", title: "Favorites", color: .red)
                    }
                }
                
                // Preferences
                Section("Preferences") {
                    NavigationLink {
                        NotificationSettingsView()
                    } label: {
                        ProfileRow(icon: "bell.fill", title: "Notifications", color: .orange)
                    }
                    
                    NavigationLink {
                        // Language settings
                    } label: {
                        ProfileRow(icon: "globe", title: "Language", color: .purple)
                    }
                }
                
                // Support
                Section("Support") {
                    NavigationLink {
                        // Help center
                    } label: {
                        ProfileRow(icon: "questionmark.circle.fill", title: "Help Center", color: .teal)
                    }
                    
                    Button {
                        // Rate app
                    } label: {
                        ProfileRow(icon: "star.fill", title: "Rate the App", color: .yellow)
                    }
                    
                    NavigationLink {
                        // About
                    } label: {
                        ProfileRow(icon: "info.circle.fill", title: "About", color: .gray)
                    }
                }
                
                // Logout
                Section {
                    Button {
                        showLogoutConfirmation = true
                    } label: {
                        HStack {
                            Spacer()
                            Text("Log Out")
                                .foregroundStyle(.red)
                            Spacer()
                        }
                    }
                }
            }
            .navigationTitle("Profile")
            .confirmationDialog("Log Out", isPresented: $showLogoutConfirmation) {
                Button("Log Out", role: .destructive) {
                    Task {
                        await authManager.logout()
                    }
                }
            } message: {
                Text("Are you sure you want to log out?")
            }
        }
    }
}

struct ProfileRow: View {
    let icon: String
    let title: String
    let color: Color
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(color)
                .frame(width: 24)
            
            Text(title)
        }
    }
}

struct EditProfileView: View {
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.dismiss) var dismiss
    
    @State private var name = ""
    @State private var phone = ""
    @State private var isSaving = false
    
    var body: some View {
        Form {
            Section("Personal Information") {
                TextField("Name", text: $name)
                
                TextField("Phone", text: $phone)
                    .keyboardType(.phonePad)
            }
            
            Section("Email") {
                Text(authManager.currentUser?.email ?? "")
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Edit Profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") {
                    saveChanges()
                }
                .disabled(name.isEmpty || isSaving)
            }
        }
        .onAppear {
            name = authManager.currentUser?.name ?? ""
            phone = authManager.currentUser?.phone ?? ""
        }
    }
    
    private func saveChanges() {
        isSaving = true
        
        Task {
            await authManager.updateProfile(
                name: name,
                phone: phone.isEmpty ? nil : phone
            )
            dismiss()
        }
    }
}

struct NotificationSettingsView: View {
    @State private var orderUpdates = true
    @State private var promotions = true
    @State private var newRestaurants = false
    
    var body: some View {
        Form {
            Section("Order Updates") {
                Toggle("Order status updates", isOn: $orderUpdates)
                Toggle("Driver updates", isOn: $orderUpdates)
            }
            
            Section("Marketing") {
                Toggle("Promotions & deals", isOn: $promotions)
                Toggle("New restaurants nearby", isOn: $newRestaurants)
            }
        }
        .navigationTitle("Notifications")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    ProfileView()
        .environmentObject(AuthManager())
}
