import SwiftUI

struct SignUpView: View {
    @EnvironmentObject var authManager: AuthManager
    @Environment(\.dismiss) var dismiss
    
    @State private var name = ""
    @State private var email = ""
    @State private var phone = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var agreeToTerms = false
    
    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Header
                VStack(spacing: 8) {
                    Text("Create Account")
                        .font(.title)
                        .fontWeight(.bold)
                    
                    Text("Sign up to get started")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 20)
                
                // Form Fields
                VStack(spacing: 16) {
                    FormField(title: "Full Name", text: $name, placeholder: "Enter your name")
                        .textContentType(.name)
                    
                    FormField(title: "Email", text: $email, placeholder: "Enter your email")
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                    
                    FormField(title: "Phone Number", text: $phone, placeholder: "+1 (555) 000-0000")
                        .textContentType(.telephoneNumber)
                        .keyboardType(.phonePad)
                    
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Password")
                            .font(.subheadline)
                            .fontWeight(.medium)
                        
                        SecureField("Create a password", text: $password)
                            .textFieldStyle(CustomTextFieldStyle())
                            .textContentType(.newPassword)
                    }
                    
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Confirm Password")
                            .font(.subheadline)
                            .fontWeight(.medium)
                        
                        SecureField("Confirm your password", text: $confirmPassword)
                            .textFieldStyle(CustomTextFieldStyle())
                            .textContentType(.newPassword)
                    }
                    
                    if !password.isEmpty && !confirmPassword.isEmpty && password != confirmPassword {
                        Text("Passwords do not match")
                            .font(.caption)
                            .foregroundStyle(.red)
                    }
                    
                    // Password Requirements
                    if !password.isEmpty {
                        PasswordRequirementsView(password: password)
                    }
                }
                .padding(.horizontal)
                
                // Terms Agreement
                HStack(alignment: .top, spacing: 12) {
                    Button {
                        agreeToTerms.toggle()
                    } label: {
                        Image(systemName: agreeToTerms ? "checkmark.square.fill" : "square")
                            .foregroundStyle(agreeToTerms ? .orange : .gray)
                            .font(.title3)
                    }
                    
                    Text("I agree to the ")
                        .foregroundStyle(.secondary)
                    + Text("Terms of Service")
                        .foregroundStyle(.orange)
                    + Text(" and ")
                        .foregroundStyle(.secondary)
                    + Text("Privacy Policy")
                        .foregroundStyle(.orange)
                }
                .font(.subheadline)
                .padding(.horizontal)
                
                // Error Message
                if let error = authManager.errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal)
                }
                
                // Sign Up Button
                Button {
                    Task {
                        await authManager.register(
                            name: name,
                            email: email,
                            phone: phone.isEmpty ? nil : phone,
                            password: password
                        )
                    }
                } label: {
                    HStack {
                        if authManager.isLoading {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text("Create Account")
                                .fontWeight(.semibold)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(isFormValid ? Color.orange : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                .disabled(!isFormValid || authManager.isLoading)
                .padding(.horizontal)
                
                // Sign In Link
                HStack {
                    Text("Already have an account?")
                        .foregroundStyle(.secondary)
                    Button("Sign In") {
                        dismiss()
                    }
                    .fontWeight(.semibold)
                    .foregroundStyle(.orange)
                }
                .font(.subheadline)
                .padding(.bottom, 32)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
    }
    
    private var isFormValid: Bool {
        !name.isEmpty &&
        !email.isEmpty &&
        email.contains("@") &&
        password.count >= 6 &&
        password == confirmPassword &&
        agreeToTerms
    }
}

struct FormField: View {
    let title: String
    @Binding var text: String
    let placeholder: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline)
                .fontWeight(.medium)
            
            TextField(placeholder, text: $text)
                .textFieldStyle(CustomTextFieldStyle())
        }
    }
}

struct PasswordRequirementsView: View {
    let password: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            RequirementRow(
                text: "At least 6 characters",
                isMet: password.count >= 6
            )
            RequirementRow(
                text: "Contains a number",
                isMet: password.contains(where: { $0.isNumber })
            )
            RequirementRow(
                text: "Contains uppercase letter",
                isMet: password.contains(where: { $0.isUppercase })
            )
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

struct RequirementRow: View {
    let text: String
    let isMet: Bool
    
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: isMet ? "checkmark.circle.fill" : "circle")
                .foregroundStyle(isMet ? .green : .gray)
                .font(.caption)
            
            Text(text)
                .font(.caption)
                .foregroundStyle(isMet ? .primary : .secondary)
        }
    }
}

#Preview {
    NavigationStack {
        SignUpView()
            .environmentObject(AuthManager())
    }
}
