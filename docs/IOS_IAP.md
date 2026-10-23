# iOS In-App Purchases (StoreKit)

Studio sells **digital plans and credit packs**. On the App Store these must use **Apple IAP**, not Stripe Checkout inside the app.

Web continues to use Stripe. Both paths grant the same entitlements on the server.

## Architecture

```
iOS app (expo-iap / StoreKit 2)
  → purchase
  → POST /api/billing/iap/confirm { workspace_id, apple_product_id, transaction_id, signed_transaction }
  → server verifies (App Store Server API when configured)
  → plan upgrade or credit pack grant (same as Stripe webhooks)
```

Product IDs (create in App Store Connect). Reference name is only unique in
Connect. The app matches Product ID.

| Reference name | Product ID | Type | Maps to |
|----------------|------------|------|---------|
| `starter_monthly` | `com.example.studio.sub.starter` | Auto-renewable sub | plan `starter` |
| `creator_monthly` | `com.example.studio.sub.creator` | Auto-renewable sub | plan `creator` |
| `studio_monthly` | `com.example.studio.sub.studio` | Auto-renewable sub | plan `studio` |
| `video_10_credits` | `com.example.studio.credit.video_10` | Consumable | pack `video_10` |
| `video_25_credits` | `com.example.studio.credit.video_25` | Consumable | pack `video_25` |
| `image_50_credits` | `com.example.studio.credit.image_50` | Consumable | pack `image_50` |
| `voice_30m_credits` | `com.example.studio.credit.voice_30m` | Consumable | pack `voice_30m` |

Retired. Not for sale. Keep in App Store Connect so unfinished purchases still
confirm. Do not reuse these Product IDs.

| Reference name | Product ID | Maps to |
|----------------|------------|---------|
| `lipsync_10_credits` | `com.example.studio.credit.lipsync_10` | pack `lipsync_10` (leftover clip credits) |
| `scripts_25_credits` | `com.example.studio.credit.scripts_25` | pack `scripts_25` |
| `creator_burst_credits` | `com.example.studio.credit.creator_burst` | pack `creator_burst` |

Leave unused: `com.example.studio.plan.*` (Non-Consumable, burned) and `com.example.studio.pack.*`
(old consumable drafts). Do not submit them. Do not reuse reference names
`starter`, `creator`, `studio`, `video_10`, `video_25`, `image_50`, `lipsync_10`,
`voice_30m`, `scripts_25`, or `creator_burst`.

Put the three plans in **one subscription group**, duration **1 month**.

## Server env

```bash
APPLE_IAP_BUNDLE_ID=com.example.studio.app
APPLE_IAP_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
APPLE_IAP_KEY_ID=XXXXXXXXXX
APPLE_IAP_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
# Local only (never production):
APPLE_IAP_ALLOW_UNVERIFIED=true
```

Create an **In-App Purchase** key in App Store Connect → Users and Access → Integrations → In-App Purchase.

## App Store Server Notifications V2

Point both Production and Sandbox notification URLs to:

```text
https://api.example.com/api/billing/iap/notifications
```

The handler updates plan status for renewals, cancels, refunds, and billing retries using `originalTransactionId` stored as `apple:{id}` on the subscription row.

## App

- Paywall: `/(app)/billing` (Profile → Upgrade / Billing)
- Uses `expo-iap` (native StoreKit). **Does not work in Expo Go** — use:

```bash
cd mobile
eas build --profile development --platform ios
# or production / TestFlight
eas build --profile production --platform ios
```

## Migrations

```bash
cd backend
alembic upgrade head   # includes 0027 push, 0028 iap, 0029 simplified plans
```

## Notes

- Stripe remains for web and Customer Portal.
- Do not offer Stripe Checkout for digital goods inside the iOS binary.
- RevenueCat is optional; this stack talks to StoreKit directly.
