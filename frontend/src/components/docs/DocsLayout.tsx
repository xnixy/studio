import type { ReactNode } from "react";
import { cn } from "../../lib/cn";
import { Input } from "../../ui";
import { Caption1 } from "../../ui/Text";
import { useMemo, useState } from "react";
import { Link, NavLink } from "react-router-dom";

import { allArticles, DOC_SECTIONS } from "../../docs/catalog";
import { filterArticles } from "../../docs/search";
import type { DocSectionId } from "../../docs/types";
import { useDocsStyles } from "../../ui/docsStyles";

export function DocsLayout({
  children,
  activeSlug,
  searchSeed = "",
}: {
  children: ReactNode;
  activeSlug?: string;
  searchSeed?: string;
}) {
  const styles = useDocsStyles();
  const [query, setQuery] = useState(searchSeed);
  const articles = useMemo(() => allArticles(), []);
  const filtered = useMemo(() => filterArticles(articles, query), [articles, query]);

  const bySection = useMemo(() => {
    const map = new Map<DocSectionId, typeof filtered>();
    for (const section of DOC_SECTIONS) {
      map.set(
        section.id,
        filtered.filter((article) => article.section === section.id),
      );
    }
    return map;
  }, [filtered]);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar} aria-label="Documentation">
        <div className="flex items-center justify-between gap-2">
          <Link className={styles.brand} to="/docs">
            Docs
          </Link>
          <Caption1 className="text-[var(--studio-fg-subtle)]">{articles.length} guides</Caption1>
        </div>
        <Input
          className={styles.search}
          type="search"
          value={query}
          onChange={(_, data) => setQuery(data.value)}
          placeholder="Search guides…"
          aria-label="Search docs"
        />

        <nav className={styles.nav}>
          {DOC_SECTIONS.map((section) => {
            const items = bySection.get(section.id) || [];
            if (!items.length && query.trim()) return null;
            return (
              <div key={section.id}>
                <p className={styles.sectionLabel}>{section.label}</p>
                <ul className={styles.navList}>
                  {(query.trim() ? items : articles.filter((a) => a.section === section.id)).map((article) => (
                    <li key={article.slug}>
                      <NavLink
                        to={`/docs/${article.slug}`}
                        className={({ isActive }) =>
                          cn(styles.link, (isActive || activeSlug === article.slug) && styles.linkActive)
                        }
                      >
                        {article.title}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
          {query.trim() && !filtered.length ? <p className={styles.empty}>No guides match that search.</p> : null}
        </nav>

        <Caption1 className={styles.foot}>
          Still stuck? <Link to="/contact">Contact us</Link>
        </Caption1>
      </aside>

      <div className={styles.main}>{children}</div>
    </div>
  );
}
