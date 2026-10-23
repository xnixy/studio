import type { DocArticle, DocBlock } from "./types";

function blockText(block: DocBlock): string {
  switch (block.type) {
    case "p":
    case "h2":
    case "h3":
      return block.text;
    case "ul":
    case "ol":
    case "steps":
      return block.items.join(" ");
    case "callout":
      return `${block.title || ""} ${block.text}`;
    case "links":
      return block.items.map((item) => item.label).join(" ");
    default:
      return "";
  }
}

export function articleSearchText(article: DocArticle): string {
  return [article.title, article.description, article.slug, ...article.body.map(blockText)].join(" ").toLowerCase();
}

export function filterArticles(articles: DocArticle[], query: string): DocArticle[] {
  const q = query.trim().toLowerCase();
  if (!q) return articles;
  const terms = q.split(/\s+/).filter(Boolean);
  return articles.filter((article) => {
    const hay = articleSearchText(article);
    return terms.every((term) => hay.includes(term));
  });
}
