import { Pressable, ScrollView, Text, View } from "react-native";
import { useAppColors } from "../ui/theme";

type Option = { value: string; label: string };

type Props = {
  label?: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  style?: "menu" | "segmented" | "wheel";
};

/** iOS-style chip / segmented control (RN web-safe). */
export function TaggedPicker({ label, value, options, onChange }: Props) {
  const c = useAppColors();
  const selection = options.some((o) => o.value === value)
    ? value
    : options[0]?.value ?? "";

  return (
    <View style={{ gap: 8 }}>
      {label ? (
        <Text
          style={{
            fontSize: 13,
            fontWeight: "600",
            color: c.muted,
            letterSpacing: 0.2,
          }}
        >
          {label}
        </Text>
      ) : null}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{
          gap: 8,
          padding: 4,
          borderRadius: 12,
          backgroundColor: c.chipOff,
        }}
      >
        {options.map((opt) => {
          const on = opt.value === selection;
          return (
            <Pressable
              key={opt.value}
              onPress={() => onChange(opt.value)}
              accessibilityRole="button"
              accessibilityLabel={opt.label}
              accessibilityState={{ selected: on }}
              style={{
                paddingHorizontal: 14,
                paddingVertical: 8,
                borderRadius: 10,
                backgroundColor: on ? c.card : "transparent",
                // iOS segmented “selected pill” shadow
                shadowColor: "#000",
                shadowOpacity: on ? 0.08 : 0,
                shadowRadius: 3,
                shadowOffset: { width: 0, height: 1 },
              }}
            >
              <Text
                style={{
                  color: on ? c.fg : c.muted,
                  fontWeight: "600",
                  fontSize: 14,
                }}
              >
                {opt.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}
