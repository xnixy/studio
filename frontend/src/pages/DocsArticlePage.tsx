import { ArrowLeft, ArrowRight } from "lucide-react";
import { cn } from "../lib/cn";
import { Link, Navigate, useParams } from "react-router-dom";

import { DocProse } from "../components/docs/DocProse";
import { DocsLayout } from "../components/docs/DocsLayout";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { adjacentArticles, getArticle } from "../docs/catalog";
import { LinkButton } from "../ui";
import { useDocsStyles } from "../ui/docsStyles";

export function DocsArticlePage() {
  const styles = useDocsStyles();
  const { slug = "" } = useParams();
  const article = getArticle(slug);
  const neighbors = article ? adjacentArticles(article.slug) : { prev: null, next: null };

  usePageMeta(
    article ? `${article.title} · Docs · Studio` : "Docs · Studio",
    article?.description || "Studio product documentation",
  );

  if (!article) {
    return (
      <DocsLayout>
        <div className={styles.missing}>
          <h1 className={styles.articleTitle}>Guide not found</h1>
          <p className={styles.articleDesc}>That page doesn’t exist or was moved.</p>
          <LinkButton to="/docs">Back to docs</LinkButton>
        </div>
      </DocsLayout>
    );
  }

  if (slug !== article.slug) {
    return <Navigate to={`/docs/${article.slug}`} replace />;
  }

  const toc = article.body.filter((block) => block.type === "h2") as { type: "h2"; id: string; text: string }[];

  return (
    <DocsLayout activeSlug={article.slug}>
      <article className={styles.article}>
        <header className={styles.articleHeader}>
          <p className={styles.crumb}>
            <Link to="/docs">Docs</Link>
            <span aria-hidden="true"> / </span>
            <span>{article.title}</span>
          </p>
          <h1 className={styles.articleTitle}>{article.title}</h1>
          <p className={styles.articleDesc}>{article.description}</p>
          <p className={styles.articleMeta}>Updated {article.updated}</p>
        </header>

        {toc.length > 1 ? (
          <nav className={styles.toc} aria-label="On this page">
            <p className={styles.tocLabel}>On this page</p>
            <ul className={styles.tocList}>
              {toc.map((item) => (
                <li key={item.id}>
                  <a className={styles.tocLink} href={`#${item.id}`}>
                    {item.text}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}

        <DocProse body={article.body} />

        <footer className={styles.footer}>
          <div className={styles.pager}>
            {neighbors.prev ? (
              <Link className={styles.pagerLink} to={`/docs/${neighbors.prev.slug}`}>
                <ArrowLeft size={16} />
                <span>
                  <small>Previous</small>
                  <br />
                  {neighbors.prev.title}
                </span>
              </Link>
            ) : (
              <span />
            )}
            {neighbors.next ? (
              <Link className={cn(styles.pagerLink, styles.pagerNext)} to={`/docs/${neighbors.next.slug}`}>
                <span>
                  <small>Next</small>
                  <br />
                  {neighbors.next.title}
                </span>
                <ArrowRight size={16} />
              </Link>
            ) : null}
          </div>
          <p className={styles.helpLine}>
            Still stuck? <Link to="/contact">Contact us</Link>. We read every message.
          </p>
        </footer>
      </article>
    </DocsLayout>
  );
}
