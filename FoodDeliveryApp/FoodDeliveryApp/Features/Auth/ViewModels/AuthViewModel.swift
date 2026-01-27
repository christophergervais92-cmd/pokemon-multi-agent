import Foundation
import Combine

// The AuthManager already handles all auth functionality
// This file provides additional auth-related utilities

extension AuthManager {
    func validateEmail(_ email: String) -> Bool {
        let emailRegex = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        let emailPredicate = NSPredicate(format: "SELF MATCHES %@", emailRegex)
        return emailPredicate.evaluate(with: email)
    }
    
    func validatePassword(_ password: String) -> PasswordValidation {
        PasswordValidation(
            hasMinLength: password.count >= 6,
            hasNumber: password.contains(where: { $0.isNumber }),
            hasUppercase: password.contains(where: { $0.isUppercase }),
            hasLowercase: password.contains(where: { $0.isLowercase })
        )
    }
    
    func validatePhone(_ phone: String) -> Bool {
        let phoneRegex = "^[+]?[0-9]{10,14}$"
        let phonePredicate = NSPredicate(format: "SELF MATCHES %@", phoneRegex)
        let cleanedPhone = phone.replacingOccurrences(of: "[^0-9+]", with: "", options: .regularExpression)
        return phonePredicate.evaluate(with: cleanedPhone)
    }
}

struct PasswordValidation {
    let hasMinLength: Bool
    let hasNumber: Bool
    let hasUppercase: Bool
    let hasLowercase: Bool
    
    var isValid: Bool {
        hasMinLength && hasNumber
    }
    
    var isStrong: Bool {
        hasMinLength && hasNumber && hasUppercase && hasLowercase
    }
}
