import SwiftUI

struct PaymentMethodsView: View {
    @StateObject private var viewModel = ProfileViewModel()
    @State private var showAddPayment = false
    
    var body: some View {
        List {
            ForEach(viewModel.paymentMethods) { method in
                PaymentMethodRow(method: method)
            }
            
            Button {
                showAddPayment = true
            } label: {
                HStack {
                    Image(systemName: "plus.circle.fill")
                        .foregroundStyle(.orange)
                    Text("Add Payment Method")
                }
            }
        }
        .navigationTitle("Payment Methods")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showAddPayment) {
            AddPaymentMethodView()
        }
        .task {
            await viewModel.loadPaymentMethods()
        }
    }
}

struct PaymentMethodRow: View {
    let method: PaymentMethod
    
    var body: some View {
        HStack(spacing: 12) {
            // Card Icon
            Image(systemName: method.icon)
                .font(.title2)
                .foregroundStyle(.gray)
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
            
            if method.isDefault {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
            }
        }
    }
}

struct AddPaymentMethodView: View {
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Text("Add Payment Method")
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("Payment method integration would use Stripe SDK for secure card input")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                
                // Placeholder for Stripe card input
                VStack(spacing: 16) {
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color(.systemGray6))
                        .frame(height: 50)
                        .overlay {
                            Text("Card Number")
                                .foregroundStyle(.secondary)
                        }
                    
                    HStack(spacing: 16) {
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color(.systemGray6))
                            .frame(height: 50)
                            .overlay {
                                Text("MM/YY")
                                    .foregroundStyle(.secondary)
                            }
                        
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color(.systemGray6))
                            .frame(height: 50)
                            .overlay {
                                Text("CVC")
                                    .foregroundStyle(.secondary)
                            }
                    }
                }
                .padding()
                
                Spacer()
                
                Button {
                    dismiss()
                } label: {
                    Text("Add Card")
                        .fontWeight(.semibold)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.orange)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                }
                .padding()
            }
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

#Preview {
    NavigationStack {
        PaymentMethodsView()
    }
}
