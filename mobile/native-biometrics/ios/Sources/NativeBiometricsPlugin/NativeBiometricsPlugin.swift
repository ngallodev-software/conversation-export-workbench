import Capacitor
import LocalAuthentication

@objc(NativeBiometricsPlugin)
public class NativeBiometricsPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "NativeBiometricsPlugin"
    public let jsName = "NativeBiometrics"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "isAvailable", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "authenticate", returnType: CAPPluginReturnPromise)
    ]

    @objc public func isAvailable(_ call: CAPPluginCall) {
        let context = LAContext()
        var error: NSError?
        let available = context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error)
        call.resolve([
            "available": available,
            "biometryType": biometryName(context.biometryType)
        ])
    }

    @objc public func authenticate(_ call: CAPPluginCall) {
        let context = LAContext()
        context.localizedCancelTitle = "Use PIN"
        var authError: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &authError) else {
            call.reject(authError?.localizedDescription ?? "Biometric authentication is unavailable")
            return
        }
        context.evaluatePolicy(
            .deviceOwnerAuthenticationWithBiometrics,
            localizedReason: "Unlock your local conversation archive"
        ) { success, error in
            DispatchQueue.main.async {
                if success {
                    call.resolve(["authenticated": true])
                } else {
                    call.reject(error?.localizedDescription ?? "Biometric authentication failed")
                }
            }
        }
    }

    private func biometryName(_ type: LABiometryType) -> String {
        switch type {
        case .faceID: return "face"
        case .touchID: return "fingerprint"
        case .opticID: return "optic"
        default: return "none"
        }
    }
}
