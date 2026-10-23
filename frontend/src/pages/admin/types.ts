export type AdminTab =
  | "overview"
  | "users"
  | "accounts"
  | "usage"
  | "jobs"
  | "inbox"
  | "maintenance"
  | "audit";

export type WithBusy = (action: () => Promise<void>, success?: string) => Promise<void>;
