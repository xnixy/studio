export type Role = "user" | "admin";

export type ContactTopic = "general" | "account";

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
}

export interface MaintenanceStatus {
  enabled: boolean;
  message: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  created_at: string;
  role: Role;
  permissions: Record<string, boolean>;
  full_name: string | null;
  is_disabled?: boolean;
  last_login_at?: string | null;
  workspace_count?: number;
}

export interface AdminContact {
  id: string;
  name: string;
  email: string;
  topic: ContactTopic;
  message: string;
  created_at: string;
  resolved_at?: string | null;
}

export interface AdminOverview {
  users: number;
  admins: number;
  disabled_users: number;
  workspaces: number;
  contacts_open: number;
  contacts_total: number;
  jobs_queued: number;
  jobs_running: number;
  jobs_failed: number;
  renders_queued: number;
  renders_running: number;
  subscriptions_by_plan: Record<string, number>;
  maintenance_enabled: boolean;
  stripe_configured: boolean;
  redis_healthy: boolean;
  ffmpeg_available: boolean;
  r2_enabled: boolean;
  xai_configured: boolean;
}

/** Personal account billing root (internal workspace id). */

export interface AdminBoost {
  id: string;
  addon_type: string;
  quantity: number;
  notes: string | null;
  status: string;
  monthly_total_cents: number;
}

export interface AdminWorkspaceRow {
  id: string;
  name: string;
  owner_email: string | null;
  plan: string;
  subscription_status: string;
  created_at: string;
  limit_overrides: Record<string, number>;
  effective_limits: Record<string, number>;
  boosts?: AdminBoost[];
}

export interface AdminJobRow {
  id: string;
  workspace_id: string;
  job_type: string;
  status: string;
  attempts: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface AdminJobStats {
  queued: number;
  running: number;
  failed: number;
  completed: number;
  canceled: number;
}

export interface AdminUsageRow {
  workspace_id: string;
  workspace_name: string;
  event_type: string;
  total_quantity: number;
}

export interface AdminAuditRow {
  id: string;
  workspace_id: string;
  workspace_name?: string | null;
  owner_email?: string | null;
  actor_id: string | null;
  actor_email?: string | null;
  actor_name?: string | null;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AdminAuditPage {
  items: AdminAuditRow[];
  total: number;
  limit: number;
  offset: number;
}

export type WorkspaceRole = "owner" | "admin" | "editor" | "viewer";

export type WorkspaceType = "personal" | "brand";

export type PlanName = "free" | "starter" | "creator" | "studio";

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

export interface Plan {
  name: PlanName;
  label: string;
  script_generation_limit: number;
  voiceover_seconds_limit: number;
  workspace_limit: number;
  seat_limit: number;
  price_monthly: number;
  competitor_limit?: number;
  video_credit_limit?: number;
  image_generation_limit?: number;
  avatar_lipsync_limit?: number;
  play_video_limit?: number;
  play_avatar_limit?: number;
  play_clip_limit?: number;
  play_still_limit?: number;
  play_face_limit?: number;
  play_lipsync_limit?: number;
  storage_gb_limit?: number;
  priority_rendering?: boolean;
  monitoring_scan_limit?: number;
  import_row_limit?: number;
  recommendation_limit?: number;
  trend_score_limit?: number;
}

export interface PlanEntitlements {
  modes: string[];
  advanced_models: boolean;
  min_plan_for_advanced: string;
  suggested_upgrade: string;
}

export interface BillingStatus {
  workspace_id: string;
  billing_workspace_id: string;
  plan: PlanName;
  status: string;
  stripe_configured: boolean;
  plans: Plan[];
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
  /** Per-function Create meters */
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

export interface BillingSession {
  url: string | null;
  configured: boolean;
  message: string;
}

export interface UsageEvent {
  id: string;
  event_type: string;
  quantity: number;
  status: string;
  created_at: string;
}

export type VideoAssetStatus = "queued" | "processing" | "ready" | "failed" | "expired";

export interface AppNotification {
  id: string;
  workspace_id: string;
  type: string;
  title: string;
  body: string | null;
  href: string | null;
  entity_kind: string | null;
  entity_id: string | null;
  payload: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}

export interface NotificationPreference {
  id: string;
  workspace_id: string | null;
  event_type: string;
  in_app: boolean;
  email: boolean;
  toast: boolean;
  updated_at: string;
}

export interface VideoAsset {
  id: string;
  workspace_id: string;
  video_project_id: string;
  video_scene_id: string | null;
  asset_type: "image" | "video" | "audio" | "stock" | "upload" | "render" | "text_card";
  source: "xai" | "gemini" | "sync_labs" | "upload" | "stock" | "render" | "system";
  status: VideoAssetStatus;
  prompt: string | null;
  provider: string | null;
  provider_model: string | null;
  provider_request_id: string | null;
  provider_url: string | null;
  storage_url: string | null;
  cost_usd_ticks: number | null;
  error_message: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type ReviewResourceType = "concept" | "video_project" | "report" | "brief" | "custom";

export type AddOnType =
  | "seats"
  | "monitored_competitors"
  | "video_credits"
  | "image_generations"
  | "avatar_lipsyncs"
  | "script_generations"
  | "voiceover_minutes"
  | "storage_gb"
  | "priority_rendering";

export type CreditPackName =
  | "video_10"
  | "video_25"
  | "image_50"
  | "voice_30m";

/** Chat-first playground generation. */

export type PlayMode = "image" | "video" | "avatar" | "lipsync";

export type PlayPlatform = "tiktok" | "reels" | "shorts" | "feed" | "custom";

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

export interface PlayQuote {
  meter: string;
  per_item: number;
  count: number;
  total: number;
  base: number;
  breakdown: Record<string, unknown>;
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
  /** Signed still frame (clip poster when ready; face while processing). */
  poster_url?: string | null;
  error_message?: string | null;
  video_project_id?: string | null;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface PlayGenerateResponse {
  generation: PlayGeneration;
  generations?: PlayGeneration[];
  message?: string | null;
}

export interface PlayModelOption {
  id: string;
  label: string;
  modality: string;
  provider: string;
  blurb: string;
  credit_meter: string;
  /** Meter tokens burned per generation (premium models cost more). */
  token_cost: number;
  default: boolean;
  enabled: boolean;
  max_duration_seconds?: number | null;
  /** Video: may attach a face plate as identity. False for Veo Lite, etc. */
  supports_face_reference?: boolean;
  lane?: "fast" | "advanced";
  requires_plan?: string | null;
  locked?: boolean;
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

/** Saved face in the workspace library (upload, generated, or a new look). */

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

/** Built-in TTS or workspace-cloned voice for lip-sync. */

export type PlayVoiceSource = "builtin" | "cloned" | "custom";

export interface PlayVoiceOption {
  id: string;
  /** Display name from API (`name`). */
  name: string;
  description?: string | null;
  provider?: string;
  source?: PlayVoiceSource;
  /** Provider voice id when different from our row id. */
  provider_voice_id?: string | null;
  /** False when listed but not yet usable (e.g. custom cloning not open). */
  available?: boolean;
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
  custom_voices_access: CustomVoicesAccess;
}

export interface CreditPack {
  name: CreditPackName;
  label: string;
  description: string;
  price_cents: number;
  grants: Record<string, number>;
  stripe_configured: boolean;
}

export interface BillingCreditGrant {
  id: string;
  workspace_id: string;
  pack_name: string;
  label: string;
  grants: Record<string, number>;
  amount_cents: number;
  status: "active" | "refunded" | "expired";
  period_start: string;
  period_end: string;
  created_at: string;
}

export interface ShareLinkPublic {
  title: string;
  resource_type: ReviewResourceType;
  allow_download: boolean;
  snapshot: Record<string, unknown>;
  requires_password: boolean;
}

export interface BillingAddOn {
  id: string;
  workspace_id: string;
  addon_type: AddOnType;
  quantity: number;
  unit_price_cents: number;
  status: "active" | "canceled";
  notes: string | null;
  monthly_total_cents: number;
  created_at: string;
  updated_at: string;
}

export interface EffectiveLimits {
  plan: PlanName;
  seat_limit: number;
  competitor_limit: number;
  video_credit_limit: number;
  image_generation_limit?: number;
  avatar_lipsync_limit?: number;
  storage_gb_limit: number;
  priority_rendering: boolean;
  script_generation_limit: number;
  voiceover_seconds_limit: number;
  monitoring_scan_limit: number;
  import_row_limit: number;
  recommendation_limit: number;
  trend_score_limit: number;
  addons: BillingAddOn[];
  credit_grants?: BillingCreditGrant[];
  packs?: CreditPack[];
}
