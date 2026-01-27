import Foundation
import CoreLocation

struct Address: Codable, Identifiable, Equatable {
    let id: String
    let userId: String
    let label: String
    let street: String
    let apartment: String?
    let city: String
    let state: String
    let zipCode: String
    let latitude: Double?
    let longitude: Double?
    let isDefault: Bool
    
    var formatted: String {
        var address = street
        if let apt = apartment, !apt.isEmpty {
            address += ", \(apt)"
        }
        address += "\n\(city), \(state) \(zipCode)"
        return address
    }
    
    var oneLine: String {
        var address = street
        if let apt = apartment, !apt.isEmpty {
            address += ", \(apt)"
        }
        address += ", \(city), \(state) \(zipCode)"
        return address
    }
    
    var location: CLLocation? {
        guard let lat = latitude, let lng = longitude else { return nil }
        return CLLocation(latitude: lat, longitude: lng)
    }
    
    func toDeliveryAddress() -> DeliveryAddress {
        DeliveryAddress(
            street: street,
            apartment: apartment,
            city: city,
            state: state,
            zipCode: zipCode
        )
    }
    
    static let preview = Address(
        id: "1",
        userId: "1",
        label: "Home",
        street: "123 Main Street",
        apartment: "Apt 4B",
        city: "San Francisco",
        state: "CA",
        zipCode: "94102",
        latitude: 37.7749,
        longitude: -122.4194,
        isDefault: true
    )
    
    static let previews: [Address] = [
        preview,
        Address(
            id: "2",
            userId: "1",
            label: "Work",
            street: "456 Market Street",
            apartment: "Floor 10",
            city: "San Francisco",
            state: "CA",
            zipCode: "94103",
            latitude: 37.7899,
            longitude: -122.4000,
            isDefault: false
        )
    ]
}

struct CreateAddressRequest: Encodable {
    let label: String
    let street: String
    let apartment: String?
    let city: String
    let state: String
    let zipCode: String
    let latitude: Double?
    let longitude: Double?
    let isDefault: Bool
}
