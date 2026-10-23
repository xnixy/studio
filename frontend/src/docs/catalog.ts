import { DOC_ARTICLES } from "./content";
import type { DocArticle, DocSection, DocSectionId } from "./types";

export const DOC_SECTIONS: DocSection[] = [
  { id: "start", label: "Start here" },
  { id: "create", label: "Create" },
  { id: "teams", label: "Account & plan" },
  { id: "help", label: "Help" },
];

export function allArticles(): DocArticle[] {
  return [...DOC_ARTICLES].sort((a, b) => {
    const sectionOrder =
      DOC_SECTIONS.findIndex((s) => s.id === a.section) - DOC_SECTIONS.findIndex((s) => s.id === b.section);
    if (sectionOrder !== 0) return sectionOrder;
    return a.order - b.order;
  });
}

export function getArticle(slug: string): DocArticle | undefined {
  return DOC_ARTICLES.find((article) => article.slug === slug);
}

export function articlesInSection(section: DocSectionId): DocArticle[] {
  return allArticles().filter((article) => article.section === section);
}

export function adjacentArticles(slug: string): { prev: DocArticle | null; next: DocArticle | null } {
  const list = allArticles();
  const index = list.findIndex((article) => article.slug === slug);
  if (index < 0) return { prev: null, next: null };
  return {
    prev: index > 0 ? list[index - 1] : null,
    next: index < list.length - 1 ? list[index + 1] : null,
  };
}

/** Featured paths on the docs home page */
export const DOC_HOME_PATHS = [
  {
    title: "New here?",
    body: "Sign up, open Create, and make your first clip.",
    to: "/docs/getting-started",
  },
  {
    title: "Make a clip",
    body: "Clip or Still. We confirm Talking or Scene.",
    to: "/docs/create-your-first-clip",
  },
  {
    title: "Models & credits",
    body: "Seedance clips, Grok stills, and what each run spends.",
    to: "/docs/models-and-tokens",
  },
  {
    title: "Voices",
    body: "Clone once. Talking and Scene can use it.",
    to: "/docs/voices-and-clone",
  },
  {
    title: "Faces",
    body: "Generate or upload a face once, reuse free.",
    to: "/docs/avatars-and-faces",
  },
  {
    title: "Plans & credits",
    body: "Monthly credits, packs, and what each plan includes.",
    to: "/docs/billing-and-plans",
  },
  {
    title: "Something stuck?",
    body: "Gens, limits, and media not loading.",
    to: "/docs/troubleshooting",
  },
] as const;
