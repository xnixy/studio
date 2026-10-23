
import { Suspense, useLayoutEffect, type ReactNode } from "react";
import { Body1 } from "./ui/Text";
import { Navigate, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { useAuth } from "./auth";
import { dismissHtmlBoot } from "./bootShell";
import { Layout } from "./components/Layout";
import { ScrollToTop } from "./components/ScrollToTop";
import { Spinner } from "./components/Spinner";
import { RouteErrorBoundary } from "./components/RouteErrorBoundary";
import { namedLazy } from "./lazyRetry";
import { PageBoard, PageLabel, PageSection } from "./ui";

/** Runs only after Suspense resolves, hides the single HTML boot overlay. */
function BootDismiss() {
  useLayoutEffect(() => {
    dismissHtmlBoot();
  }, []);
  return null;
}

// Marketing + auth
const HomePage = namedLazy(() => import("./pages/HomePage"), "HomePage");
const AboutPage = namedLazy(() => import("./pages/AboutPage"), "AboutPage");
const PricingPage = namedLazy(() => import("./pages/PricingPage"), "PricingPage");
const ContactPage = namedLazy(() => import("./pages/ContactPage"), "ContactPage");
const DocsHomePage = namedLazy(() => import("./pages/DocsHomePage"), "DocsHomePage");
const DocsArticlePage = namedLazy(() => import("./pages/DocsArticlePage"), "DocsArticlePage");
const PrivacyPage = namedLazy(() => import("./pages/PrivacyPage"), "PrivacyPage");
const TermsPage = namedLazy(() => import("./pages/TermsPage"), "TermsPage");
const LoginPage = namedLazy(() => import("./pages/LoginPage"), "LoginPage");
const RegisterPage = namedLazy(() => import("./pages/RegisterPage"), "RegisterPage");
const CaptchaBridgePage = namedLazy(() => import("./pages/CaptchaBridgePage"), "CaptchaBridgePage");
const ForgotPasswordPage = namedLazy(() => import("./pages/ForgotPasswordPage"), "ForgotPasswordPage");
const ResetPasswordPage = namedLazy(() => import("./pages/ResetPasswordPage"), "ResetPasswordPage");
const VerifyEmailPage = namedLazy(() => import("./pages/VerifyEmailPage"), "VerifyEmailPage");
const SharePage = namedLazy(() => import("./pages/SharePage"), "SharePage");
const NotFoundPage = namedLazy(() => import("./pages/NotFoundPage"), "NotFoundPage");

// Avatar-first app
const PlayPage = namedLazy(() => import("./pages/PlayPage"), "PlayPage");
const AvatarsPage = namedLazy(() => import("./pages/AvatarsPage"), "AvatarsPage");
const VoicesPage = namedLazy(() => import("./pages/VoicesPage"), "VoicesPage");
const ClipsPage = namedLazy(() => import("./pages/ClipsPage"), "ClipsPage");
const ClipDetailPage = namedLazy(() => import("./pages/ClipDetailPage"), "ClipDetailPage");
const ProfilePage = namedLazy(() => import("./pages/ProfilePage"), "ProfilePage");
const BillingPage = namedLazy(() => import("./pages/BillingPage"), "BillingPage");
const AdminPage = namedLazy(() => import("./pages/AdminPage"), "AdminPage");

function RouteFallback() {
  return <Spinner />;
}

function loginRedirectPath(): string {
  if (typeof window === "undefined") return "/login";
  const path = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  // Only same-origin relative paths; avoid open redirects.
  if (!path.startsWith("/") || path.startsWith("//")) return "/login";
  return `/login?next=${encodeURIComponent(path)}`;
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const auth = useAuth();
  if (!auth.initialized) {
    return <Spinner />;
  }
  if (!auth.isAuthenticated) {
    return <Navigate to={loginRedirectPath()} replace />;
  }
  if (!auth.user?.email_verified) {
    return <Navigate to="/verify-email" replace />;
  }
  return children;
}

function AdminRoute({ children }: { children: ReactNode }) {
  const auth = useAuth();
  if (!auth.initialized) {
    return <Spinner />;
  }
  if (!auth.isAuthenticated) {
    return <Navigate to={loginRedirectPath()} replace />;
  }
  if (!auth.user?.email_verified) {
    return <Navigate to="/verify-email" replace />;
  }
  return auth.isAdmin ? children : <Navigate to="/play" replace />;
}

function MaintenanceGate({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const maintenance = useQuery({
    queryKey: ["maintenance"],
    queryFn: api.maintenance,
    staleTime: 30_000,
    retry: 1,
    retryDelay: 800,
  });

  if (!auth.initialized || (maintenance.isPending && !maintenance.isFetched && !maintenance.isError)) {
    return <Spinner />;
  }

  if (maintenance.data?.enabled && !auth.isAdmin) {
    return (
      <BootDismissWrap>
        <main
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            padding: "24px",
          }}
        >
          <PageBoard narrow>
            <PageSection>
              <PageLabel>Studio</PageLabel>
              <Body1>
                {maintenance.data.message || "The site is currently under maintenance. Please check back soon."}
              </Body1>
            </PageSection>
          </PageBoard>
        </main>
      </BootDismissWrap>
    );
  }

  return children;
}

function BootDismissWrap({ children }: { children: ReactNode }) {
  useLayoutEffect(() => {
    dismissHtmlBoot();
  }, []);
  return children;
}

export function App() {
  return (
    <MaintenanceGate>
      <ScrollToTop />
      <Layout>
        <RouteErrorBoundary>
          <Suspense fallback={<RouteFallback />}>
            <BootDismiss />
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/pricing" element={<PricingPage />} />
              <Route
                path="/play"
                element={
                  <ProtectedRoute>
                    <PlayPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/avatars"
                element={
                  <ProtectedRoute>
                    <AvatarsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/voices"
                element={
                  <ProtectedRoute>
                    <VoicesPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/clips"
                element={
                  <ProtectedRoute>
                    <ClipsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/clips/:clipId"
                element={
                  <ProtectedRoute>
                    <ClipDetailPage />
                  </ProtectedRoute>
                }
              />

              <Route path="/share/:token" element={<SharePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/captcha-bridge" element={<CaptchaBridgePage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />
              <Route path="/verify-email" element={<VerifyEmailPage />} />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/billing"
                element={
                  <ProtectedRoute>
                    <BillingPage />
                  </ProtectedRoute>
                }
              />
              <Route path="/growth" element={<Navigate to="/billing" replace />} />
              <Route
                path="/admin"
                element={
                  <AdminRoute>
                    <AdminPage />
                  </AdminRoute>
                }
              />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/docs" element={<DocsHomePage />} />
              <Route path="/docs/:slug" element={<DocsArticlePage />} />
              <Route path="/roadmap" element={<Navigate to="/" replace />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              <Route path="/terms" element={<TermsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </RouteErrorBoundary>
      </Layout>
    </MaintenanceGate>
  );
}
