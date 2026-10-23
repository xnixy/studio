import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { DocsLayout } from "../components/docs/DocsLayout";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { allArticles, DOC_HOME_PATHS } from "../docs/catalog";
import { useAuth } from "../auth";
import { LinkButton } from "../ui";
import { useDocsStyles } from "../ui/docsStyles";

export function DocsHomePage() {
  const auth = useAuth();
  const styles = useDocsStyles();
  const articles = allArticles();
  usePageMeta(
    "Docs · Studio",
    "Guides for Create: Clip or Still, Talking, Scene, Seedance, credits, faces, voices, and plans.",
  );

  return (
    <DocsLayout>
      <header className={styles.hero}>
        <p className={styles.kicker}>Help center</p>
        <h1 className={styles.heroTitle}>How to get work done in Studio</h1>
        <p className={styles.heroLede}>
          Short guides for Create: write a prompt, confirm the kind, get a clip, download it. Faces, Voices, Library,
          and Billing sit next to that loop.
        </p>
        <div className={styles.ctaRow}>
          {auth.isAuthenticated ? (
            <LinkButton to="/play">
              Open Create
              <ArrowRight size={16} />
            </LinkButton>
          ) : (
            <LinkButton to="/register">
              Create account
              <ArrowRight size={16} />
            </LinkButton>
          )}
          <LinkButton variant="secondary" to="/docs/getting-started">
            Getting started
          </LinkButton>
        </div>
      </header>

      <section className={styles.pathGrid} aria-label="Popular paths">
        {DOC_HOME_PATHS.map((path) => (
          <Link key={path.to} className={styles.pathCard} to={path.to}>
            <h2 className={styles.pathTitle}>{path.title}</h2>
            <p className={styles.pathBody}>{path.body}</p>
            <span className={styles.pathGo}>
              Read guide <ArrowRight size={14} />
            </span>
          </Link>
        ))}
      </section>

      <section className={styles.allSection}>
        <h2 className={styles.allTitle}>All guides</h2>
        <ul className={styles.allList}>
          {articles.map((article) => (
            <li key={article.slug}>
              <Link className={styles.allLink} to={`/docs/${article.slug}`}>
                <span className={styles.allLinkStrong}>{article.title}</span>
                <span className={styles.allLinkDesc}>{article.description}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </DocsLayout>
  );
}
