import { registerPlugin } from '@capacitor/core';

export const NativeBiometrics = registerPlugin('NativeBiometrics', {
  web: () => Promise.resolve({
    isAvailable: async () => ({ available: false }),
    authenticate: async () => { throw new Error('Native biometrics are unavailable on web'); },
  }),
});
