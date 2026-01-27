import SwiftUI
import CoreLocation

struct AddressPickerView: View {
    @EnvironmentObject var locationManager: LocationManager
    @Environment(\.dismiss) var dismiss
    
    @State private var addresses: [Address] = []
    @State private var isLoading = true
    @State private var showAddAddress = false
    
    var body: some View {
        NavigationStack {
            List {
                // Current Location
                Section {
                    Button {
                        locationManager.requestLocation()
                        dismiss()
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: "location.fill")
                                .foregroundStyle(.blue)
                                .font(.title3)
                            
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Use Current Location")
                                    .font(.headline)
                                
                                if let address = locationManager.currentAddress {
                                    Text(address)
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                } else if locationManager.isLoading {
                                    Text("Getting location...")
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            
                            Spacer()
                            
                            if locationManager.isLoading {
                                ProgressView()
                            }
                        }
                    }
                    .buttonStyle(PlainButtonStyle())
                }
                
                // Saved Addresses
                Section("Saved Addresses") {
                    if isLoading {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                    } else if addresses.isEmpty {
                        Text("No saved addresses")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(addresses) { address in
                            Button {
                                // Select address
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
                                        
                                        Text(address.oneLine)
                                            .font(.subheadline)
                                            .foregroundStyle(.secondary)
                                    }
                                    
                                    Spacer()
                                    
                                    Image(systemName: "chevron.right")
                                        .foregroundStyle(.gray)
                                }
                            }
                            .buttonStyle(PlainButtonStyle())
                        }
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
            }
            .navigationTitle("Delivery Address")
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
            .task {
                await loadAddresses()
            }
        }
    }
    
    private func loadAddresses() async {
        do {
            addresses = try await APIClient.shared.request(endpoint: Endpoints.userAddresses)
        } catch {
            addresses = Address.previews
        }
        isLoading = false
    }
}

#Preview {
    AddressPickerView()
        .environmentObject(LocationManager())
}
