import SwiftUI

struct ItemCustomizationSheet: View {
    let item: MenuItem
    let restaurant: Restaurant
    
    @EnvironmentObject var cartManager: CartManager
    @Environment(\.dismiss) var dismiss
    
    @State private var quantity = 1
    @State private var selectedOptions: [String: [MenuItemOptionChoice]] = [:]
    @State private var specialNotes = ""
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 0) {
                    // Item Image
                    if let imageUrl = item.imageUrl {
                        AsyncImage(url: URL(string: imageUrl)) { image in
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                        } placeholder: {
                            Rectangle()
                                .fill(Color(.systemGray5))
                        }
                        .frame(height: 200)
                        .clipped()
                    }
                    
                    VStack(alignment: .leading, spacing: 16) {
                        // Item Info
                        VStack(alignment: .leading, spacing: 8) {
                            Text(item.name)
                                .font(.title2)
                                .fontWeight(.bold)
                            
                            if let description = item.description {
                                Text(description)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                            
                            Text(item.priceFormatted)
                                .font(.title3)
                                .fontWeight(.semibold)
                        }
                        .padding()
                        
                        // Options
                        if let options = item.options, !options.isEmpty {
                            ForEach(options) { option in
                                OptionSection(
                                    option: option,
                                    selectedChoices: selectedOptions[option.id] ?? [],
                                    onSelectionChange: { choices in
                                        selectedOptions[option.id] = choices
                                    }
                                )
                            }
                        }
                        
                        // Special Notes
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Special Instructions")
                                .font(.headline)
                            
                            TextField("Add a note (allergies, preferences...)", text: $specialNotes, axis: .vertical)
                                .textFieldStyle(.roundedBorder)
                                .lineLimit(3...5)
                        }
                        .padding()
                        
                        // Quantity Selector
                        HStack {
                            Text("Quantity")
                                .font(.headline)
                            
                            Spacer()
                            
                            QuantitySelector(quantity: $quantity)
                        }
                        .padding()
                    }
                }
            }
            .safeAreaInset(edge: .bottom) {
                // Add to Cart Button
                VStack(spacing: 0) {
                    Divider()
                    
                    Button {
                        addToCart()
                    } label: {
                        HStack {
                            Text("Add to Cart")
                                .fontWeight(.semibold)
                            Spacer()
                            Text(totalPriceFormatted)
                                .fontWeight(.bold)
                        }
                        .padding()
                        .background(canAddToCart ? Color.orange : Color.gray)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                    }
                    .disabled(!canAddToCart)
                    .padding()
                    .background(Color(.systemBackground))
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.gray)
                            .font(.title2)
                    }
                }
            }
        }
    }
    
    private var canAddToCart: Bool {
        guard let options = item.options else { return true }
        
        for option in options where option.required {
            guard let selected = selectedOptions[option.id], !selected.isEmpty else {
                return false
            }
        }
        return true
    }
    
    private var totalPrice: Decimal {
        var price = item.price
        for (_, choices) in selectedOptions {
            for choice in choices {
                price += choice.price
            }
        }
        return price * Decimal(quantity)
    }
    
    private var totalPriceFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        return formatter.string(from: totalPrice as NSDecimalNumber) ?? "$\(totalPrice)"
    }
    
    private func addToCart() {
        cartManager.addItem(
            item,
            quantity: quantity,
            options: selectedOptions,
            notes: specialNotes.isEmpty ? nil : specialNotes,
            fromRestaurant: restaurant
        )
        dismiss()
    }
}

struct OptionSection: View {
    let option: MenuItemOption
    let selectedChoices: [MenuItemOptionChoice]
    let onSelectionChange: ([MenuItemOptionChoice]) -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(option.name)
                    .font(.headline)
                
                if option.required {
                    Text("Required")
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(4)
                }
                
                Spacer()
                
                if option.type == .multiple, let max = option.maxSelect {
                    Text("Choose up to \(max)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            
            VStack(spacing: 0) {
                ForEach(option.choices) { choice in
                    OptionChoiceRow(
                        choice: choice,
                        isSelected: selectedChoices.contains { $0.id == choice.id },
                        selectionType: option.type,
                        onTap: {
                            handleSelection(choice)
                        }
                    )
                    
                    if choice.id != option.choices.last?.id {
                        Divider()
                            .padding(.leading, 40)
                    }
                }
            }
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
        .padding()
    }
    
    private func handleSelection(_ choice: MenuItemOptionChoice) {
        var newSelection = selectedChoices
        
        if option.type == .single {
            // Single selection - replace
            newSelection = [choice]
        } else {
            // Multiple selection
            if let index = newSelection.firstIndex(where: { $0.id == choice.id }) {
                newSelection.remove(at: index)
            } else {
                if let max = option.maxSelect, newSelection.count >= max {
                    return // Can't select more
                }
                newSelection.append(choice)
            }
        }
        
        onSelectionChange(newSelection)
    }
}

struct OptionChoiceRow: View {
    let choice: MenuItemOptionChoice
    let isSelected: Bool
    let selectionType: MenuItemOption.OptionType
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack {
                Image(systemName: isSelected ? selectedIcon : unselectedIcon)
                    .foregroundStyle(isSelected ? .orange : .gray)
                
                Text(choice.name)
                    .foregroundStyle(.primary)
                
                Spacer()
                
                if choice.price > 0 {
                    Text(choice.priceText)
                        .foregroundStyle(.secondary)
                }
            }
            .padding()
        }
    }
    
    private var selectedIcon: String {
        selectionType == .single ? "circle.inset.filled" : "checkmark.square.fill"
    }
    
    private var unselectedIcon: String {
        selectionType == .single ? "circle" : "square"
    }
}

struct QuantitySelector: View {
    @Binding var quantity: Int
    
    var body: some View {
        HStack(spacing: 16) {
            Button {
                if quantity > 1 {
                    quantity -= 1
                }
            } label: {
                Image(systemName: "minus.circle.fill")
                    .font(.title2)
                    .foregroundStyle(quantity > 1 ? .orange : .gray)
            }
            .disabled(quantity <= 1)
            
            Text("\(quantity)")
                .font(.title3)
                .fontWeight(.semibold)
                .frame(minWidth: 30)
            
            Button {
                if quantity < 99 {
                    quantity += 1
                }
            } label: {
                Image(systemName: "plus.circle.fill")
                    .font(.title2)
                    .foregroundStyle(.orange)
            }
        }
    }
}

#Preview {
    ItemCustomizationSheet(item: .preview, restaurant: .preview)
        .environmentObject(CartManager())
}
