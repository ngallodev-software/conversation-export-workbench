package software.ngallodev.cew.biometrics;

import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.FragmentActivity;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.util.concurrent.Executor;

@CapacitorPlugin(name = "NativeBiometrics")
public class NativeBiometricsPlugin extends Plugin {
    private static final int AUTHENTICATORS = BiometricManager.Authenticators.BIOMETRIC_STRONG;

    @PluginMethod
    public void isAvailable(PluginCall call) {
        int result = BiometricManager.from(getContext()).canAuthenticate(AUTHENTICATORS);
        JSObject ret = new JSObject();
        ret.put("available", result == BiometricManager.BIOMETRIC_SUCCESS);
        ret.put("status", result);
        call.resolve(ret);
    }

    @PluginMethod
    public void authenticate(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            if (!(getActivity() instanceof FragmentActivity)) {
                call.reject("Biometric authentication requires a FragmentActivity");
                return;
            }
            int result = BiometricManager.from(getContext()).canAuthenticate(AUTHENTICATORS);
            if (result != BiometricManager.BIOMETRIC_SUCCESS) {
                call.reject("Biometric authentication is unavailable", Integer.toString(result));
                return;
            }

            FragmentActivity activity = (FragmentActivity) getActivity();
            Executor executor = ContextCompat.getMainExecutor(getContext());
            BiometricPrompt prompt = new BiometricPrompt(activity, executor,
                new BiometricPrompt.AuthenticationCallback() {
                    @Override
                    public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
                        super.onAuthenticationSucceeded(result);
                        JSObject ret = new JSObject();
                        ret.put("authenticated", true);
                        call.resolve(ret);
                    }

                    @Override
                    public void onAuthenticationError(int errorCode, CharSequence errString) {
                        super.onAuthenticationError(errorCode, errString);
                        call.reject(errString.toString(), Integer.toString(errorCode));
                    }
                });

            BiometricPrompt.PromptInfo info = new BiometricPrompt.PromptInfo.Builder()
                .setTitle("Unlock Conversation Export Workbench")
                .setSubtitle("Use your device biometrics to unlock the local archive")
                .setNegativeButtonText("Use PIN")
                .setAllowedAuthenticators(AUTHENTICATORS)
                .build();
            prompt.authenticate(info);
        });
    }
}
