import Foundation
import Combine

@MainActor
class AuthManager: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private var cancellables = Set<AnyCancellable>()
    
    init() {
        Task {
            await checkAuthStatus()
        }
    }
    
    func checkAuthStatus() async {
        if let token = await KeychainHelper.shared.get(forKey: "accessToken") {
            await APIClient.shared.setAuthToken(
                token,
                refresh: await KeychainHelper.shared.get(forKey: "refreshToken")
            )
            
            do {
                let user: User = try await APIClient.shared.request(endpoint: Endpoints.currentUser)
                self.currentUser = user
                self.isAuthenticated = true
            } catch {
                // Token expired or invalid
                await logout()
            }
        }
    }
    
    func login(email: String, password: String) async {
        isLoading = true
        errorMessage = nil
        
        struct LoginRequest: Encodable {
            let email: String
            let password: String
        }
        
        struct LoginResponse: Decodable {
            let user: User
            let accessToken: String
            let refreshToken: String
        }
        
        do {
            let response: LoginResponse = try await APIClient.shared.request(
                endpoint: Endpoints.login,
                method: .POST,
                body: LoginRequest(email: email, password: password)
            )
            
            await KeychainHelper.shared.save(response.accessToken, forKey: "accessToken")
            await KeychainHelper.shared.save(response.refreshToken, forKey: "refreshToken")
            await APIClient.shared.setAuthToken(response.accessToken, refresh: response.refreshToken)
            
            self.currentUser = response.user
            self.isAuthenticated = true
        } catch let error as APIError {
            self.errorMessage = error.errorDescription
        } catch {
            self.errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func register(name: String, email: String, phone: String, password: String) async {
        isLoading = true
        errorMessage = nil
        
        struct RegisterRequest: Encodable {
            let name: String
            let email: String
            let phone: String
            let password: String
        }
        
        struct RegisterResponse: Decodable {
            let user: User
            let accessToken: String
            let refreshToken: String
        }
        
        do {
            let response: RegisterResponse = try await APIClient.shared.request(
                endpoint: Endpoints.register,
                method: .POST,
                body: RegisterRequest(name: name, email: email, phone: phone, password: password)
            )
            
            await KeychainHelper.shared.save(response.accessToken, forKey: "accessToken")
            await KeychainHelper.shared.save(response.refreshToken, forKey: "refreshToken")
            await APIClient.shared.setAuthToken(response.accessToken, refresh: response.refreshToken)
            
            self.currentUser = response.user
            self.isAuthenticated = true
        } catch let error as APIError {
            self.errorMessage = error.errorDescription
        } catch {
            self.errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func logout() async {
        await KeychainHelper.shared.deleteAll()
        await APIClient.shared.setAuthToken(nil)
        
        currentUser = nil
        isAuthenticated = false
    }
    
    func updateProfile(name: String?, phone: String?) async {
        isLoading = true
        
        struct UpdateRequest: Encodable {
            let name: String?
            let phone: String?
        }
        
        do {
            let user: User = try await APIClient.shared.request(
                endpoint: Endpoints.currentUser,
                method: .PUT,
                body: UpdateRequest(name: name, phone: phone)
            )
            self.currentUser = user
        } catch let error as APIError {
            self.errorMessage = error.errorDescription
        } catch {
            self.errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
}
