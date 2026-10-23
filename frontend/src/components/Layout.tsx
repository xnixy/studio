import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { Body1, Caption1, Text } from "../ui/Text";
import {
  Clapperboard,
  CreditCard,
  Sparkles,
  LogOut,
  Menu,
  Mic,
  Settings,
  Shield,
  BookOpen,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { Button, IconButton, LinkButton } from "../ui";
import { useDashboardStyles } from "../ui/dashboardStyles";
import { useMarketingStyles } from "../ui/marketingStyles";
import { NotificationBell } from "../features/notifications/NotificationBell";
import { PresenceStrip } from "../features/notifications/PresenceStrip";
import { RealtimeToasts } from "../features/notifications/RealtimeToasts";
import { BrandLogo } from "./BrandLogo";
import { Spinner } from "./Spinner";
import { ThemeToggle } from "./ThemeToggle";

/** Public marketing routes that always use MarketingShell, even when signed in. */
const MARKETING_FORCE_PATHS = ["/about", "/pricing", "/contact", "/privacy", "/terms", "/docs"];

function isMarketingForcePath(pathname: string): boolean {
  return MARKETING_FORCE_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

export function Layout({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const location = useLocation();

  // Native app WebView host for Turnstile: no marketing chrome, no auth gate spinner.
  if (location.pathname === "/captcha-bridge") {
    return <>{children}</>;
  }

  if (!auth.initialized) {
    // Keep the single HTML boot overlay; do not mount a second spinner.
    return <Spinner />;
  }

  if (isMarketingForcePath(location.pathname)) {
    return <MarketingShell>{children}</MarketingShell>;
  }

  if (auth.isAuthenticated) {
    return <DashboardShell>{children}</DashboardShell>;
  }

  return <MarketingShell>{children}</MarketingShell>;
}

function MarketingShell({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const location = useLocation();
  const styles = useMarketingStyles();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isLanding = location.pathname === "/";
  // Centered card layout for all public auth / account-recovery pages
  const isAuth = [
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/verify-email",
  ].includes(location.pathname);
  const isDocs = location.pathname === "/docs" || location.pathname.startsWith("/docs/");
  const isAuthed = auth.isAuthenticated;
  const homeTo = "/";

  // Close drawer on navigation so it never sticks open across pages
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname, location.search]);

  // Lock body scroll while the mobile menu is open (chrome is sticky; page scroll was detaching it)
  useEffect(() => {
    if (!mobileOpen) {
      return;
    }
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [mobileOpen]);

  // Same content rail on all public pages; only landing / auth / docs need layout variants.
  // Legal and about/contact use the default main so the nav chrome width never jumps by route.
  const mainClass = cn(
    styles.main,
    isLanding && styles.mainLanding,
    isAuth && styles.mainAuth,
    isDocs && styles.mainWide,
  );

  function closeMobile() {
    setMobileOpen(false);
  }

  /** Landing home: always go to the top of the page (not mid-page anchors). */
  function goLandingTop(event?: { preventDefault: () => void }) {
    closeMobile();
    if (!isAuthed && (location.pathname === "/" || location.pathname === "")) {
      event?.preventDefault();
      if (location.hash) {
        window.history.replaceState(null, "", "/");
      }
      window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
    }
  }

  const desktopPrimaryNav = (
    <>
      {!isAuthed ? (
        <Link className={styles.railLink} to="/" onClick={goLandingTop}>
          Home
        </Link>
      ) : null}
      <Link className={styles.railLink} to="/about">
        About
      </Link>
      <Link className={styles.railLink} to="/pricing">
        Pricing
      </Link>
      <Link className={styles.railLink} to="/docs">
        Docs
      </Link>
      <Link className={styles.railLink} to="/contact">
        Contact
      </Link>
    </>
  );

  const mobilePrimaryNav = (
    <>
      {!isAuthed ? (
        <Link className={styles.mobileNavLink} to="/" onClick={goLandingTop}>
          Home
        </Link>
      ) : null}
      <Link className={styles.mobileNavLink} to="/about" onClick={closeMobile}>
        About
      </Link>
      <Link className={styles.mobileNavLink} to="/pricing" onClick={closeMobile}>
        Pricing
      </Link>
      <Link className={styles.mobileNavLink} to="/docs" onClick={closeMobile}>
        Docs
      </Link>
      <Link className={styles.mobileNavLink} to="/contact" onClick={closeMobile}>
        Contact
      </Link>
    </>
  );

  return (
    <div className={cn(styles.shell, isLanding && styles.shellLanding)}>
      {mobileOpen ? (
        <button
          type="button"
          className={styles.mobileNavScrim}
          aria-label="Close menu"
          onClick={closeMobile}
        />
      ) : null}

      {/* Fixed chrome: stays pinned while the page scrolls (mobile + desktop). */}
      <div className={styles.chrome}>
        <div className={styles.chromeInner}>
          <header className={styles.rail}>
            <Link className={styles.wordmark} to={homeTo} onClick={goLandingTop} aria-label="Studio home">
              <BrandLogo />
            </Link>

            {/* Desktop center nav, hidden on mobile via CSS */}
            <nav className={styles.railNav} aria-label="Marketing">
              {desktopPrimaryNav}
            </nav>

            <div className={styles.railActions}>
              <ThemeToggle />

              {/* Desktop CTAs, hidden on small screens so the rail stays one row */}
              <div className={styles.railDesktopCtas}>
                {isAuthed ? (
                  <LinkButton to="/play" size="small">
                    Create
                  </LinkButton>
                ) : (
                  <>
                    {/* Keep the same CTAs on every public route so the rail width does not jump. */}
                    <Link className={styles.railLink} to="/login">
                      Sign in
                    </Link>
                    <LinkButton to="/register" size="small">
                      Create account
                    </LinkButton>
                  </>
                )}
              </div>

              {/* Mobile hamburger, every marketing page, including login/register & signed-in public pages */}
              <button
                type="button"
                className={styles.menuButton}
                aria-label={mobileOpen ? "Close menu" : "Open menu"}
                aria-expanded={mobileOpen}
                aria-controls="marketing-mobile-nav"
                onClick={() => setMobileOpen((v) => !v)}
              >
                {mobileOpen ? <X size={20} strokeWidth={2} /> : <Menu size={20} strokeWidth={2} />}
              </button>
            </div>
          </header>

          {mobileOpen ? (
            <div
              id="marketing-mobile-nav"
              className={styles.mobileNav}
              role="navigation"
              aria-label="Mobile"
            >
              {mobilePrimaryNav}
              <div className={styles.mobileNavDivider} />
              {isAuthed ? (
                <Link className={styles.mobileNavCta} to="/play" onClick={closeMobile}>
                  Create
                </Link>
              ) : (
                <>
                  <Link className={styles.mobileNavLink} to="/login" onClick={closeMobile}>
                    Sign in
                  </Link>
                  <Link className={styles.mobileNavCta} to="/register" onClick={closeMobile}>
                    Create account
                  </Link>
                </>
              )}
              <div className={styles.mobileNavDivider} />
              <Link className={styles.mobileNavLink} to="/privacy" onClick={closeMobile}>
                Privacy
              </Link>
              <Link className={styles.mobileNavLink} to="/terms" onClick={closeMobile}>
                Terms
              </Link>
            </div>
          ) : null}
        </div>
      </div>
      <div className={styles.chromeSpacer} aria-hidden="true" />

      <main className={mainClass}>{children}</main>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <Text weight="semibold" size={400}>
              Studio
            </Text>
            <Body1>
              Make Talking, Scene, and stills for TikTok, Reels, and Shorts. Pick a face, spend
              credits, download the file.
            </Body1>
          </div>
          <nav className={styles.footerLinks} aria-label="Footer">
            <Link className={styles.railLink} to="/about">
              About
            </Link>
            <Link className={styles.railLink} to="/pricing">
              Pricing
            </Link>
            <Link className={styles.railLink} to="/docs">
              Docs
            </Link>
            <Link className={styles.railLink} to="/contact">
              Contact
            </Link>
            <Link className={styles.railLink} to="/privacy">
              Privacy
            </Link>
            <Link className={styles.railLink} to="/terms">
              Terms
            </Link>
            {isAuthed ? (
              <Link className={styles.railLink} to="/play">
                Create
              </Link>
            ) : (
              <>
                <Link className={styles.railLink} to="/login">
                  Sign in
                </Link>
                <Link className={styles.railLink} to="/register">
                  Create account
                </Link>
              </>
            )}
          </nav>
          <Caption1 className={styles.footerMeta}>
            © {new Date().getUTCFullYear()} Studio · <a href="mailto:contact@example.com">contact@example.com</a>
          </Caption1>
        </div>
      </footer>
    </div>
  );
}

function DashboardShell({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const styles = useDashboardStyles();
  const [open, setOpen] = useState(false);

  // Drop focus after route change so leftover focus rings don't paint a full-screen line
  useEffect(() => {
    const active = document.activeElement;
    if (active instanceof HTMLElement && active !== document.body) {
      active.blur();
    }
  }, [location.pathname]);

  async function logout() {
    setOpen(false);
    await auth.logout();
    navigate("/", { replace: true });
  }

  function closeNav() {
    setOpen(false);
  }

  const navLink = ({ isActive }: { isActive: boolean }) =>
    cn(styles.navLink, isActive && styles.navLinkActive);

  const nav = (
    <>
      <div className={cn(styles.sidebarSection, styles.sidebarSectionCompact)}>
        <p className={styles.sidebarLabel}>Make</p>
        <NavLink className={navLink} to="/play" onClick={closeNav} end>
          <Sparkles size={18} />
          <span>Create</span>
        </NavLink>
        <NavLink className={navLink} to="/avatars" onClick={closeNav}>
          <UserRound size={18} />
          <span>Faces</span>
        </NavLink>
        <NavLink className={navLink} to="/voices" onClick={closeNav}>
          <Mic size={18} />
          <span>Voices</span>
        </NavLink>
        <NavLink className={navLink} to="/clips" onClick={closeNav}>
          <Clapperboard size={18} />
          <span>Library</span>
        </NavLink>
      </div>

      <div className={styles.sidebarSection}>
        <p className={styles.sidebarLabel}>Account</p>
        <NavLink className={navLink} to="/billing" onClick={closeNav}>
          <CreditCard size={18} />
          <span>Billing</span>
        </NavLink>
        <NavLink className={navLink} to="/profile" onClick={closeNav}>
          <Settings size={18} />
          <span>Profile</span>
        </NavLink>
        <NavLink className={navLink} to="/docs" onClick={closeNav}>
          <BookOpen size={18} />
          <span>Help</span>
        </NavLink>
        {auth.isAdmin ? (
          <NavLink className={navLink} to="/admin" onClick={closeNav}>
            <Shield size={18} />
            <span>Ops</span>
          </NavLink>
        ) : null}
      </div>
    </>
  );

  return (
    <div className={styles.shell}>
      <aside
        className={cn(styles.sidebar, styles.desktopSidebar)}
        aria-label="Primary"
      >
        <div className={styles.sidebarTop}>
          <Link className={styles.wordmark} to="/" aria-label="Studio home">
            <BrandLogo />
          </Link>
          <div className={styles.sidebarTopTools}>
            <NotificationBell />
          </div>
        </div>
        <nav className={styles.sidebarNav}>{nav}</nav>
        <div className={styles.sidebarBottom}>
          <div className={styles.userRow}>
            <div className={styles.userAvatar} aria-hidden="true">
              {(auth.user?.full_name || auth.user?.email || "U").slice(0, 1).toUpperCase()}
            </div>
            <div className={styles.userMeta}>
              <Text weight="semibold">{auth.user?.full_name || "Operator"}</Text>
              <Caption1>{auth.user?.email}</Caption1>
            </div>
            <PresenceStrip />
          </div>
          <div className={styles.sidebarTools}>
            <ThemeToggle />
            <Button variant="subtle" type="button" onClick={logout} icon={<LogOut size={18} />}>
              Sign out
            </Button>
          </div>
        </div>
      </aside>

      <div className={styles.frame}>
        <header className={styles.topbar}>
          <IconButton aria-label="Open navigation" onClick={() => setOpen(true)}>
            <Menu size={20} />
          </IconButton>
          <div className={styles.topbarBrand}>
            <BrandLogo size="sm" />
          </div>
          <div className={styles.topbarSpacer} />
          <NotificationBell />
          <ThemeToggle />
        </header>
        <div className={styles.topbarReserve} aria-hidden="true" />

        <main className={styles.main}>
          {children}
        </main>

        <RealtimeToasts />
      </div>

      {open ? (
        <>
          <div className={styles.backdrop} onClick={closeNav} />
          <aside
            className={cn(styles.sidebar, styles.mobileSidebar)}
            aria-label="Primary"
          >
            <div className={styles.sidebarTop}>
              <Link className={styles.wordmark} to="/" onClick={closeNav} aria-label="Studio home">
                <BrandLogo />
              </Link>
              <IconButton aria-label="Close navigation" onClick={closeNav}>
                <X size={20} />
              </IconButton>
            </div>
            <nav className={styles.sidebarNav}>{nav}</nav>
            <div className={styles.sidebarBottom}>
              <Button variant="subtle" type="button" onClick={logout} icon={<LogOut size={18} />}>
                Sign out
              </Button>
            </div>
          </aside>
        </>
      ) : null}
    </div>
  );
}
