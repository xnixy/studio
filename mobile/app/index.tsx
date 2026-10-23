import { Redirect } from "expo-router";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/src/auth/AuthContext";

export default function Index() {
  const auth = useAuth();

  if (!auth.initialized) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator />
      </View>
    );
  }

  if (auth.isAuthenticated) {
    if (!auth.user?.email_verified) {
      return <Redirect href={"/(public)/verify-email" as never} />;
    }
    return <Redirect href="/(app)" />;
  }

  // Public main page (not sign-in)
  return <Redirect href="/(public)/welcome" />;
}
