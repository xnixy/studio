export type DocSectionId = "start" | "create" | "teams" | "help";

export type DocBlock =
  | { type: "p"; text: string }
  | { type: "h2"; id: string; text: string }
  | { type: "h3"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "steps"; items: string[] }
  | { type: "callout"; tone: "tip" | "note" | "warning"; title?: string; text: string }
  | { type: "links"; items: { label: string; to: string }[] };

export interface DocArticle {
  slug: string;
  title: string;
  description: string;
  section: DocSectionId;
  order: number;
  updated: string;
  body: DocBlock[];
}

export interface DocSection {
  id: DocSectionId;
  label: string;
}
