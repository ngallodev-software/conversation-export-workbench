# iOS distribution

The Capacitor iOS project can be generated from `mobile/` with:

```bash
cd mobile
npm install
npm run build
npx cap add ios
npx cap sync ios
```

A simulator build does not require Apple signing and is built in release CI for structural validation.

An installable iPhone/iPad build requires Apple signing. For TestFlight/App Store distribution, configure an Apple Developer team, a matching App Store Connect app/bundle ID, a distribution certificate, and an App Store Connect provisioning profile. The release pipeline intentionally does not publish an unsigned IPA as if it were installable.
