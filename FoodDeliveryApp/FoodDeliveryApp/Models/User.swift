import Foundation

struct User: Codable, Identifiable, Equatable {
    let id: String
    let email: String
    let phone: String?
    let name: String
    let avatarUrl: String?
    let createdAt: Date?
    
    static let preview = User(
        id: "1",
        email: "john@example.com",
        phone: "+1234567890",
        name: "John Doe",
        avatarUrl: nil,
        createdAt: Date()
    )
}
