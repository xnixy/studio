/**
 * Build public/sitemap.xml (and refresh docs links in llms.txt) from doc article slugs.
 * Run via `npm run sitemap` or automatically before `npm run build`.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const contentPath = join(root, "src", "docs", "content.ts");
const sitemapPath = join(root, "public", "sitemap.xml");
const llmsPath = join(root, "public", "llms.txt");

const ORIGIN = "https://example.com";

/** Static marketing / public routes (not the app shell). */
const STATIC_URLS = [
  { path: "/", changefreq: "weekly", priority: "1.0" },
  { path: "/about", changefreq: "monthly", priority: "0.8" },
  { path: "/pricing", changefreq: "monthly", priority: "0.85" },
  { path: "/contact", changefreq: "monthly", priority: "0.8" },
  { path: "/docs", changefreq: "weekly", priority: "0.9" },
  { path: "/login", changefreq: "monthly", priority: "0.4" },
  { path: "/register", changefreq: "monthly", priority: "0.5" },
  { path: "/forgot-password", changefreq: "yearly", priority: "0.2" },
  { path: "/privacy", changefreq: "yearly", priority: "0.3" },
  { path: "/terms", changefreq: "yearly", priority: "0.3" },
];

function docSlugsFromContent(source) {
  const slugs = [];
  const re = /slug:\s*"([a-z0-9-]+)"/g;
  let match;
  while ((match = re.exec(source)) !== null) {
    slugs.push(match[1]);
  }
  return [...new Set(slugs)];
}

function urlEntry({ path, changefreq, priority }) {
  return `  <url>
    <loc>${ORIGIN}${path}</loc>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>
  </url>`;
}

function buildSitemap(slugs) {
  const entries = [
    ...STATIC_URLS.map(urlEntry),
    ...slugs.map((slug) =>
      urlEntry({
        path: `/docs/${slug}`,
        changefreq: "weekly",
        priority: "0.7",
      }),
    ),
  ];
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries.join("\n")}
</urlset>
`;
}

function patchLlmsDocs(llms, slugs, titlesBySlug) {
  const docLinks = [
    `- [Docs home](${ORIGIN}/docs): Guides for Create, models and credits, avatars, plans, and troubleshooting`,
    ...slugs.map((slug) => {
      const title = titlesBySlug.get(slug) || slug;
      return `- [${title}](${ORIGIN}/docs/${slug})`;
    }),
  ].join("\n");

  // Drop every existing Documentation section so re-runs never duplicate.
  const withoutDocs = llms.replace(/\n*## Documentation\n[\s\S]*?(?=\n## |\s*$)/g, "\n");
  const pagesEnd = withoutDocs.search(/\n## Optional\b/);
  const section = `\n## Documentation\n\n${docLinks}\n`;
  if (pagesEnd >= 0) {
    return withoutDocs.slice(0, pagesEnd) + section + withoutDocs.slice(pagesEnd);
  }
  return `${withoutDocs.trimEnd()}\n${section}`;
}

function titlesFromContent(source) {
  const map = new Map();
  // Match each article block's slug then title nearby
  const blockRe = /slug:\s*"([a-z0-9-]+)"[\s\S]*?title:\s*"([^"]+)"/g;
  let match;
  while ((match = blockRe.exec(source)) !== null) {
    map.set(match[1], match[2]);
  }
  return map;
}

const source = readFileSync(contentPath, "utf8");
const slugs = docSlugsFromContent(source);
if (slugs.length < 5) {
  console.error("generate-sitemap: expected multiple doc slugs, got", slugs);
  process.exit(1);
}

const sitemap = buildSitemap(slugs);
writeFileSync(sitemapPath, sitemap, "utf8");
console.log(`Wrote ${sitemapPath} (${STATIC_URLS.length + slugs.length} URLs, ${slugs.length} docs)`);

const titles = titlesFromContent(source);
let llms = readFileSync(llmsPath, "utf8");
llms = patchLlmsDocs(llms, slugs, titles);
writeFileSync(llmsPath, llms, "utf8");
console.log(`Updated docs links in ${llmsPath}`);
