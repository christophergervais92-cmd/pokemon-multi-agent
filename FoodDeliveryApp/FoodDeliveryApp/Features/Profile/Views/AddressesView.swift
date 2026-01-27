import SwiftUI

struct AddressesView: View {
    @StateObject private var viewModel = ProfileViewModel()
    @State private var showAddAddress = false
    
    var body: some View {
        List {
            ForEach(viewModel.addresses) { address in
                AddressRow(
                    address: address,
                    onSetDefault: {
                        Task { await viewModel.setDefaultAddress(address) }
                    }
                )
                .swipeActions(edge: .trailing) {
                    Button(role: .destructive) {
                        Task { await viewModel.deleteAddress(address) }
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
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
        .navigationTitle("Addresses")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showAddAddress) {
            AddAddressView()
        }
        .task {
            await viewModel.loadAddresses()
        }
    }
}

struct AddressRow: View {
    let address: Address
    let onSetDefault: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(address.label)
                    .font(.headline)
                
                if address.isDefault {
                    Text("Default")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.orange.opacity(0.2))
                        .foregroundStyle(.orange)
                        .cornerRadius(4)
                }
                
                Spacer()
                
                if !address.isDefault {
                    Button("Set Default") {
                        onSetDefault()
                    }
                    .font(.caption)
                    .foregroundStyle(.orange)
                }
            }
            
            Text(address.formatted)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    NavigationStack {
        AddressesView()
    }
}
