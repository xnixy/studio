# Mobile agent notes (Studio)

## SwiftUI vs React Native

Both are in play. Picking wrong causes silent blank areas, not build errors.

- **SwiftUI (`@expo/ui/swift-ui`) for navigation chrome only:** liquid-glass
  stack headers, SF Symbols. These own a whole surface and size themselves.
- **RN + `GlassCard` for content sections.** Anything inside a `Screen` scroll view.
- **Never put a SwiftUI `Form` inside `Screen`.** A `Form` is a fill-parent scroll
  container with no intrinsic size, so `Host matchContents` measures it near zero and
  the tree renders as an empty void. This shipped twice on You (Account and
  Delete account both blank) before it was caught. `useViewportSizeMeasurement` is for
  a `Host` that owns the full screen, nothing less.
- Text fields inside a SwiftUI `Host`: `useNativeState` + `text={state}`, not React state.
- Pickers: children `Text` with the `tag(value)` modifier; see `src/components/TaggedPicker.tsx`.
- Media: RN islands (`expo-image`, `expo-video`) outside or as siblings of a `Host`.

## Navigation

- Root stack (`app/_layout.tsx`) uses `animation: "none"`. Every move at that level is
  an auth-gate swap, not navigation; animating it slid the app in from the right on launch.
- Wrap the tree in React Navigation `ThemeProvider` with `studioNavigationTheme`. Card
  and background must be the canvas (`#050508` / `#E8ECF4`), never DefaultTheme white.
  `liquidGlassStackHeaderOptions` keeps a transparent header but must still set
  `contentStyle` to the canvas. Skipping either is the white splash on Back.
  The status bar is translucent so the canvas and scrolled clips show through.
  Header-less Home uses `Screen` `safeTop` to pad scroll *content* (not the
  screen root) so "Hey" starts below the icons, then slides under the bar.
  Home also sets `scrollEdgeEffects.top: hidden` so iOS 26 does not paint a
  glass plate over the clock on scroll.
- Public pages use the transparent glass header with the hero carrying the title.
  `verify-email` is the one exception still on a solid bar (its SwiftUI `Form` needs it).
- **Deep-link params are one-shot.** `play.tsx` applies each inbound batch once and then
  clears it with `router.setParams`. Params used to replay on every tab refocus and
  overwrite later user choices, and re-writing them into `sessionStorage` destroyed the
  value Voices had just saved. Any new param consumer must follow the same pattern.

## Create screen contract

- Talking is **one box** plus a draft card. State may still hold the joined
  `scene. says: line` form. Bubbles, Library, Home, and Copy show
  `promptForDisplay` / `avatarPromptPreview`. The live field uses
  `avatarPromptForField` so inbound drafts hide `says:` without re-running
  scene cleanup on every keystroke (that trim ate trailing spaces). Users
  never type or read `says:`. Assist extracts `and says` / `she says` / quotes into
  the draft line on the server. The live field does not parse those forms.
  Two quoted speakers, or a friend who replies, is Scene. Both lines stay in
  SCENE. Do not extract the first into They say.
- `splitAvatarPrompt` / `joinAvatarPrompt` in `createConstants.ts` mirror the backend
  `split_avatar_user_prompt`. If one side changes, change both. Note the backend returns
  `(spoken, scene)` in that order.
- Eyeline is a backend house rule (ADDRESS). Assist also adds one short look sentence
  to the draft scene when a listener is in it. Solo Talking must not name a friend
  in SPEAKER. That invented extras. Do not bake "looks at camera" into Talking scene
  copy unless the clip is a presenter talking to the viewer. Conversation scenes
  look at the other person. Assist writes one short default shot on Talking
  (eye-level, face large) unless they named a camera. Do not ask the user for
  camera notes.
- Sample fill goes through `fillSamplePrompt` so a mode switch can clear it.
  Example taps must not add a starter face.
- Create tabs are Clip | Still. Kind (Talking / Scene) is
  confirmed on the draft card. Library filters and `generationKindLabel` use
  those same names. `modeUsesAssist` is always true. Chip taps never
  call the model.
- Face and voice wait until generate, after kind is known. Do not disable Send
  for a missing Face while kind is still unknown. Talking
  needs a face then. A client Assist miss must not spend. Send again retries
  the helper. Do not mark Assist ready on that miss. Voice
  default is the Voices pick. If none is saved: clone, then Jessica. When a
  Face is on the clip, that Face's bound voice wins over a leftover chip,
  except on Revoice and Extend. Switching to an unbound Face restores the
  Voices fallback. Only set the chip to a bind that is in the Voices list.
  Do not leave it empty. Cost line prefers `POST /play/quote`.
  Create shows featured five plus the current pick as names on the Voice
  control. Full hosted catalog (search, gender, accent) lives on Voices.
  One take is 15s Fast / 30s on 2.5. Longer
  is Extend. Draft-card Generate uses the same `onSend` path.
- Talking + clone spends clip credits and voiceover seconds. Show that
  on the cost line. Scene with a Face, a spoken line, and a clone spends
  clip credits plus voice seconds. Hide clones on Scene until
  a Face is selected. Face lines use that Face's bound voice if set, else
  the picker. Anyone else gets a different built-in.
- Talking is Face plus TTS plus Seedance. Named place goes
  in SCENE. Hidden clip still is server-side. Clip has no Options. Still Fast / Quality lives in
  the native header. The composer is an iMessage bar: plus (refs) left of the
  field, Face inside the pill, Voice then Send on the right. Length and credits
  sit on the user bubble, not under the field.
  The prompt `TextInput` grows via `onContentSizeChange` on a wrap view, not
  via `height` on the field (iPad then never grows). Cap 120 on phone, 200 on
  iPad. Do not put `flex: 1` on the multiline field. Ignore `onContentSizeChange`
  on the focus frame. iPad reports a huge height there and the pill jumps.
  Generate clears the prompt
  and sets `editable={false}` together, and iOS then grows the native view to
  the window for a frame.
  Create lifts the absolute composer by keyboard overlap (`windowHeight -
  screenY`), not raw keyboard height. Native stack avoidance does not move
  that overlay. Leaving it native-only hid the field under the keyboard.
  Set `keyboardHandlingEnabled: false` on the Create screen so a later
  native inset cannot double-count. `padBottom` is 8 while the keyboard is
  up, home indicator when it is down. Keep ignoring `onContentSizeChange`
  on the focus frame.
- Duration and speech estimates must match the backend formula (`words / 2.4 + 1`)
  **after** `expandSpokenDomains`. Talking Fast clamps 4..15. Over 15s uses 2.5
  up to 30s. Assist picks the lane. Do not ask Fast vs 2.5
  on every short clip.
- Talking auto length follows TTS. Seedance 2.5 goes to 30s. Fast stays 15s.
  2.5 max is 720p. 1080p and 4k only on Fast.
- One idempotency key per draft, held across retries and cleared on success, New,
  mode change, **voice** change, and **Face** change. A leftover key after New can dedupe the wrong prompt.
- Clip models are Seedance only. All of them take a face.
- Voice control opens the same name strip as Talking. Clones show once a Face is on.
- Extend is Seedance: prior clip as `@Video1`, new TTS as `@Audio1`. Fast extends
  a 15s take. 2.5 extends a 30s take. Each card is a new take. Unlock Talking
  and Talking extend. Seedance has no voice id. The MP3 plus `@Audio1 defines`
  voice and words is the lock. Do not re-quote the line for Seedance to invent.
- Thread clip cards use `threadClipCardWidth`: 9:16 stays phone-narrow (~228px),
  1:1 a bit wider. Cover-crop, poster first, no native video controls. A wide
  88% card with maxHeight letterboxes vertical clips.

## Home, You, and Welcome

- There is no tab bar. Home (`app/(app)/index.tsx`) is the signed-in root.
  Clip, Still, Faces, Voices, Library, Billing, and You all push from Home.
  Do not put NativeTabs back. Do not put Clip | Still in the Create header.
- Home is the last clip (phone hero, muted loop), a **Recent** strip whose
  count and thumb size come from the width on screen (about 4 on a modern
  iPhone, more on iPad), and a thumb-zone compose tray: Faces then Clip and Still.
  Greeting is Hey plus Account (`person.circle`). Faces and Voices are iOS-style
  buttons under the credit chips. Library is **See All** on Recent, not a text
  label in the corner. Talking / Scene chips open Billing. No Examples
  rail. No studio tiles at the top. No Voices glyph on the Face rail. Voice bind
  is Faces (Voice on the card), Face edit (Choose voice), or Voices (tap a voice,
  pick a Face). Empty Faces: "Add a Face. That is who talks." Bound voice name
  (or "No voice") sits under the Face circle.
  On iPhone and iPad the compose tray is a floating dock (inset sides, rounded,
  sits above the home indicator). Do not stretch it edge to edge on the phone.
  Max width 520. Gate iPad hero size on `Platform.isPad`. Pass `safeBottom={false}`
  on Home Screen so the tray owns the home-indicator inset.
- Faces and Library grids use `fitGrid` (`minCell` ~108). Phone is 3 columns,
  iPad adds columns instead of stretching two giant tiles. Do not pin 2 columns.
- You (Account) is account, plan, and legal. No Clip / Still / Library / Faces / Voices
  on that screen. Home opens it as Account.
- Signed-out Welcome: Sign in, Create account.
- Library grid cards use `HomePosterCard` (full-bleed glass poster + title and caption,
  16:10 media). Do not mix padded GlassCard thumbs with raw ExpoImage posters.
- Prefetch gens / faces / billing in `usePrefetchHomeData` once the workspace id
  exists and belongs to the signed-in user. Last-used storage must store user id
  plus workspace id. A leftover id from the previous account is how Home still
  showed that account's clips after sign-out. Home and Library share
  `fetchPlayGenerationsList` and `playGenerationsKey`. Never use a short Home
  limit that overwrites the Library cache.
- Logout, login, and register must `queryClient.clear()` and drop workspace /
  Face / Voice / play idempotency prefs. Do not keep the last workspace id in
  React state after the user id changes.

## First paint and lists

- Empty states wait until the query has data or has settled (`isPending` is false).
  Missing data is not empty. Home chrome (greeting) does not wait on workspace.
- Reserve layout: skeleton cards that match final size, or keep chrome and fill
  in place. Do not flash empty copy, a Create CTA, or a mid-page spinner that
  then grows into content.
- Lists use `MediaThumb` stills only. No video players in scroll rails or grids.
  Home's single hero may muted-loop while focused. The recents filmstrip stays
  stills. `recyclingKey` / `mediaStableKey` keep signed posters from flashing. List thumbs
  use `transition={0}`. Face portraits may `contentPosition="top"`.
- `staleTime` on workspace lists so tab refocus does not reload-flash. Pull to
  refresh uses a local `pullRefreshing` flag only. Query `isFetching` on focus
  freezes iOS RefreshControl.

## Push

- Payload carries `asset_id` and `href` `/clips/{id}`. Parse a full UUID, not a
  loose `/clips/` prefix. Tap handling must not replay
  `getLastNotificationResponseAsync` if a live tap already opened a clip, or if
  that last response is older than ~45s (it is sticky across launches).
- Clip detail `id` can be a string array when the stack is reused; use the last
  value. Do not prompt for permission at login; ask after the first successful
  generate (`ensurePushRegistration`). Unregister the token in logout before
  `clearSession`.

## API

- Always send `X-Studio-Client: mobile`. Tokens in SecureStore, prefs in AsyncStorage.
- Signed media URLs carry `?exp=` and expire in two hours. Never pin one in long-lived
  state; refetch the generation (`freshPlayMediaUrl` / `getPlayGeneration`) when
  `isSignedMediaUrlExpired` is true, including clip detail after it is already ready.
- Register reads `GET /public/config` `turnstile_required`. If false, skip Turnstile.
  If the widget or config fails while required, offer Retry, not a dead form.
- Offline is API reachability (`markNetworkOnline` / `markNetworkOffline` in the
  client), not NetInfo. `OfflineBanner` sits in the root layout. Create send and
  draft Generate must refuse when offline.

## Copy

- Match root `AGENTS.md` tone: no em or en dashes, no marketing fluff, short and concrete.
- The library is **Library**, not Clips: it holds Talking, Scene, and
  stills. It lives on You. Routes and filenames still say `clips` so existing
  links resolve.
- Faces are upload, generate, or edit. No starter library. Face rows share
  `play_mode: avatar` with talking clips and have no voice; never purge
  talking by empty voice without excluding `face_library` /
  `avatar_source_image`. Keep Faces head-and-shoulders, not full-body.
  A full-figure plate makes Seedance compose tiny-face street shots.
  Face edit compare is a drag wipe on the photo (`BeforeAfterCompare`),
  capped at 320pt. Do not use Before / Split / After chips or a full-bleed
  iPad square. The divider is the control. Register `face-edit` in the
  stack like the other screens.
  Wardrobe lives on the look unless the prompt names
  clothes. Talking + clone is TTS then Seedance, one clip. One clone
  per workspace. Bind wins over a leftover chip. Do not persist bind as the
  Voices default. A stale bind falls back to the chip, then Jessica.

## VoiceOver

- Icon-only and chip controls need `accessibilityRole="button"` plus
  `accessibilityLabel`. Selected chips also need `accessibilityState={{ selected }}`.
  Visible text on a Pressable is not enough for send, face, ref, and filter chips.

## Voice clone

- Language list and read-aloud scripts live in `src/lib/cloneVoice.ts`. Mirror
  `frontend/src/features/play/cloneVoice.ts` and `backend/app/clone_languages.py`.
  Record languages are the 32 Instant Voice Clone set. Clone TTS is Eleven v3.
- Recordings go through `prepareCloneAudioFile` so uploadAsync has a real
  `.wav`/`.m4a`/`.caf` filename. In-app record uses `cloneRecordingOptions`
  (flattened native options; iOS WAV / Linear PCM). Nested `RecordingPresets`
  keys never reach AVAudioRecorder. The API transcodes to WAV before ElevenLabs.

## Housekeeping

- Soft file size ~250 lines; split screens as they grow.
- `npx tsc --noEmit` before claiming done. Fast Refresh shows stale errors mid-edit, so
  relaunch the app (`xcrun simctl terminate` + `launch`) before trusting a red screen.
- After bumping `react-native-worklets` or Reanimated, stop Metro and
  `npx expo start -c`. A stale cache keeps the old Babel plugin
  (`0.10.0` vs `0.10.1`) and `_layout.tsx` then looks like it is missing
  a default export. That is the worklets throw on import, not a missing
  `export default`.
- Running the app needs a dev build, not Expo Go (StoreKit via `expo-iap`, `@expo/ui`,
  Sentry). See `README.md` for the full local setup.
- Local Xcode has no Sentry org, so source-map upload fails the bundle script.
  `SENTRY_DISABLE_AUTO_UPLOAD=true` lives in `ios/.xcode.env` via
  `plugins/withSentryDisableAutoUpload.js`. EAS sets the same env in `eas.json`.
