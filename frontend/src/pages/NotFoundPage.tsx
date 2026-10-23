import { usePageMeta } from "../components/marketing/usePageMeta";
import { useAuth } from "../auth";
import { LinkButton } from "../ui";
import { useMarketingStyles } from "../ui/marketingStyles";

export function NotFoundPage() {
  const auth = useAuth();
  const styles = useMarketingStyles();
  usePageMeta("Page not found · Studio", "That page does not exist.");

  return (
    <div className={styles.authCard}>
      <div className={styles.authCardInner}>
        <header>
          <h1 className={styles.authTitle}>Page not found</h1>
          <p className={styles.authLede}>That URL is not a page in Studio. It may have moved, or the link is incomplete.</p>
        </header>
        <div className={styles.authActions}>
          {auth.isAuthenticated ? (
            <LinkButton to="/play">Back to studio</LinkButton>
          ) : (
            <LinkButton to="/">Back home</LinkButton>
          )}
          <LinkButton variant="secondary" to="/docs">
            Docs
          </LinkButton>
        </div>
      </div>
    </div>
  );
}
