# Agent / contributor conventions (Studio)

## Soft line-length budget for source files

Keep modules readable and reviewable:

| Target | Guidance |
|--------|----------|
| **Ideal** | **~250 lines** per file |
| **Soft max** | **~500 lines** per file |
| **Hard review** | Above ~500 lines, prefer splitting before adding more logic |

These are **soft** caps (not lint-enforced). Exceptions are fine for generated code, dense data tables, or a short-lived extraction. Prefer domain splits with a re-export hub so call sites stay stable (`from app.schemas import X`, `from app.models import User`).

### When adding features

1. Put new types/routes next to their domain module when it already exists.
2. If a file is already near 500 lines, extract helpers or a sibling route module first.
3. Prefer `package/` with `__init__.py` re-exports over one growing monolith.

### Already split (examples)

- `backend/app/schemas/` — Pydantic DTOs by domain  
- `backend/app/models/` — SQLAlchemy models by domain  
- `backend/app/routers/video*.py` — video API by concern  

## Backend notes

- Keep OpenAPI import-safe: schema modules must import every type they annotate (e.g. `ContactTopic` from `common`).
- Shut down Redis clients with `aclose(close_connection_pool=True)` during lifespan stop so reloads stay quiet.
- Run `uv run pytest -q` before claiming done. Introspecting routers by importing them
  reports the wrong thing; check `app.openapi()` to confirm a route is registered.

### Credits (money, treat carefully)

- **Every terminal failure must refund.** `release_usage_for_failed_asset` on the way out,
  `emit_asset_terminal` after commit. A path that fails an asset without both keeps a
  paying customer's tokens for a clip that never arrived. The poll-budget timeout shipped
  missing this.
- Non-terminal assets are swept by `fail_stuck_processing_assets` in the worker loop.
  Anything that can leave an asset `processing` needs to be reachable by that sweep.
- Generate is idempotent by key: the in-flight marker is claimed **before** reserving and
  released if the request fails. After the response is stored, delete the in-flight
  key so a retry hits the cached response instead of 409. Clients persist one key
  per draft (sessionStorage / AsyncStorage) across reloads until success, New, or
  Face / Voice / mode change.
- Apple pack REFUND marks the matching `BillingCreditGrant` (`iap:{transactionId}`)
  `refunded` so unused pack credits drop off. Plan refunds still cancel to free.

### Play prompt contract

- Intimate contact (kiss, hug, embrace, cuddle, make out, caress, nuzzle) is refused before any credit reserve (`intimate_contact.py`). Assist returns that sentence with `ready=false` and an empty draft. Generate, face generate, and face edit return 422. Do not delete the check.
- `split_avatar_user_prompt` returns `(spoken, scene)`. A prompt with no `says:` /
  natural says / `say exactly` is scene-only unless it is a bare first-person or
  greeting line (`hey welcome back`, `I'm at a cafe`). Those words are the line.
  Both clients mirror this; changing it means changing three places. Tapping Scene folds a leftover spoken line
  back into SCENE as quotes. Generate for Scene sends SCENE only, so a line left behind
  on the draft never reaches the model. Two quoted speakers, a friend who replies
  / says / asks, or a man / woman who asks, is Scene. Keep both quotes in SCENE in order. Do not pull the first
  line into THEY SAY. Do not pull a leftover `and says` after other speakers into
  THEY SAY. Quote a leftover spoken tail after the last quote so generate
  speaks it. "They look at each other" already counts as a look sentence.
  A leftover line after "the friend replies" is the Face's first line. Put it
  before the reply so TTS and the picture ask, then answer. The friend looks
  like the opposite-gender stock voice (Brian if the Face voice is female).
- Create assist extracts a spoken line from natural English (`and says …`, `and she says …`, `she says …`,
  quoted speech) even without the colon token. Scene keeps wardrobe, place, and action.
  If that line is already present, do not call Grok. Generate still joins with `says:`
  internally. Clients keep mirroring the colon-token splitter only. Never show `says:`
  in UI. If the scene has a listener, Assist adds one short look sentence to the
  draft scene (`ensure_listener_look`): they look at that person, not past them and
  not at the camera. Do not ask the user for camera notes, 3/4 angles, or blur.
- Talking always gets a short house **LOOK** line (ultra-real human, photoreal, not
  CGI) via `_avatar_look_rules`, plus **FOCUS**: deep focus, no cinematic background
  blur, unless the scene asks for bokeh. Video clips get the same FOCUS block.
  Copy the Face as photographed, including makeup and finish. Do not restyle or
  de-filter unless the scene text asks. Face edits (makeup, filters, hair,
  wardrobe on the plate) belong on Face edit, not generate. Place, wardrobe, voice,
  and duration still come only from the request. Do not stuff scene-specific
  quality notes (neck, city blur, sample locations) into the prompt builder. LOOK
  must not mention camera, eyeline, or talking-head framing. "On camera" was read
  as look-at-lens and overrode conversation scenes.
- **FRAME** (`avatar_frame_rule`) must not prescribe a camera. Same pattern as CAST:
  do not invent what the scene did not write. No house eye-level, fisheye ban,
  talking-head, or 3/4. Assist writes the default shot into Talking SCENE via
  `ensure_talking_frame` (eye-level, not from above, face large) unless they
  named a camera. Generate injects the same if Assist was skipped. A drone, a
  table-down, a wide walk, and a full-figure ask all have to win. LOOK still
  must not mention camera. Do not "fix" a bad street take by making Faces
  full-body. Seedance copies the plate crop, so a full-figure Face makes Talking
  a tiny-face shot. Keep Faces 1:1 head-and-shoulders.
- **ADDRESS** (`avatar_address_rule`) owns who they look at. Branch on
  `scene_has_addressee`. A listener (friend, person beside them, someone they ask)
  stays visible and holds the eyeline. Solo / no addressee looks at the camera.
  SPEAKER must not say "a friend is the listener" on a solo scene. That invented
  an over-the-shoulder extra on a NYC street Talking clip. Solo gets CAST: one
  foreground person. Other people stay in the background if the place has a
  crowd. Do not hardcode streets or a pull-back. "Talking to the camera / viewer / you"
  is presenter address, not a listener. Bystanders do not count. Never switch
  mid-line either way. Generate also injects the look sentence into SCENE via
  `ensure_listener_look` when a listener is present. Video **DIALOGUE** follows
  the same eyeline. Persist `provider_prompt` on the asset. Hide it from the DTO.
- Lip-sync length is counted **after** `expand_spoken_domains`, so clients must expand too
  before estimating. Talking and Scene with a spoken Face line are ElevenLabs TTS,
  then Seedance with those public MP3s as `@Audio1` / `@Audio2`. Seedance has no
  voice-id field. Bind `@AudioN defines the voice and the spoken words`. Do not
  re-quote the TTS line in the Seedance prompt or the model invents a new take.
  Keep `generate_audio: true`. No Sync. No silent picture pass. Pad TTS under ~2s.
  Quote stays audio-on. When a Face is on the clip, TTS uses that Face's bound
  voice if set (`pick_play_voice`), not a leftover Voice chip.
- `PLATFORM_PRESETS` maps `custom` to 9:16. Anything assuming square for `custom` is wrong.
- **`says:` is a parser token and must never appear in UI copy, placeholders, hints, or
  any prompt echoed back to a user** (thread bubbles, sample cards, landing previews,
  Library, Home, Copy). Natural `and says LINE` / `and she says LINE` / `She says LINE`
  still extract the full spoken line (including later sentences). `?` and `!` count
  as sentence breaks (`? She says no`). A leftover `and says thats Studio` after other
  speakers must not become the Talking line. Two quoted speakers, a friend who
  replies / says / asks, or a man / woman who asks, is Scene. Keep the whole
  prompt in SCENE. Do not pull the last `and says` into THEY SAY. Bystanders in
  a crowd ("people in the background and she says") stay Talking. Assist replies
  must not paste or truncate the scene. Both clients are one box plus a draft card.
  The live field uses `avatarPromptForField` so inbound drafts hide `says:` without trimming typed spaces.
  Bubbles and Library use `avatarPromptPreview` / `promptForDisplay` (web Library
  and clip detail too: `ClipsPage`, `ClipDetailPage`). Switching away
  from Talking must flatten the draft with `avatarPromptPreview`, or the joined string
  lands in a plain field.

### Create composer parity (web and mobile)

There is no shared package, so these pairs are hand-mirrored and must change together:

| Concern | Mobile | Web |
|---|---|---|
| Split/join, speech estimate | `mobile/src/features/create/createConstants.ts` | `frontend/src/lib/playPricing.ts` |
| Provider durations / 2.5 resolution | same file (`isSeedance25Model`) | `frontend/src/pages/playPageModel.ts` |
| Mode labels, hints, placeholders | same file, `MODES` / `MODE_HINT` (Clip \| Still) | `frontend/src/pages/playPageChrome.tsx` (`COMPOSER_TABS`) |
| Assist vs generate on first send | same file, `modeUsesAssist` (always true) | same file |
| Credits line copy | `mobile/src/features/create/createCostLine.ts` | `frontend/src/features/play/createCostLine.ts` |
| Talking entry | `CreateComposer.tsx` (one box + draft card) | `frontend/src/features/play/PromptFields.tsx` (one box + draft card) |
| Landing preview of the composer | `LandingCreatePreview.tsx` | `HomePage.tsx` (reuses `PromptFields`) |
| Video face support by model | `mobile/src/lib/qualityTier.ts` (`modelSupportsFaceReference`) | `frontend/src/pages/playPageModel.ts` (same helper) |
| Extend engine pick | same file (`pickExtendModel`) | same file (`pickExtendModel`) |
| Create thread clip card | `CreateThread.tsx` + `CreateThreadGenCard.tsx` | `frontend/src/features/play/CreateThread.tsx` |

The live field uses `avatarPromptForField` so inbound drafts hide `says:` without
re-running scene cleanup on every keystroke. That trim used to eat a trailing "and"
while it was still being typed.

Options are gone on Clip. On iOS there is no tab bar. Home is the signed-in
root. Clip and Still are chosen on Home, then Create is a stack screen with a
native Back. The Create header title is Clip or Still. There is no Clip | Still
switch. Still Fast / Quality is headerRight. The bar is iMessage-shaped: plus
(refs) left of the field, Face inside the pill, Voice then Send. Length and
credits sit on the user bubble. Web Create header is Clip or Still. Empty thread
picks Clip or Still. There is no persistent Clip | Still tab bar. Web still keeps Face, Voice, and Add reference on the composer. Default Voice is
the Voices pick (saved until they pick another). If none is saved: clone, else Jessica.
When a Face is on the clip, that Face's bound voice wins over a leftover chip, except
on Revoice and Extend (`revoice_of` / `continue_from`), where an explicit Voice pick
wins. Switching to an unbound Face restores the Voices fallback (saved pick, else
clone, else Jessica). Only set the chip to a bind that is in the Voices list. Do not
leave Voice empty. Assist picks Fast vs 2.5 and resolution from the line.
A client Assist miss (network, 4xx, stale send) must not spend. The grey line is
"Send again. Nothing was spent." Next send retries Assist. Do not set `ready=true`
on that miss or the composer skips the helper and generates the raw box. Server
Grok miss still returns HTTP 200 with a draft (topic-only Talking becomes Scene).
Talking without a
Face is blocked at generate. Cost line prefers `POST /play/quote`.

Clip is Seedance only. Default Fast (`seedance-*-fast`, 15s, 720p). Speech over 15s and
at most 30s uses 2.5. Over 30s: first 30s on 2.5, then Extend. 2.5 max is 720p. 1080p
and 4k only on Fast. Do not ask Fast vs 2.5 on every short clip.

Create is **Clip or Still**. Kind is confirmed on the draft card: **Talking**
or **Scene** (`kind:avatar` / `kind:video`). Old `kind:lipsync` remaps to Talking.
Every
Create send talks the clip through first (`modeUsesAssist` is always true). Assist
never trims the spoken line. Talking duration follows the line, capped at 15s Fast /
30s on 2.5. Chip taps
never call the model. Do not treat the words "a scene" inside a spoken line as
the Scene job (a Talking pitch can list Talking, a scene, or a still). Tapping
Talking after a Scene fold must re-extract the line from SCENE. Assist natural-says matches generate (`(?!that\b)`).
Grok only drafts a spoken
line when kind is Talking and there is a topic but no extractable line. Face and voice
guards wait until generate, after kind is known. Do not disable Continue for a missing
Face while kind is still unknown. Assist provider errors return HTTP 200 with
`ready=true` (topic-only Talking becomes Scene). A client Assist failure must not
fall through to generate as written. Send again retries the helper. Say "credits" in user copy, never
"tokens".

Faces stay 1:1 head-and-shoulders. Do not switch the library to full-body. Seedance
copies the plate crop, so a full-figure Face makes Talking a tiny-face street shot
with laggy lips. Do not bake a room or background into a Face. Named
place goes in SCENE. Face is `@Image1`. Assist writes one short default shot into
Talking SCENE unless they named a camera (eye-level, not from above, face large).
Generate injects the same if Assist was skipped. Do not ask the user for camera
notes. A drone, a wide, or a full figure they wrote wins. Talking builds a hidden
clip still from the Face plus that SCENE (`play_clip_still.py`), attached as `@Image2`.
Not billed, not a Face, not in Library. Skip on Extend. If the still fails, generate
anyway. FRAME must not invent a camera. SCENE owns the shot. Clone Talking / spoken Scene adds voiceover seconds only.
Two-hander lines stay separate MP3s. User Add reference slots start after
house TTS.

Create-thread results are phone-shaped media bubbles, not dashboard cards. Vertical
clips stay narrow (`threadClipCardWidth` / `threadClipCardClass`, ~228px) with
`aspect-ratio` 9/16 and `object-cover`. Square (feed) is a bit wider at 1:1. Do not
put a 9:16 clip in a wide bubble and cap height: that letterboxes or squashes the
frame and native `<video controls>` look wrong in chat. Poster first, tap to play,
no native player chrome in the thread. Clip detail can keep native controls.

Video mode may attach an optional face. Clip models are Seedance only (all support
face refs). Talking always needs a Face.

Scene with a Face and a spoken line uses the same TTS then Seedance path as Talking.
Quotes, ``says:``, or natural ``and says LINE`` all count. Face lines use that Face's
bound voice if set, else the Voice chip (stock or clone). Other speakers get the
opposite-gender built-in (Brian if the Face voice is female, Jessica if male). No Face,
or a Scene with no spoken line, stays native Seedance audio. Stock stays on video
credits. Clone adds voiceover seconds only. Hide clones on Scene until a Face is
selected.

### Grok stills and assist (not Clip)

- Clip catalogs drop Grok, Kling, and Veo. Keep Grok stills and `grok-4.6` assist
  (`XAI_TEXT_MODEL`). Stills Quality is `grok-imagine-image-2.0` (catalog id
  `xai-image-quality`). Face edit already uses 2.0. Fast stills stay
  `grok-imagine-image`.
- Keep `sync_labs.py` so in-flight Sync jobs can finish. Do not add new Sync generate
  paths. House TTS is injected server-side and must not appear as ref chips.

### Seedance

- Clip is Seedance only. Fast is `seedance-2-0-fast` / `seedance-avatar-fast`
  (15s). Advanced is 2.5 (`seedance-2-5` / `seedance-avatar`, 30s, 720p max).
  Old `seedance-photo*` ids alias to the Talking models. Do not send `seed` on 2.5. Cap 1080p/4k
  requests to 720p on 2.5.
- Voice drive: public MP3s as `audio_urls`. Fast 3 files / 15s combined. 2.5 10
  files / 30s combined. There is no Seedance voice id. The prompt must say
  `@AudioN defines` voice and words, and must not also dump the transcript as
  "speaks this line". Video refs on 2.5 allow a 30s `@Video1` for Extend.
-   Talking and Scene can Extend. Each Extend is a new Library
  card, not one spliced file. Restore the source clip's mode, Face, and voice.
  Do not force Scene. Server copies `face_asset_id` from the prior clip when
  the client omits it. `scene_needs_exact_voice` must not bypass
  `continue_from`.

### Auth

- Registration is open. Do not add invite codes, waitlists, or Request access CTAs
  for signup. Guest primary CTA is Create account (`/register`). Contact stays for
  help, not gatekeeping.
- Refresh rotation looks up revoked tokens deliberately: rotated within
  `REFRESH_ROTATION_GRACE_SECONDS` is a benign multi-tab race (401, leave the cookie
  alone), older is a replay (revoke that refresh family, not every device). Never clear
  the refresh cookie on an unknown token; on a shared cookie jar that signs out the tab
  that just won.
- Sign-out and a new sign-in must wipe the React Query cache plus account prefs
  (workspace id, Face, Voice, play idempotency). The QueryClient is a process
  singleton. Leaving it filled is how a new account still showed
  `admin@studio.local` Library clips and then 404 Workspace not found.
- A stored workspace id may seed Home fetches only when it is tagged with the
  current user id. Never fall back to a bare last-used id after logout.
- Register sends only the confirm-email message. Welcome waits until the first
  successful verify. That mail links to `/play` (Create). `/studio/overview`
  is gone and must not appear in new-account copy.

### iOS IAP

- Plans are auto-renewable under `com.example.studio.sub.{starter,creator,studio}`. Packs are
  consumables under `com.example.studio.credit.*`. Sale packs: `video_10`, `video_25`,
  `image_50`, `voice_30m`. Retired `lipsync_10`, `scripts_25`, `creator_burst`
  still fulfill Stripe/IAP that already charged. Do not reuse `com.example.studio.plan.*`,
  `com.example.studio.pack.*`, or retired `com.example.studio.credit.*` IDs. Those App Store Connect
  IDs are burned. Catalog: `backend/app/iap_catalog.py`. Setup: `docs/IOS_IAP.md`.

### Faces, wardrobe, and custom voices

- Faces are upload, generate, or edit. There is no starter library. Example
  taps fill the prompt only. They must not add Maya/Jordan/etc. Existing
  `source_kind: "starter"` rows stay as normal faces. Face rows are
  `video_assets` with `play_mode: "avatar"`, `mode: "avatar_source_image"`,
  `face_library: true`, and no `voice`. Never DELETE talking clips by empty
  voice plus `play_mode=avatar` without excluding those (0043 did; restore
  with `backend/scripts/restore_purged_faces.py`). Bind is `bound_voice_id` on
  face metadata (stock id like `jessica`, or a ready clone UUID). Talking and voiced Scene use that bind
  when the Face is on the clip (`pick_play_voice` / `resolve_play_generate_voice`).
  Generate tries bound, then the chip, then Jessica. A deleted or unready bind
  must not 422 if the chip or Jessica still works. A leftover Jessica chip
  must not win while the bind is ready. Do not persist the bound voice as the
  Voices default. Cost line uses the effective voice (bound if it is in the
  list). Scene clone voiceover bills Face TTS seconds only.
- Face edit is a surgical edit of the source photo, not a new portrait.
  `face_edit_prompt` must not open with "Photorealistic head-and-shoulders
  portrait" or force studio light and background. Lock eyes, nose, mouth, jaw,
  skin, age, and expression. Hair or facial-hair asks restyle that layer only
  and must not rebuild the face. Omit `aspect_ratio` on the xAI edit so the
  source crop wins. New look siblings store `previous_url` so compare still
  works after navigation.
- Wardrobe lives on the selected look. SCENE uses that look unless the prompt
  names clothes for this clip only. Named clothes (yoga pants, a tank, "dressed
  in") must beat the Face photo. Clothes on a friend or listener stay on that
  person. Do not put those on the Face. The photo is face, hair, skin, and makeup.
  Keep that finish in Talking and Scene. Do not let identity lock copy the
  photo outfit over clothes the scene named. Do not tell Grok to take clothes
  off. That wording plus a Face photo is `imagine:content-moderated` after the
  clip renders. Say wear the scene clothes, not the outfit in the photo.
- Stock voices are ElevenLabs (`backend/app/stock_voices.py` plus
  `library_voices.json`). Ordinary first names (Jessica, Brian, Hope, …).
  Defaults (19) need no Voice Library add. Hosted library copies are pinned
  from trending shared voices (no credit multipliers, not live 10k search).
  Ingest with `backend/scripts/ingest_elevenlabs_library.py`. Those copies
  are shared stock, not workspace clones, and do not count toward
  `clone_slot_limit`. Create shows featured five plus the current pick.
  Voices search covers the full hosted list. Talking with a stock voice is
  the same generate as a clone (TTS, then Seedance) but only clip credits.
  Never send an ElevenLabs id in `reference_audios`.
  One Library asset (`play_mode: "avatar"`). Clone adds voiceover seconds only.
  Talking and Scene can Extend.
- Talking + a clone is the same chain. Cost is clip credits plus voiceover seconds.
- One clone per workspace. Admin raises via `subscription.limit_overrides["clone_slot_limit"]`.
  At cap: delete to replace. No waitlist.
- Clone samples are transcoded to WAV on the API before ElevenLabs. iOS Voice
  Memos and expo-audio often write CAF or PCM labeled as `.m4a`. Native
  `AudioRecorder` ignores nested `ios` / `android` preset keys, so do not pass
  `RecordingPresets.HIGH_QUALITY` into `new AudioRecorder`. Flatten first
  (`cloneRecordingOptions`): iOS records WAV / Linear PCM. The API retries CAF /
  AAC / ipod demuxers when the first ffmpeg pass fails. Do not send the original
  filename (a missing extension used to default to `.wav`).
- Clone language lists and read-aloud scripts are hand-mirrored:
  `mobile/src/lib/cloneVoice.ts` and `frontend/src/features/play/cloneVoice.ts`.
  Allowed codes live in `backend/app/clone_languages.py`. The Voices screen
  asks for language first, then shows that script. Record languages are the 32
  Instant Voice Clone set (Flash v2.5 / Multilingual v2). Clone TTS is
  `eleven_v3` (`ELEVENLABS_TTS_MODEL`). Do not pin `eleven_multilingual_v2`
  again. v3 can speak 70+ languages from that clone.

## UI / product copy (strict)

User-facing text must sound human, not AI-generated marketing.

- **No em dashes (—) or en dashes (–)** in prose. Prefer periods or short sentences.
- **No robotic product-speak:** avoid phrases like "brand-aware", "deliverable", "pipeline", "leverage", "unlock", "multi-hook variants", "seed a draft", "control spend", "seamless", "robust", "empower".
- Prefer plain labels and sentences: what it does, where to click, what it costs in credits.
- Match existing studio tone: short, concrete, slightly casual. Read nearby strings before writing new ones.
- Empty-stat placeholder `—` in metrics is fine; dash-heavy marketing sentences are not.
- Public `/pricing`, `/docs/billing-and-plans`, and `frontend/src/marketing/plans.ts` must
  match `clip_credit_limit` in `backend/app/plans.py` (`play_avatar` + `play_video` + leftover `play_lipsync`).
  Do not
  publish `image_generation_limit` as still credits (Starter stills are 70, not 90).
  Talking and Scene share one Clip pool (sum remainings so mid-month nobody
  loses). Events still write `play_avatar` / `play_video`. Historical `play_lipsync`
  usage counts toward Clip. Reserve checks the
  combined used + combined cap. New video packs grant `play_video_limit` only.
  Existing dual-written grants keep both keys. Create docs are Clip | Still plus
  Talking / Scene. Clone Talking spends clip plus voice seconds. Clone
  Scene with a Face and a spoken line spends clip plus voice seconds. Do not show a
  Photo meter or a Scripts meter. `lipsync_10` is retired (burned IAP id) and still
  grants leftover clip credits on fulfill. Say "credits", never
  "tokens", on public pages.

## Frontend styling (strict)

- **Tailwind only.** Entry: `frontend/src/styles/tailwind.css` via `StudioThemeProvider`.
- Recipes: `frontend/src/ui/tw.ts`. Shell maps: `*Styles.ts`. Theme: `theme/brand.ts` + `theme/materials.ts`.
- **Do not** add plain CSS files, `productTw`/`pc()` bridges, or reintroduce Fluent/Radix for chrome.
- The SPA is on `example.com` and the API on `api.example.com`. `API_BASE_URL` falls back to the
  production API on any non-local host when `VITE_API_BASE_URL` is unset, because a
  relative base makes signed media resolve against the SPA origin and 404.
- Signed media carries `?exp=` with a two hour life. Do not pin one in state a user can
  leave open; refetch when `isSignedMediaUrlExpired`.
- Play clip URLs in the DTO must stay relative `/api/media`. `PUBLIC_API_BASE_URL` is for
  providers (Seedance fetching audio/video), not the browser. Baking a Tailscale `http://`
  host into the clip URL makes HTTPS (tunnel) play and download fail as mixed content.
- Safari on iPhone will not open the mic on `http://` LAN Vite (`server.host: 0.0.0.0`).
  Needs HTTPS (tunnel) or Upload. `MediaRecorder` must request `audio/mp4`; the default
  webm constructor throws. Put that error next to Record. Helpers: `frontend/src/lib/recordAudio.ts`.
  Clone file input must not use `accept="audio/*"` alone. That opens Music and greys out
  Voice Memos `.m4a`. Use `CLONE_AUDIO_ACCEPT` (extensions first).
- Outer rails (public chrome, sections, docs, `dashMain`) cap at **90rem**. Logged-in
  Create and the landing composer share **max-w-5xl**. Legal/reading stays **max-w-3xl**.
  Do not put Create back on `max-w-3xl`. It reads as a phone column on a laptop.

## Naming

- The past-work surface is **Library** (Talking, Scene, stills). Routes,
  files, and component names still say `clips` so existing links and notification hrefs
  keep resolving; only user-facing text changed.
- Faces are **Faces** on mobile and web. Routes stay `/avatars` so old links and
  notification hrefs keep resolving. Both are upload / generate / edit. No starter catalog.

## Keeping this file honest

Update `AGENTS.md` (and `mobile/AGENTS.md`) in the same change that establishes a new
convention or fixes a trap another agent could fall into. These files exist because the
mistakes recorded here were all made at least once.
