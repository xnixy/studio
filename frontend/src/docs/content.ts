import type { DocArticle } from "./types";

const UPDATED = "August 26, 2026";

export const DOC_ARTICLES: DocArticle[] = [
  {
    slug: "getting-started",
    title: "Getting started",
    description: "From signup to your first clip in Create.",
    section: "start",
    order: 1,
    updated: UPDATED,
    body: [
      {
        type: "p",
        text: "Studio is Create: Talking, Scene, and stills in a chat-style thread. Clips run on Seedance. Stills stay on Grok and Nano Banana. You spend credits and download the file. This guide is for day one.",
      },
      {
        type: "callout",
        tone: "note",
        title: "Open signup",
        text: "Create an account with your name, email, and a password. After signup, your workspace opens with Create, Faces, Voices, Library, and Billing.",
      },
      { type: "h2", id: "create-account", text: "1. Create your account" },
      {
        type: "steps",
        items: [
          "Open Register or Create account.",
          "Enter your name, email, password (twice), and complete the captcha.",
          "Sign in if you aren’t signed in already.",
        ],
      },
      { type: "h2", id: "workspace", text: "2. Your workspace" },
      {
        type: "p",
        text: "Your account holds faces, a custom voice, clips, and credit budget. Plans and packs live under Billing.",
      },
      { type: "h2", id: "first-steps", text: "3. What to do first" },
      {
        type: "ol",
        items: [
          "Optional: open Faces and generate or upload a face. Reusing it is free.",
          "Optional: open Voices and clone yours once if you want Talking in your voice.",
          "Open Create. Tabs are Clip or Still.",
          "Write what the clip is about in one box. We talk it through and confirm Talking or Scene before you spend credits.",
          "Generate, then download or open it from Library.",
        ],
      },
      {
        type: "callout",
        tone: "tip",
        title: "Start small",
        text: "Use Seedance Fast while you learn the UI. Credit cost is on the draft card before you generate.",
      },
      { type: "h2", id: "next", text: "Next guides" },
      {
        type: "links",
        items: [
          { label: "Make your first clip", to: "/docs/create-your-first-clip" },
          { label: "Models & credits", to: "/docs/models-and-tokens" },
          { label: "Faces", to: "/docs/avatars-and-faces" },
          { label: "Voices & clone", to: "/docs/voices-and-clone" },
          { label: "Plans & credits", to: "/docs/billing-and-plans" },
        ],
      },
    ],
  },
  {
    slug: "account-and-invite",
    title: "Account",
    description: "Signing in, your profile, and how access works.",
    section: "start",
    order: 2,
    updated: UPDATED,
    body: [
      {
        type: "p",
        text: "Create a free account on the site or in the iOS app. Your workspace holds faces, a custom voice, clips, and credit budget.",
      },
      { type: "h2", id: "sign-up", text: "Create an account" },
      {
        type: "ul",
        items: [
          "Open Create account on the site or in the app.",
          "Enter your name, email, and a password. Complete the captcha.",
          "Verify your email, then you are in.",
        ],
      },
      { type: "h2", id: "sign-in", text: "Sign in" },
      {
        type: "p",
        text: "Use the email and password you registered with. If you’re already signed in, Sign in sends you to Create.",
      },
      { type: "h2", id: "security-check", text: "Security check (captcha)" },
      {
        type: "p",
        text: "Register and Contact show a Cloudflare security check. Complete it before submit. It cuts down bots without making signup harder for real people.",
      },
      { type: "h2", id: "profile", text: "Profile" },
      {
        type: "p",
        text: "Open Profile in the sidebar to set your display name, change password, or tweak look and feel. Changing password signs you out everywhere. You’ll also see remaining clip and still credits for the active workspace.",
      },
      {
        type: "callout",
        tone: "warning",
        title: "Never share passwords",
        text: "Studio staff will never ask for your password. Use a unique password for this account.",
      },
    ],
  },
  {
    slug: "create-your-first-clip",
    title: "Make your first clip",
    description: "Clip or Still. We confirm Talking or Scene.",
    section: "create",
    order: 1,
    updated: UPDATED,
    body: [
      {
        type: "p",
        text: "Create is the main surface. One thread per session. Past work lives in Library. Faces hold faces you reuse. Voices holds your clone.",
      },
      {
        type: "callout",
        tone: "note",
        title: "AI is a draft",
        text: "Always watch the result and check the prompt before you post. You are responsible for what goes public.",
      },
      { type: "h2", id: "tabs", text: "Clip or Still" },
      {
        type: "p",
        text: "Create has two tabs. Kind is confirmed on a draft card after you send, not as a fourth tab.",
      },
      {
        type: "ul",
        items: [
          "Clip: a short video. Write one prompt. We confirm Talking or Scene.",
          "Still: one image (Grok or Nano Banana). No spoken lines.",
        ],
      },
      { type: "h2", id: "kinds", text: "The two clip kinds" },
      {
        type: "ul",
        items: [
          "Talking: your face in a new scene, speaking a line. Seedance Fast is the default. Length follows the line, up to 15s. Over 15s uses 2.5, up to 30s. Longer is Extend.",
          "Scene: any short video. Face is optional. With a Face and a spoken line, the Face uses its bound voice if one is set, else the Voice chip. Other people get a different built-in.",
        ],
      },
      {
        type: "callout",
        tone: "tip",
        title: "Write it how you talk",
        text: "One box. “She’s in yoga pants in the kitchen and says I actually finish these protein bars.” We pull the spoken line and keep the clothes and place in the scene. You never need a special token in the prompt.",
      },
      { type: "h2", id: "bar", text: "Face and voice" },
      {
        type: "ul",
        items: [
          "Face and Voice sit on the composer bar. Clip has no Options. Still keeps a Fast / Quality pick.",
          "Default Voice is the Voices pick. If none is saved: clone, else Jessica. When a Face is on the clip, that Face’s bound voice wins. Don’t leave Voice empty.",
          "Face and voice guards wait until generate, after kind is known.",
          "We always talk the clip through first. Chip taps on the draft card do not call the model.",
        ],
      },
      { type: "h2", id: "steps", text: "Steps" },
      {
        type: "steps",
        items: [
          "Open Create from the sidebar.",
          "Leave Clip selected, or switch to Still.",
          "Write what you want in the box. Send. Confirm the kind on the draft card.",
          "Add a face for Talking. Pick a voice if you want your clone or a built-in.",
          "Credit cost is shown before you generate. Assist picks Fast or 2.5 from the line.",
          "Generate. When ready, download or open it from Library.",
        ],
      },
      {
        type: "callout",
        tone: "tip",
        title: "Gens take a moment",
        text: "Clips poll until ready. Stay on the page or check Library in a minute. Failed runs release reserved credits.",
      },
      { type: "h2", id: "next", text: "Related" },
      {
        type: "links",
        items: [
          { label: "Models & credits", to: "/docs/models-and-tokens" },
          { label: "Faces", to: "/docs/avatars-and-faces" },
          { label: "Voices & clone", to: "/docs/voices-and-clone" },
          { label: "Plans & credits", to: "/docs/billing-and-plans" },
        ],
      },
    ],
  },
  {
    slug: "models-and-tokens",
    title: "Models & credits",
    description: "Seedance clips, Grok stills, and what each run spends.",
    section: "create",
    order: 2,
    updated: UPDATED,
    body: [
      {
        type: "p",
        text: "Each generation spends credits from a monthly pool. Cheaper models cost fewer credits. Longer talking and video clips spend more. You see the number before you run.",
      },
      { type: "h2", id: "pools", text: "Two media pools" },
      {
        type: "ul",
        items: [
          "Clip credits: Talking, Scene, and Extend. One shared pool. Leftover Photo caps fold in.",
          "Still credits: stills. Face generate uses a smaller face pool.",
        ],
      },
      { type: "h2", id: "typical", text: "What a typical run spends" },
      {
        type: "ul",
        items: [
          "Fast still: 1 still credit. Quality Grok still: 2. Nano Banana 2: 3. Pro: 5.",
          "Talking Fast: 8 credits at about 5s, 13 credits at about 8s. Length follows the line. Over 15s uses 2.5, up to 30s.",
          "Talking with your clone: the clip credits above, plus a few voiceover seconds.",
          "Scene Fast: 8 clip credits at about 5s. With a Face and a spoken line, the Face uses its bound voice if one is set, else the Voice chip. A clone adds a few voiceover seconds.",
          "Seedance 2.5: 12 credits. Up to 30s at 720p.",
        ],
      },
      { type: "h2", id: "image-models", text: "Still models" },
      {
        type: "ul",
        items: [
          "Grok Image Fast: 1 credit. Volume and drafts.",
          "Grok Image 2.0: 2 credits. Latest Grok stills.",
          "Nano Banana 2 Lite: 2 credits. Faster Gemini stills.",
          "Nano Banana 2: 3 credits. Strong text and detail.",
          "Nano Banana Pro: 5 credits. Hard prompts and brand work.",
        ],
      },
      { type: "h2", id: "video-models", text: "Clip models" },
      {
        type: "ul",
        items: [
          "Seedance Fast: 8 credits. Talking and Scene. Up to 15s. 1080p and 4k only on Fast.",
          "Seedance 2.5: 12 credits. Up to 30s at 720p. Assist picks this when the line is over 15s.",
        ],
      },
      {
        type: "callout",
        tone: "tip",
        title: "See cost before you run",
        text: "The draft card and the line under the prompt show credits. Clone Talking and clone Scene show voice seconds. Assist picks Fast or 2.5. Still keeps Fast / Quality.",
      },
      { type: "h2", id: "packs", text: "When you run out" },
      {
        type: "p",
        text: "Open Billing. Buy a Clip, Still, or Voice pack for the current month. Packs require a paid plan.",
      },
      {
        type: "links",
        items: [
          { label: "Plans & credits", to: "/docs/billing-and-plans" },
          { label: "Make your first clip", to: "/docs/create-your-first-clip" },
          { label: "Voices & clone", to: "/docs/voices-and-clone" },
        ],
      },
    ],
  },
  {
    slug: "avatars-and-faces",
    title: "Faces",
    description: "Generate or upload a face once, reuse free in Talking and Scene.",
    section: "create",
    order: 3,
    updated: UPDATED,
    body: [
      {
        type: "p",
        text: "A Face is identity only: head and shoulders on a plain background. Scene, outfit, and dialogue come from each clip prompt. Reusing a face does not spend still credits. There is no starter catalog. Example taps fill the prompt only.",
      },
      { type: "h2", id: "add", text: "Add a face" },
      {
        type: "ul",
        items: [
          "Generate: describe the face only. Pick Grok or Nano Banana. This spends face credits. Do not bake a room into a Face.",
          "Upload: JPEG, PNG, or WebP. Confirm you have rights to use the likeness.",
          "Edit: change hair or look on an existing Face without starting over.",
        ],
      },
      {
        type: "callout",
        tone: "warning",
        title: "Consent and rights",
        text: "Only use faces you have the right to use. Enter the rights-holder name when asked. Review every cut before posting.",
      },
      { type: "h2", id: "use", text: "Use a face" },
      {
        type: "steps",
        items: [
          "Select the face in Faces or on the Create bar.",
          "Write the clip. We confirm Talking or Scene.",
          "Talking: describe place, clothes, and what they say. Named clothes beat the photo outfit.",
          "Generate. The Face is identity (face, hair, skin). Clothes the scene named win.",
        ],
      },
      {
        type: "callout",
        tone: "note",
        title: "Voice on the Face",
        text: "A Face can remember a bound voice. When that Face is on the clip, that voice is the one that speaks. Selecting the Face sets Voice on Create.",
      },
      {
        type: "links",
        items: [
          { label: "Make your first clip", to: "/docs/create-your-first-clip" },
          { label: "Voices & clone", to: "/docs/voices-and-clone" },
          { label: "Models & credits", to: "/docs/models-and-tokens" },
        ],
      },
    ],
  },
  {
    slug: "voices-and-clone",
    title: "Voices & clone",
    description: "Built-in voices plus one custom clone per workspace for Talking and Scene.",
    section: "create",
    order: 4,
    updated: UPDATED,
    body: [
      {
        type: "p",
        text: "Voice sits on the Create bar as the featured five. Open Voices to search the full hosted list by name, gender, or accent. You can also clone your own voice once and use it in Talking and spoken Scene.",
      },
      { type: "h2", id: "defaults", text: "What gets picked" },
      {
        type: "ul",
        items: [
          "The voice you pick on Voices is the default for Create until you pick another.",
          "If none is saved: clone, else Jessica. When a Face is on the clip, that Face's bound voice wins over a leftover pick.",
          "Voice should not be empty.",
        ],
      },
      { type: "h2", id: "clone", text: "Clone your voice" },
      {
        type: "steps",
        items: [
          "Open Voices. Pick the language you will record in, then read that script.",
          "Record or upload 30 to 90 seconds in a quiet room.",
          "Clone. Listen to the preview, then use it in Create.",
        ],
      },
      {
        type: "callout",
        tone: "note",
        title: "One clone per workspace",
        text: "At the cap, delete the old clone to replace it. There is no waitlist. Admin can raise the slot for a workspace.",
      },
      { type: "h2", id: "talking", text: "Talking with a clone" },
      {
        type: "p",
        text: "Talking plus a clone is one generate: we speak the line in your voice, then Seedance makes the picture from that audio. One Library clip. Cost is clip credits plus voiceover seconds.",
      },
      {
        type: "ul",
        items: [
          "Jessica or another built-in on Talking spends clip credits only.",
          "A clone on Talking or spoken Scene adds a few voiceover seconds.",
        ],
      },
      {
        type: "links",
        items: [
          { label: "Make your first clip", to: "/docs/create-your-first-clip" },
          { label: "Models & credits", to: "/docs/models-and-tokens" },
          { label: "Plans & credits", to: "/docs/billing-and-plans" },
        ],
      },
    ],
  },
  {
    slug: "billing-and-plans",
    title: "Plans & credits",
    description: "Free, Starter, Creator, Studio: monthly credits and packs.",
    section: "teams",
    order: 1,
    updated: UPDATED,
    body: [
      {
        type: "callout",
        tone: "note",
        title: "Free to start",
        text: "Free seats include a tiny credit sample. Paid plans add more clip and still credits.",
      },
      { type: "h2", id: "tiers", text: "Plans" },
      {
        type: "ul",
        items: [
          "Free: 25 clip, 12 still.",
          "Starter ($39): 80 clip, 70 still.",
          "Creator ($99): 200 clip, 160 still.",
          "Studio ($179): 525 clip, 400 still, plus priority rendering.",
        ],
      },
      {
        type: "p",
        text: "Talking and Scene share one Clip pool. A Talking Fast clip at about 5s spends 8 clip credits, so Starter covers a handful of those if you only make talking clips. Talking with a clone spends clip credits plus voice seconds.",
      },
      {
        type: "callout",
        tone: "tip",
        title: "Plans vs packs",
        text: "The subscription covers the product and a monthly batch of credits. For heavy weeks, add a one-time credit pack. Seedance Fast stretches the month. Seedance 2.5 spends more per run.",
      },
      { type: "h2", id: "meters", text: "What counts" },
      {
        type: "ul",
        items: [
          "Clip credits (Talking, Scene, Extend)",
          "Still credits (stills). Face generate is a smaller pool.",
          "Voiceover seconds for clone TTS",
        ],
      },
      { type: "h2", id: "where", text: "Where to manage" },
      {
        type: "p",
        text: "In the app: Billing. See remaining credits, buy packs, or open the Stripe portal. On iPhone, plans and packs go through the App Store.",
      },
      {
        type: "links",
        items: [
          { label: "Public pricing", to: "/pricing" },
          { label: "Models & credits", to: "/docs/models-and-tokens" },
        ],
      },
    ],
  },
  {
    slug: "faq",
    title: "FAQ",
    description: "Common questions about Create, models, and credits.",
    section: "help",
    order: 1,
    updated: UPDATED,
    body: [
      { type: "h2", id: "what", text: "What is Studio?" },
      {
        type: "p",
        text: "A chat-first Create app for Talking, Scene, and stills. Clips run on Seedance. Stills stay on Grok and Nano Banana. You spend monthly credits and download the files. It does not post anything for you.",
      },
      { type: "h2", id: "tabs", text: "Where did Talking / Scene tabs go?" },
      {
        type: "p",
        text: "Create is Clip or Still. Write one prompt. We confirm Talking or Scene on a draft card before you spend. Face and Voice stay on the bar. Clip has no Options.",
      },
      { type: "h2", id: "models", text: "Which models can I use?" },
      {
        type: "p",
        text: "Stills: Grok Imagine and Google Nano Banana. Clips: Seedance Fast and Seedance 2.5. Talking and Scene with a spoken Face line use ElevenLabs, then Seedance. Availability depends on server keys and your plan credits.",
      },
      { type: "h2", id: "credits", text: "How do credits work?" },
      {
        type: "p",
        text: "Each generation reserves credits from the matching pool. Cost is shown before you generate. If a run fails, the reservation is released. Packs top up the current month. Clone Talking spends clip credits plus voice seconds. Clone Scene spends clip credits plus voice seconds.",
      },
      { type: "h2", id: "clone", text: "Does my clone work on Talking?" },
      {
        type: "p",
        text: "Yes. Talking and Scene with a Face and a spoken line can use it. Bind it on the Face so it wins over a leftover pick. It adds a few voice seconds. Jessica does not.",
      },
      { type: "h2", id: "publish", text: "Does Studio post for me?" },
      {
        type: "p",
        text: "No. You download and publish yourself in the apps you already use.",
      },
      { type: "h2", id: "images", text: "Can I make stills only?" },
      {
        type: "p",
        text: "Yes. Switch Create to Still. Fast Grok stills cost 1 credit.",
      },
      { type: "h2", id: "price", text: "How much does it cost?" },
      {
        type: "p",
        text: "Free sample, then Starter $39, Creator $99, Studio $179. Talking, scene, stills, and photo on every tier. Extra media via credit packs. See Plans & credits or Pricing.",
      },
    ],
  },
  {
    slug: "troubleshooting",
    title: "Troubleshooting",
    description: "Gens stuck, limits, and media not loading.",
    section: "help",
    order: 2,
    updated: UPDATED,
    body: [
      { type: "h2", id: "stuck", text: "Generation stuck on processing" },
      {
        type: "ul",
        items: [
          "Wait a minute; clips poll in the background.",
          "Open Library and refresh. If it fails, try again with a shorter prompt or a different model.",
          "Check Billing. A 402 means you hit a monthly credit limit.",
        ],
      },
      { type: "h2", id: "limit", text: "Monthly limit reached" },
      {
        type: "p",
        text: "Buy a credit pack or wait for the period reset.",
      },
      { type: "h2", id: "face", text: "Face required" },
      {
        type: "p",
        text: "Talking needs a face. Add one under Faces or the face chip on Create. Scene can skip the face.",
      },
      { type: "h2", id: "media", text: "Preview blank or download fails" },
      {
        type: "ul",
        items: [
          "Hard-refresh the page.",
          "Confirm storage is configured (R2) for your environment.",
          "Try Open in a new tab from the clip detail page.",
        ],
      },
      { type: "h2", id: "captcha", text: "Captcha never loads" },
      {
        type: "ul",
        items: [
          "Disable aggressive ad blockers for example.com.",
          "Try another browser or network.",
        ],
      },
      {
        type: "callout",
        tone: "note",
        title: "Still stuck?",
        text: "Contact us with your workspace name, the clip kind, model, and approximate time of the failure. Don’t send passwords or full API keys.",
      },
    ],
  },
];
