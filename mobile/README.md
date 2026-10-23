# Studio for iOS

The iOS app for Studio, built with [Expo](https://expo.dev) and React Native. Navigation chrome uses real SwiftUI through [`@expo/ui/swift-ui`](https://docs.expo.dev/versions/latest/sdk/ui/swift-ui/). It talks to the same API as the web app.

What is in it: sign in and sign up, Create (Talking, Scene, stills), Faces, Voices (including voice cloning), Library, Billing with Apple in-app purchases, and push notifications.

## Requirements

- macOS with Xcode (for the iOS simulator or a device build)
- Node.js 20.19+ (or 22.12+)
- The Studio API running somewhere the phone can reach (see the [main README](../README.md))

The app uses native modules (StoreKit via `expo-iap`, `@expo/ui`, Sentry), so it needs a **development build**. Expo Go will not work.

## Run it

```bash
cd mobile
npm install
npx expo run:ios            # builds the native app and opens the simulator
# on a plugged-in iPhone:
npx expo run:ios --device
```

After the first build you can just start Metro with `npx expo start` and reopen the installed app.

## Point it at your API

By default the app uses the computer running Metro, on port 3001: `http://<your LAN IP>:3001/api`. That works if:

- the phone and computer are on the same network, and
- the API listens on all interfaces: `uvicorn app.main:app --host 0.0.0.0 --port 3001`

To use another API, copy `.env.example` to `.env` and set:

```bash
EXPO_PUBLIC_API_BASE_URL=https://api.your-domain.com/api
```

The sign-in screen footer shows which API URL is in use. If sign-in says it cannot reach the API, check your firewall allows port 3001.

Sign in with the local admin account from the main README (`admin@studio.local`).

## Checks

```bash
npx tsc --noEmit
```

## Building for TestFlight / the App Store

This repo does not include an Expo account link. To build with [EAS](https://docs.expo.dev/build/introduction/):

1. Change `ios.bundleIdentifier` (and `android.package`) in `app.json` from `com.example.studio.app` to your own.
2. Run `npm i -g eas-cli`, `eas login`, then `eas init` to link the project to your Expo account.
3. Set `EXPO_PUBLIC_API_BASE_URL` in `eas.json` to your API.
4. Run `eas build --profile production --platform ios`.

In-app purchase setup (product IDs, App Store Connect, server keys) is in [`docs/IOS_IAP.md`](../docs/IOS_IAP.md).

## Deep links

- Custom scheme: `studio://`, for example `studio://reset-password?token=...` and `studio://verify-email?token=...`
- Universal links use `applinks:example.com` in `app.json` and `frontend/public/apple-app-site-association`. Replace the domain and `YOUR_TEAM_ID` with yours.

## Layout

| Path | What |
|------|------|
| `app/` | Screens (Expo Router). `(public)` is signed out, `(app)` is signed in |
| `src/api` | API client and types |
| `src/auth` | Session storage and token refresh |
| `src/features` | Create, Home, and other feature code |
| `src/components` | Shared UI |
| `plugins/` | Expo config plugins |
| `patches/` | `patch-package` fixes applied on install |

Contributor notes (SwiftUI vs React Native, Create screen rules) are in [`AGENTS.md`](AGENTS.md).
