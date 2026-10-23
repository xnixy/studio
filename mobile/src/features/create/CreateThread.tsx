import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  ActionSheetIOS,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as Clipboard from "expo-clipboard";
import { SymbolView } from "expo-symbols";
import type { PlayAssistOptions, PlayGeneration, PlayMode, PlayPlatform } from "@/src/api/types";
import { CreateThreadGenCard } from "@/src/features/create/CreateThreadGenCard";
import { promptForDisplay } from "@/src/features/create/createConstants";
import { hapticLight, hapticSuccess } from "@/src/lib/haptics";
import { isSignedMediaUrlExpired } from "@/src/lib/media";
import type { AppColors } from "@/src/ui/theme";

export type ThreadItem =
  | {
      kind: "user";
      id: string;
      text: string;
      mode: PlayMode;
      platform: PlayPlatform;
      /** Length and credits. Shown on the bubble, not under the field. */
      cost?: string | null;
    }
  | { kind: "system"; id: string; text: string; tone?: "error" | "chat" }
  /** Waiting on the pre-flight. Replaced by its reply, so it is never left behind. */
  | { kind: "thinking"; id: string }
  /**
   * What is about to be generated, laid out to be read rather than filled in.
   * The line lives here and nowhere else, so there is one place to check it.
   */
  | {
      kind: "draft";
      id: string;
      line: string;
      scene: string;
      summary: string[];
      options?: PlayAssistOptions | null;
    }
  | { kind: "gen"; id: string; generation: PlayGeneration; note?: string | null };

type Props = {
  colors: AppColors;
  thread: ThreadItem[];
  onStartNew: () => void;
  onExtend?: (genId: string, gen: PlayGeneration) => void;
  /** Put prompt text back into the composer. */
  onReusePrompt?: (text: string) => void;
  /** Fire the same prompt/settings again (new generate). */
  onRetry?: (gen: PlayGeneration) => void;
  /** Re-poll provider status for a stuck or failed card. */
  onRefreshStatus?: (genId: string) => void;
  /** Tapping an alternative sends it back as the next turn. */
  onChooseOption?: (value: string) => void;
  /** Generate straight from the card, so nobody hunts for the send button. */
  onGenerateDraft?: () => void;
  /** Put the cursor back in the composer to change the draft. */
  onEditDraft?: () => void;
  generatePending?: boolean;
};

function ActionChip({
  label,
  colors,
  onPress,
}: {
  label: string;
  colors: AppColors;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={(e) => {
        e.stopPropagation?.();
        onPress();
      }}
      hitSlop={6}
      style={[styles.actionChip, { backgroundColor: colors.chipOff, borderColor: colors.border }]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Text style={{ color: colors.brand, fontWeight: "700", fontSize: 12 }}>{label}</Text>
    </Pressable>
  );
}

async function copyText(text: string): Promise<boolean> {
  const t = (text || "").trim();
  if (!t) return false;
  try {
    await Clipboard.setStringAsync(t);
    void hapticSuccess();
    return true;
  } catch {
    return false;
  }
}

export function CreateThread({
  colors,
  thread,
  onStartNew,
  onExtend,
  onReusePrompt,
  onRetry,
  onRefreshStatus,
  onChooseOption,
  onGenerateDraft,
  onEditDraft,
  generatePending,
}: Props) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);

  const flashCopied = useCallback((id: string) => {
    setCopiedId(id);
    setTimeout(() => setCopiedId((cur) => (cur === id ? null : cur)), 1400);
  }, []);

  useEffect(() => {
    if (!onRefreshStatus) return;
    for (const item of thread) {
      if (item.kind !== "gen") continue;
      if (isSignedMediaUrlExpired(item.generation.url)) {
        onRefreshStatus(item.generation.id);
      }
    }
  }, [thread, onRefreshStatus]);

  if (thread.length === 0) return null;

  return (
    <View style={styles.root}>
      <View style={styles.toolbar}>
        <Pressable
          onPress={onStartNew}
          hitSlop={8}
          accessibilityRole="button"
          accessibilityLabel="Start new clip"
          style={[styles.newChip, { backgroundColor: colors.brandSoft }]}
        >
          <SymbolView
            name="square.and.pencil"
            size={14}
            tintColor={colors.brand}
            weight="semibold"
            fallback={null}
          />
          <Text style={{ color: colors.brand, fontWeight: "700", fontSize: 14 }}>New</Text>
        </Pressable>
      </View>

      {thread.map((item) => {
        if (item.kind === "user") {
          return (
            <Pressable
              key={item.id}
              accessibilityRole="text"
              accessibilityLabel={promptForDisplay(item.text, item.mode) || "Prompt"}
              onLongPress={() => {
                void hapticLight();
                if (Platform.OS === "ios") {
                  ActionSheetIOS.showActionSheetWithOptions(
                    {
                      options: ["Cancel", "Copy", "Edit in field"],
                      cancelButtonIndex: 0,
                    },
                    (idx) => {
                      if (idx === 1) {
                        void copyText(promptForDisplay(item.text, item.mode)).then((ok) => {
                          if (ok) flashCopied(item.id);
                        });
                      }
                      if (idx === 2) onReusePrompt?.(item.text);
                    },
                  );
                }
              }}
              style={[styles.userBubble, { backgroundColor: colors.userBubble }]}
            >
              <Text style={{ color: colors.userText, fontSize: 16, lineHeight: 22 }}>
                {promptForDisplay(item.text, item.mode) || item.text}
              </Text>
              {item.cost || copiedId === item.id ? (
                <Text style={styles.userMeta}>
                  {[item.cost, copiedId === item.id ? "Copied" : null].filter(Boolean).join(" · ")}
                </Text>
              ) : null}
            </Pressable>
          );
        }
        if (item.kind === "thinking") {
          return (
            <View key={item.id} style={[styles.systemBubble, { backgroundColor: colors.systemBubble }]}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <ActivityIndicator size="small" color={colors.brand} />
                <Text style={{ color: colors.systemText, fontSize: 14 }}>Working it out…</Text>
              </View>
            </View>
          );
        }
        if (item.kind === "draft") {
          return (
            <View
              key={item.id}
              style={[
                styles.draftCard,
                { backgroundColor: colors.systemBubble, borderColor: colors.border },
              ]}
            >
              {item.line ? (
                <>
                  <Text style={[styles.draftLabel, { color: colors.muted }]}>They say</Text>
                  <Text style={[styles.draftLine, { color: colors.fg }]}>{item.line}</Text>
                </>
              ) : null}
              {item.scene ? (
                <>
                  <Text style={[styles.draftLabel, { color: colors.muted, marginTop: 10 }]}>
                    Scene
                  </Text>
                  <Text style={{ color: colors.fg, fontSize: 14, lineHeight: 20 }}>{item.scene}</Text>
                </>
              ) : null}
              {item.summary.length ? (
                <Text style={{ color: colors.brand, fontSize: 12, marginTop: 10 }}>
                  {item.summary.join(" · ")}
                </Text>
              ) : null}
              {item.options?.choices?.length ? (
                <>
                  <Text style={[styles.draftLabel, { color: colors.muted, marginTop: 12 }]}>
                    {item.options.header}
                  </Text>
                  <View style={styles.optionRow}>
                    {item.options.choices.map((c) => (
                      <Pressable
                        key={c.label}
                        onPress={() => {
                          void hapticLight();
                          onChooseOption?.(c.value);
                        }}
                        accessibilityRole="button"
                        accessibilityLabel={c.label}
                        accessibilityState={{ selected: Boolean(c.selected) }}
                        style={[
                          styles.optionChip,
                          {
                            backgroundColor: c.selected ? colors.chipOn : colors.chipOff,
                            borderColor: c.selected ? colors.brand : "transparent",
                          },
                        ]}
                      >
                        <Text
                          style={{
                            color: c.selected ? colors.brand : colors.fg,
                            fontSize: 12,
                            fontWeight: "600",
                          }}
                        >
                          {c.label}
                        </Text>
                      </Pressable>
                    ))}
                  </View>
                </>
              ) : null}
              <View style={styles.actionRow}>
                <Pressable
                  onPress={() => {
                    void hapticLight();
                    onGenerateDraft?.();
                  }}
                  disabled={generatePending}
                  accessibilityRole="button"
                  accessibilityLabel="Generate"
                  accessibilityState={{ disabled: generatePending }}
                  style={[
                    styles.draftPrimary,
                    { backgroundColor: generatePending ? colors.chipOff : colors.brand },
                  ]}
                >
                  {generatePending ? (
                    <ActivityIndicator size="small" color={colors.fg} />
                  ) : (
                    <Text style={{ color: "#fff", fontWeight: "700", fontSize: 13 }}>Generate</Text>
                  )}
                </Pressable>
                <ActionChip label="Change" colors={colors} onPress={() => onEditDraft?.()} />
              </View>
            </View>
          );
        }
        if (item.kind === "system") {
          return (
            <View
              key={item.id}
              style={[
                styles.systemBubble,
                {
                  backgroundColor:
                    item.tone === "error" ? "rgba(255,69,58,0.16)" : colors.systemBubble,
                },
              ]}
            >
              <Text
                style={{
                  color: item.tone === "error" ? colors.danger : colors.systemText,
                  fontSize: 14,
                  lineHeight: 20,
                }}
              >
                {item.text}
              </Text>
              {item.tone === "error" && item.text.trim() ? (
                <View style={[styles.actionRow, { marginTop: 8 }]}>
                  <ActionChip
                    label={copiedId === item.id ? "Copied" : "Copy error"}
                    colors={colors}
                    onPress={() => {
                      void copyText(item.text).then((ok) => {
                        if (ok) flashCopied(item.id);
                      });
                    }}
                  />
                </View>
              ) : null}
            </View>
          );
        }

        return (
          <CreateThreadGenCard
            key={item.id}
            colors={colors}
            generation={item.generation}
            note={item.note}
            playing={playingId === item.id}
            onPlay={() => setPlayingId(item.id)}
            onStop={() => setPlayingId(null)}
            onExtend={onExtend}
            onRetry={onRetry}
            onRefreshStatus={onRefreshStatus}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { gap: 12 },
  toolbar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
  },
  newChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 999,
  },
  userBubble: {
    alignSelf: "flex-end",
    maxWidth: "88%",
    borderRadius: 20,
    borderBottomRightRadius: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  userMeta: {
    color: "rgba(255,255,255,0.72)",
    fontSize: 11,
    fontWeight: "600",
    marginTop: 6,
  },
  systemBubble: {
    alignSelf: "flex-start",
    maxWidth: "90%",
    borderRadius: 20,
    borderBottomLeftRadius: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  actionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 8,
  },
  draftCard: {
    alignSelf: "flex-start",
    maxWidth: "95%",
    borderRadius: 18,
    borderBottomLeftRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  draftLabel: {
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.4,
    textTransform: "uppercase",
    marginBottom: 3,
  },
  draftLine: {
    fontSize: 17,
    lineHeight: 24,
    fontWeight: "600",
  },
  optionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 2,
  },
  draftPrimary: {
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 8,
    alignItems: "center",
    justifyContent: "center",
    minWidth: 92,
  },
  optionChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 11,
    paddingVertical: 6,
  },
  actionChip: {
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
});
