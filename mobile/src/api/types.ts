export type Role = "user" | "admin";
export type WorkspaceType = "personal" | "brand";
export type WorkspaceRole = "owner" | "admin" | "editor" | "viewer";
export type PlayMode = "image" | "video" | "avatar" | "lipsync";
export type PlayPlatform = "tiktok" | "reels" | "shorts" | "feed" | "custom";
export type PlanName = "free" | "starter" | "creator" | "studio";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  permissions: Record<string, boolean>;
  email_verified?: boolean;
}

export interface AuthResponse {
  access_token: string;
  user: User;
  refresh_token?: string | null;
}

export interface Workspace {
  id: string;
  name: string;
  type: WorkspaceType;
  role: WorkspaceRole;
  member_count: number;
  billing_workspace_id: string;
  permissions: string[];
  created_at: string;
}

export interface PlayModelOption {
  id: string;
  label: string;
  modality: string;
  provider: string;
  blurb: string;
  credit_meter: string;
  token_cost: number;
  default: boolean;
  enabled: boolean;
  max_duration_seconds?: number | null;
  /** Video: may attach a face plate as identity. False for Veo Lite, etc. */
  supports_face_reference?: boolean;
  /** fast = Grok; advanced = Seedance/Veo/Kling/Nano Banana. */
  lane?: "fast" | "advanced";
  requires_plan?: string | null;
  locked?: boolean;
}

export interface PlanEntitlements {
  modes: string[];
  advanced_models: boolean;
  min_plan_for_advanced: string;
  suggested_upgrade: string;
}

export type PlayRefKind = "image" | "video" | "audio";

export interface PlayRef {
  id: string;
  workspace_id: string;
  kind: PlayRefKind;
  url?: string | null;
  duration_seconds?: number | null;
  label?: string | null;
  status: string;
  created_at: string;
}

export interface PlayGeneration {
  id: string;
  workspace_id: string;
  mode: string;
  platform: string;
  prompt: string | null;
  status: string;
  asset_type: string;
  provider?: string | null;
  provider_model?: string | null;
  model_id?: string | null;
  url?: string | null;
  poster_url?: string | null;
  error_message?: string | null;
  video_project_id?: string | null;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface PlayQuote {
  meter: string;
  per_item: number;
  count: number;
  total: number;
  base: number;
  breakdown: Record<string, unknown>;
}

export interface PlayGenerateResponse {
  generation: PlayGeneration;
  generations?: PlayGeneration[];
  message?: string | null;
}

export interface PlayVoiceOption {
  id: string;
  name: string;
  description?: string | null;
  provider?: string;
  source?: "builtin" | "cloned" | "custom";
  available?: boolean;
  provider_voice_id?: string | null;
  /** female | male | neutral */
  gender?: string | null;
  /** e.g. american, british */
  accent?: string | null;
  /** e.g. multilingual, en */
  language?: string | null;
}

/** Workspace access to custom voices (cloning). */
export interface CustomVoicesAccess {
  can_clone: boolean;
  clone_cap: number;
  clone_count: number;
}

export interface PlayVoicesResponse {
  voices: PlayVoiceOption[];
  custom_voices_access?: CustomVoicesAccess;
}

export interface PlayFace {
  id: string;
  workspace_id: string;
  label?: string | null;
  url?: string | null;
  source_kind: string;
  consent_name?: string | null;
  prompt?: string | null;
  status: string;
  created_at: string;
  starter_id?: string | null;
  parent_face_id?: string | null;
  bound_voice_id?: string | null;
  previous_url?: string | null;
}

export interface PlanInfo {
  name: PlanName;
  label: string;
  price_monthly: number;
  video_credit_limit?: number;
  image_generation_limit?: number;
  avatar_lipsync_limit?: number;
  script_generation_limit?: number;
  seat_limit?: number;
}

export interface BillingStatus {
  workspace_id: string;
  billing_workspace_id: string;
  plan: PlanName;
  status: string;
  stripe_configured: boolean;
  plans?: PlanInfo[];
  plan_track?: "content" | "static" | "ads";
  features?: string[];
  suggested_upgrade?: PlanName | null;
  entitlements?: PlanEntitlements;
  script_generations_used: number;
  script_generations_remaining: number;
  voiceover_seconds_used: number;
  voiceover_seconds_remaining: number;
  image_generations_used?: number;
  image_generations_remaining?: number;
  video_generations_used?: number;
  video_generations_remaining?: number;
  avatar_lipsyncs_used?: number;
  avatar_lipsyncs_remaining?: number;
  play_video_used?: number;
  play_video_remaining?: number;
  play_avatar_used?: number;
  play_avatar_remaining?: number;
  play_clip_used?: number;
  play_clip_remaining?: number;
  play_still_used?: number;
  play_still_remaining?: number;
  play_face_used?: number;
  play_face_remaining?: number;
  play_lipsync_used?: number;
  play_lipsync_remaining?: number;
  period_start: string;
  period_end: string;
  cancel_at_period_end: boolean;
}

export interface MaintenanceStatus {
  enabled: boolean;
  message: string | null;
}

/** One turn of the Create pre-flight conversation. */
export interface PlayAssistMessage {
  role: "user" | "assistant";
  content: string;
}

/** The pending generation in the terms the composer owns. */
export interface PlayAssistDraft {
  scene: string;
  line: string;
  duration_seconds: number | null;
  voice: string | null;
  kind?: "avatar" | "lipsync" | "video" | null;
  model?: string | null;
  resolution?: string | null;
  extend_rest?: boolean;
  platform?: string | null;
}

/** A clip this request follows on from, so the planner is not guessing blind. */
export interface PlayAssistSource {
  kind: "continue" | "revoice" | "retry";
  /** The prior clip's prompt. */
  prompt?: string;
  /** Why the prior attempt failed. Only meaningful for a retry. */
  error?: string;
}

/** One tappable alternative for a decision the planner already made. */
export interface PlayAssistChoice {
  label: string;
  value: string;
  selected: boolean;
}

/** A single decision worth surfacing, with the pick already applied. */
export interface PlayAssistOptions {
  header: string;
  choices: PlayAssistChoice[];
}

export interface PlayAssistResponse {
  reply: string;
  draft: PlayAssistDraft;
  /** At most one decision per turn, so the card never becomes a form. */
  options?: PlayAssistOptions | null;
  /** False while something material is unsettled; keep the conversation open. */
  ready: boolean;
  /** Server-stated facts about the clip. Render verbatim, never recompute. */
  summary: string[];
}
