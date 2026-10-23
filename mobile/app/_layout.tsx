import "react-native-gesture-handler";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack, ThemeProvider } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect, useState } from "react";
import { useColorScheme } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import "react-native-reanimated";

import { AuthProvider, useAuth } from "@/src/auth/AuthContext";
import { AppStatusBar } from "@/src/components/AppStatusBar";
import { MaintenanceGate } from "@/src/components/MaintenanceGate";
import { OfflineBanner } from "@/src/components/OfflineBanner";
import { usePrefetchHomeData } from "@/src/features/home/usePrefetchHomeData";
import { useIapRecovery } from "@/src/hooks/useIapRecovery";
import { usePushNotifications } from "@/src/hooks/usePushNotifications";
import { initCrashReporting, setCrashUser } from "@/src/lib/crashReporting";
import { canvasColor, studioNavigationTheme } from "@/src/ui/theme";
import { useWorkspace, WorkspaceProvider } from "@/src/workspace/WorkspaceContext";

export { ErrorBoundary } from "expo-router";

// Before any provider mounts, so a startup crash is still reported.
initCrashReporting();

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10_000,
    },
  },
});

export default function RootLayout() {
  const scheme = useColorScheme();
  const dark = scheme === "dark";
  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: canvasColor(dark) }}>
      <ThemeProvider value={studioNavigationTheme(scheme)}>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <WorkspaceProvider>
              <RootNavigator />
            </WorkspaceProvider>
          </AuthProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}

function RootNavigator() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const dark = useColorScheme() === "dark";
  const [ready, setReady] = useState(false);
  usePushNotifications();
  useIapRecovery(workspace.activeWorkspaceId, auth.isAuthenticated);
  usePrefetchHomeData(workspace.activeWorkspaceId, auth.isAuthenticated);

  useEffect(() => {
    if (auth.initialized) {
      setReady(true);
      void SplashScreen.hideAsync();
    }
  }, [auth.initialized]);

  // Id only, so a crash can be traced to an account without shipping PII.
  useEffect(() => {
    setCrashUser(auth.user?.id ?? null);
  }, [auth.user?.id]);

  if (!ready) {
    return null;
  }

  return (
    <MaintenanceGate bypass={!auth.isAuthenticated}>
      <AppStatusBar />
      <OfflineBanner />
      <Stack
        screenOptions={{
          headerShown: false,
          // index only redirects, so every move at this level is an auth-gate swap,
          // not navigation. Animating it slides the app in from the right on launch.
          animation: "none",
          statusBarTranslucent: true,
          contentStyle: { backgroundColor: canvasColor(dark) },
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="(public)" />
        <Stack.Screen name="(app)" />
      </Stack>
    </MaintenanceGate>
  );
}
