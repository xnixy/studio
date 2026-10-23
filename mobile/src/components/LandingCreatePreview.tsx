/**
 * Marketing Create preview for welcome.
 * iMessage-style thread + frosted glass shell (not a heavy settings card).
 */
import { useMemo, useRef, useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useColorScheme,
  useWindowDimensions,
} from "react-native";
import { Image } from "expo-image";
import { DEMO_AVATARS } from "@/src/lib/demoAvatars";
import {
  avatarPromptPreview,
  composerTabForMode,
} from "@/src/features/create/createConstants";
import { GlassSurface } from "./GlassSurface";

type ClipMode = "avatar" | "image";

const MODES: { id: ClipMode; label: string }[] = [
  { id: "avatar", label: "Clip" },
  { id: "image", label: "Still" },
];

type Props = {
  onGenerate: (payload: { mode: ClipMode; prompt: string; faceId: string | null }) => void;
  ctaLabel?: string;
};

export function LandingCreatePreview({ onGenerate, ctaLabel = "Try it" }: Props) {
  const dark = useColorScheme() === "dark";
  const { width } = useWindowDimensions();
  const isTablet = width >= 768;
  const narrow = width < 380;
  const [mode, setMode] = useState<ClipMode>("avatar");
  const [faceId, setFaceId] = useState(DEMO_AVATARS[0]?.id ?? "maya");
  const [prompt, setPrompt] = useState(DEMO_AVATARS[0]?.scenePrompt ?? "");

  const colors = useMemo(
    () => ({
      fg: dark ? "#F5F5F7" : "#111111",
      muted: dark ? "#A1A1A6" : "#6C6C70",
      brand: dark ? "#0A84FF" : "#007AFF",
      // iMessage-like bubbles
      userBubble: dark ? "#0A84FF" : "#007AFF",
      userText: "#FFFFFF",
      systemBubble: dark ? "rgba(118,118,128,0.28)" : "rgba(120,120,128,0.16)",
      systemText: dark ? "#F5F5F7" : "#111111",
      chipOn: dark ? "rgba(10,132,255,0.28)" : "rgba(0,122,255,0.14)",
      chipOff: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)",
      field: dark ? "rgba(118,118,128,0.24)" : "rgba(120,120,128,0.12)",
      divider: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
      ring: dark ? "rgba(10,132,255,0.9)" : "rgba(0,122,255,0.85)",
    }),
    [dark],
  );

  const needsFace = mode === "avatar";
  const face = DEMO_AVATARS.find((f) => f.id === faceId) ?? DEMO_AVATARS[0];
  const faceSize = isTablet ? 52 : narrow ? 42 : 48;

  // One box, matching the real composer. Kind is confirmed after send.
  const isTalking = mode === "avatar";
  /** The starting prompt is a face's sample, so it clears on a mode change. */
  const promptIsSampleRef = useRef(true);

  /** Typing makes the text the user's own, so a mode change stops clearing it. */
  const editPrompt = (text: string) => {
    promptIsSampleRef.current = false;
    setPrompt(text);
  };

  /** Prose for the bubble: the stored prompt is the joined canonical form. */
  const bubbleText = isTalking ? avatarPromptPreview(prompt) : prompt.trim();

  function selectMode(next: ClipMode) {
    if (mode === next) return;
    if (promptIsSampleRef.current) {
      promptIsSampleRef.current = false;
      setPrompt("");
    } else if (next === "image" && mode !== "image") {
      setPrompt((p) => avatarPromptPreview(p));
    } else if (mode === "avatar" && next !== "avatar") {
      setPrompt((p) => avatarPromptPreview(p));
    }
    setMode(next);
  }

  function pickFace(id: string) {
    const f = DEMO_AVATARS.find((x) => x.id === id);
    if (!f) return;
    setFaceId(f.id);
    if (mode !== "avatar") setMode("avatar");
    promptIsSampleRef.current = true;
    setPrompt(f.scenePrompt);
  }

  const send = () =>
    onGenerate({
      mode,
      prompt: prompt.trim(),
      faceId: needsFace ? faceId : null,
    });

  return (
    <GlassSurface
      intensity={64}
      style={[
        styles.shell,
        {
          maxWidth: isTablet ? 520 : "100%",
          alignSelf: isTablet ? "center" : "stretch",
          width: "100%",
        },
      ]}
      contentStyle={styles.shellInner}
    >
      {/* Minimal chrome, not a form header */}
      <View style={styles.topBar}>
        <View style={styles.liveDot} />
        <Text style={[styles.topTitle, { color: colors.fg }]}>Create</Text>
        <Text style={{ color: colors.muted, fontSize: 13, fontWeight: "500" }}>preview</Text>
      </View>

      {/* Thread */}
      <View style={styles.thread}>
        {bubbleText ? (
          <>
            <View style={[styles.userBubble, { backgroundColor: colors.userBubble }]}>
              {needsFace && face ? (
                <View style={styles.faceRow}>
                  <Image source={face.image} style={styles.bubbleFace} contentFit="cover" />
                  <Text style={{ color: "rgba(255,255,255,0.85)", fontSize: 12, fontWeight: "600" }}>
                    {face.label}
                  </Text>
                </View>
              ) : null}
              <Text style={{ color: colors.userText, fontSize: 15, lineHeight: 21 }}>
                {bubbleText}
              </Text>
              <Text style={styles.metaOnBlue}>
                {composerTabForMode(mode) === "still" ? "Still" : "Clip"} · 9:16
              </Text>
            </View>

            <View style={[styles.systemBubble, { backgroundColor: colors.systemBubble }]}>
              <Text style={{ color: colors.systemText, fontSize: 14, lineHeight: 20 }}>
                {needsFace && face
                  ? `Got it. Using ${face.label} for a vertical clip.`
                  : "Got it. Ready when you are."}
              </Text>
            </View>
          </>
        ) : (
          <Text style={{ color: colors.muted, fontSize: 14, textAlign: "center", paddingVertical: 12 }}>
            {needsFace ? "Pick a face, then write a prompt." : "Write a prompt below."}
          </Text>
        )}
      </View>

      {/* Composer — iMessage-style */}
      <View style={[styles.composer, { borderTopColor: colors.divider }]}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.hScroll}
          contentContainerStyle={styles.hScrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {MODES.map((m) => {
            const on = mode === m.id;
            return (
              <Pressable
                key={m.id}
                onPress={() => selectMode(m.id)}
                accessibilityRole="button"
                accessibilityLabel={m.label}
                accessibilityState={{ selected: on }}
                style={[
                  styles.chip,
                  {
                    backgroundColor: on ? colors.chipOn : colors.chipOff,
                    borderColor: on ? colors.brand : "transparent",
                  },
                ]}
              >
                <Text
                  style={{
                    color: on ? colors.brand : colors.fg,
                    fontWeight: "600",
                    fontSize: 13,
                  }}
                >
                  {m.label}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>

        {needsFace ? (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.hScroll}
            contentContainerStyle={[styles.hScrollContent, { paddingTop: 2 }]}
            keyboardShouldPersistTaps="handled"
          >
            {DEMO_AVATARS.map((f) => {
              const on = f.id === faceId;
              return (
                <Pressable
                  key={f.id}
                  onPress={() => pickFace(f.id)}
                  accessibilityRole="button"
                  accessibilityLabel={f.label}
                  accessibilityState={{ selected: on }}
                  style={styles.facePick}
                >
                  <View
                    style={[
                      styles.faceRing,
                      {
                        borderColor: on ? colors.ring : "transparent",
                        padding: on ? 2 : 0,
                      },
                    ]}
                  >
                    <Image
                      source={f.image}
                      style={{
                        width: faceSize,
                        height: faceSize,
                        borderRadius: faceSize / 2,
                      }}
                      contentFit="cover"
                    />
                  </View>
                  <Text
                    style={{
                      color: on ? colors.brand : colors.muted,
                      fontSize: 11,
                      fontWeight: on ? "700" : "500",
                      marginTop: 4,
                    }}
                    numberOfLines={1}
                  >
                    {f.label}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>
        ) : null}

        <View style={styles.fieldRow}>
          <View style={[styles.field, { backgroundColor: colors.field }]}>
              <TextInput
                value={prompt}
                onChangeText={editPrompt}
                placeholder={mode === "image" ? "Describe the still" : "What is the clip about?"}
                placeholderTextColor={colors.muted}
                multiline
                style={[
                  styles.input,
                  {
                    color: colors.fg,
                    minHeight: isTablet ? 44 : 36,
                    maxHeight: 88,
                  },
                ]}
              />
          </View>
          <Pressable
            onPress={send}
            accessibilityRole="button"
            accessibilityLabel={ctaLabel}
            style={[styles.send, { backgroundColor: colors.brand }]}
          >
            <Text style={styles.sendArrow}>↑</Text>
          </Pressable>
        </View>
      </View>
    </GlassSurface>
  );
}

const styles = StyleSheet.create({
  shell: {
    borderRadius: 28,
    // Soft float over ambient background
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 12 },
    elevation: 8,
  },
  shellInner: {
    borderRadius: 28,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 4,
  },
  liveDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: "#34C759",
  },
  topTitle: {
    fontSize: 15,
    fontWeight: "700",
    letterSpacing: -0.2,
    flex: 1,
  },
  thread: {
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 6,
    gap: 10,
    minHeight: 108,
  },
  userBubble: {
    alignSelf: "flex-end",
    maxWidth: "88%",
    borderRadius: 20,
    borderBottomRightRadius: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  systemBubble: {
    alignSelf: "flex-start",
    maxWidth: "88%",
    borderRadius: 20,
    borderBottomLeftRadius: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  faceRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 },
  bubbleFace: { width: 26, height: 26, borderRadius: 13 },
  metaOnBlue: {
    color: "rgba(255,255,255,0.72)",
    fontSize: 11,
    fontWeight: "600",
    marginTop: 6,
  },
  composer: {
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 12,
    gap: 10,
  },
  hScroll: { flexGrow: 0, flexShrink: 0 },
  hScrollContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingRight: 4,
  },
  chip: {
    borderRadius: 999,
    paddingHorizontal: 13,
    paddingVertical: 7,
    borderWidth: StyleSheet.hairlineWidth,
  },
  facePick: {
    alignItems: "center",
    width: 64,
  },
  faceRing: {
    borderRadius: 999,
    borderWidth: 2,
  },
  fieldRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 8,
  },
  field: {
    flex: 1,
    borderRadius: 22,
    paddingHorizontal: 14,
    paddingVertical: 8,
    justifyContent: "center",
  },
  input: {
    fontSize: 16,
    lineHeight: 21,
    padding: 0,
    textAlignVertical: "center",
  },
  send: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 2,
  },
  sendArrow: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
    marginTop: -1,
  },
});
