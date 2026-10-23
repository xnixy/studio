import { Text, View } from "react-native";
import { useAppColors } from "../ui/theme";

type Props = {
  message: string;
  tone?: "error" | "info" | "success";
};

/** iOS-style inline banner (RN; works on web too). */
export function StatusBanner({ message, tone = "info" }: Props) {
  const c = useAppColors();
  const color =
    tone === "error" ? c.danger : tone === "success" ? c.success : c.muted;
  const bg =
    tone === "error"
      ? "rgba(255,69,58,0.12)"
      : tone === "success"
        ? "rgba(52,199,89,0.12)"
        : c.brandSoft;

  return (
    <View
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
      style={{
        marginHorizontal: 16,
        marginVertical: 6,
        paddingHorizontal: 14,
        paddingVertical: 12,
        borderRadius: 12,
        backgroundColor: bg,
        borderWidth: 0.5,
        borderColor: color + "44",
      }}
    >
      <Text style={{ color, fontSize: 14, fontWeight: "600", lineHeight: 19 }}>{message}</Text>
    </View>
  );
}
