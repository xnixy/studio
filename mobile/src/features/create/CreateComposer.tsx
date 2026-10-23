import { useEffect, useRef, useState } from "react";

import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Image } from "expo-image";
import { router } from "expo-router";
import { SymbolView } from "expo-symbols";
import type { PlayFace, PlayMode, PlayVoiceOption } from "@/src/api/types";
import { PROMPT_PLACEHOLDER, avatarPromptForField } from "@/src/features/create/createConstants";
import { ComposerVoiceStrip } from "@/src/features/create/ComposerVoiceStrip";
import { RefStrip, type LocalRefChip } from "@/src/features/create/RefStrip";
import { hapticMedium } from "@/src/lib/haptics";
import { mediaImageSource } from "@/src/lib/media";
import { isClonedVoice } from "@/src/lib/stockVoices";
import type { AppColors } from "@/src/ui/theme";

const INPUT_MIN = 26;
const INPUT_MAX = Platform.OS === "ios" && Platform.isPad ? 200 : 120;

export type ComposerPicker = "none" | "face" | "voice";

type Props = {
  colors: AppColors;
  padBottom: number;
  keyboardLift: number;
  error: string | null;
  mode: PlayMode;
  isExtending: boolean;
  assistPending: boolean;
  assistReady: boolean;
  picker: ComposerPicker;
  selectedVoiceLabel: string;
  lipsyncVoices: PlayVoiceOption[];
  voice: string;
  faces: PlayFace[];
  selectedFace: PlayFace | null;
  needsFace: boolean;
  allowsFace: boolean;
  prompt: string;
  generatePending: boolean;
  canAttachRefs: boolean;
  refsUploading: boolean;
  refChips: LocalRefChip[];
  continuePoster: string | null;
  onToggleVoicePicker: () => void;
  onToggleFacePicker: () => void;
  onSelectVoice: (id: string) => void;
  onSelectFace: (id: string) => void;
  onClearContinue: () => void;
  onPromptChange: (t: string) => void;
  onSend: () => void;
  onOpenAttach: () => void;
  onRemoveRef: (localId: string) => void;
  onRefRoleChange: (localId: string, role: string) => void;
  onFieldFocus: () => void;
  registerFocus?: (focus: () => void) => void;
  offline?: boolean;
};

/**
 * iMessage-style Create bar: plus (refs), face inside the field, voice, send.
 * Clip | Still lives in the header. Length and credits live on the thread.
 */
export function CreateComposer({
  colors,
  padBottom,
  keyboardLift,
  error,
  mode,
  isExtending,
  assistPending,
  assistReady,
  picker,
  selectedVoiceLabel,
  lipsyncVoices,
  voice,
  faces,
  selectedFace,
  needsFace,
  allowsFace,
  prompt,
  generatePending,
  canAttachRefs,
  refsUploading,
  refChips,
  continuePoster,
  onToggleVoicePicker,
  onToggleFacePicker,
  onSelectVoice,
  onSelectFace,
  onClearContinue,
  onPromptChange,
  onSend,
  onOpenAttach,
  onRemoveRef,
  onRefRoleChange,
  onFieldFocus,
  registerFocus,
  offline = false,
}: Props) {
  const missingFace = needsFace && !selectedFace && !isExtending;
  const missingVoice = needsFace && !voice && !isExtending;
  const faceSource = selectedFace ? mediaImageSource(selectedFace.url) : null;
  const continueSource = continuePoster ? mediaImageSource(continuePoster) : null;
  const showVoice = mode !== "image";

  const inputRef = useRef<TextInput>(null);
  const ignoreSizeRef = useRef(false);
  const fieldValue = mode === "avatar" ? avatarPromptForField(prompt) : prompt;
  const [inputH, setInputH] = useState(INPUT_MIN);
  useEffect(() => {
    registerFocus?.(() => inputRef.current?.focus());
  }, [registerFocus]);
  useEffect(() => {
    if (!fieldValue.trim()) setInputH(INPUT_MIN);
  }, [fieldValue]);
  useEffect(() => {
    if (generatePending) inputRef.current?.blur();
  }, [generatePending]);

  const sendInactive =
    generatePending ||
    assistPending ||
    refsUploading ||
    !prompt.trim() ||
    offline ||
    missingFace ||
    missingVoice;

  return (
    <View
      style={[
        styles.dock,
        {
          paddingBottom: padBottom,
          marginBottom: keyboardLift > 0 ? keyboardLift : 0,
        },
      ]}
    >
      {error ? (
        <Text
          accessibilityRole="alert"
          accessibilityLiveRegion="polite"
          style={{ color: colors.danger, fontSize: 13, marginBottom: 8, paddingHorizontal: 4 }}
        >
          {error}
        </Text>
      ) : null}

      {isExtending ? (
        <View style={[styles.extendBanner, { backgroundColor: colors.brandSoft }]}>
          {continueSource ? (
            <Image source={continueSource} style={styles.extendThumb} contentFit="cover" />
          ) : (
            <View style={[styles.extendThumb, { backgroundColor: colors.chipOff }]} />
          )}
          <Text style={{ flex: 1, color: colors.brand, fontWeight: "700", fontSize: 13 }}>
            Extending
          </Text>
          <Pressable
            onPress={onClearContinue}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel="Cancel extend"
          >
            <Text style={{ color: colors.brand, fontWeight: "700", fontSize: 13 }}>Cancel</Text>
          </Pressable>
        </View>
      ) : null}

      {canAttachRefs ? (
        <RefStrip
          items={refChips}
          colors={colors}
          onRemove={onRemoveRef}
          onRoleChange={onRefRoleChange}
        />
      ) : null}

      {picker === "voice" && showVoice ? (
        <ComposerVoiceStrip
          colors={colors}
          voices={lipsyncVoices}
          voiceId={voice}
          hint={
            mode === "video" && !selectedFace
              ? "Add a Face to use this voice on spoken lines."
              : null
          }
          showAdd={
            (mode !== "video" || Boolean(selectedFace)) && !lipsyncVoices.some(isClonedVoice)
          }
          showMore={mode !== "video" || Boolean(selectedFace)}
          bindFaceId={selectedFace?.id}
          onSelect={onSelectVoice}
        />
      ) : null}

      {picker === "face" && allowsFace ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 8, paddingBottom: 10 }}
        >
          <Pressable
            onPress={() => router.push("/(app)/faces")}
            accessibilityRole="button"
            accessibilityLabel="Add a new face"
            style={[styles.faceAdd, { borderColor: colors.border }]}
          >
            <Text style={{ color: colors.brand, fontWeight: "700" }}>+ New</Text>
          </Pressable>
          {selectedFace ? (
            <Pressable
              onPress={() =>
                router.push({
                  pathname: "/(app)/face-edit",
                  params: { id: selectedFace.id },
                } as never)
              }
              accessibilityRole="button"
              accessibilityLabel="Edit face"
              style={[styles.faceAdd, { borderColor: colors.brand }]}
            >
              <Text style={{ color: colors.brand, fontWeight: "700" }}>Edit</Text>
            </Pressable>
          ) : null}
          {faces.slice(0, 16).map((f) => {
            const on = f.id === (selectedFace?.id ?? null);
            const thumb = mediaImageSource(f.url);
            return (
              <Pressable
                key={f.id}
                onPress={() => onSelectFace(f.id)}
                accessibilityRole="button"
                accessibilityLabel={f.label || "Face"}
                accessibilityState={{ selected: on }}
                style={[
                  styles.facePick,
                  {
                    borderColor: on ? colors.brand : colors.border,
                    backgroundColor: on ? colors.brandSoft : colors.field,
                  },
                ]}
              >
                {thumb ? (
                <Image
                  source={thumb}
                  style={styles.faceThumb}
                  contentFit="cover"
                  recyclingKey={f.id}
                />
                ) : (
                  <View style={[styles.faceThumb, { backgroundColor: colors.chipOff }]} />
                )}
                <Text style={{ color: colors.fg, fontSize: 11, maxWidth: 56 }} numberOfLines={1}>
                  {f.label || "Face"}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
      ) : null}

      <View style={styles.bar}>
        {canAttachRefs ? (
          <Pressable
            onPress={onOpenAttach}
            disabled={refsUploading}
            hitSlop={6}
            accessibilityLabel="Add reference"
            accessibilityRole="button"
            style={({ pressed }) => [styles.iconBtn, { opacity: pressed ? 0.55 : 1 }]}
          >
            <SymbolView
              name={{ ios: "plus.circle.fill", android: "add_circle", web: "add_circle" }}
              size={34}
              tintColor={colors.muted}
              weight="regular"
              fallback={
                <Text style={{ color: colors.muted, fontSize: 28, fontWeight: "400" }}>+</Text>
              }
            />
          </Pressable>
        ) : null}

        <View
          style={[
            styles.pill,
            {
              backgroundColor: colors.field,
              borderColor: missingFace ? colors.brand : "transparent",
              borderWidth: missingFace ? 1.5 : 0,
            },
          ]}
        >
          {allowsFace ? (
            <Pressable
              onPress={onToggleFacePicker}
              hitSlop={6}
              style={[
                styles.faceBtn,
                {
                  borderColor: colors.brand,
                  borderStyle: selectedFace ? "solid" : "dashed",
                },
              ]}
              accessibilityLabel={selectedFace ? "Change face" : "Add face"}
              accessibilityRole="button"
              accessibilityState={{ selected: picker === "face" }}
            >
              {faceSource ? (
                <Image source={faceSource} style={styles.faceBtnImg} contentFit="cover" />
              ) : (
                <SymbolView
                  name="person.crop.circle.badge.plus"
                  size={20}
                  tintColor={colors.brand}
                  weight="medium"
                  fallback={
                    <Text style={{ color: colors.brand, fontSize: 12, fontWeight: "700" }}>+</Text>
                  }
                />
              )}
            </Pressable>
          ) : null}

          <View style={[styles.inputWrap, { height: inputH }]}>
            <TextInput
              ref={inputRef}
              value={fieldValue}
              onChangeText={(t) => {
                if (!t) setInputH(INPUT_MIN);
                onPromptChange(t);
              }}
              placeholder={
                isExtending ? "What happens next in this scene…" : PROMPT_PLACEHOLDER[mode]
              }
              placeholderTextColor={colors.muted}
              multiline
              scrollEnabled
              onContentSizeChange={(e) => {
                if (ignoreSizeRef.current) return;
                if (!fieldValue.trim()) {
                  setInputH(INPUT_MIN);
                  return;
                }
                const next = Math.ceil(e.nativeEvent.contentSize.height);
                if (!Number.isFinite(next) || next <= 0) return;
                const clamped = Math.min(INPUT_MAX, Math.max(INPUT_MIN, next));
                setInputH((h) => (Math.abs(h - clamped) > 1 ? clamped : h));
              }}
              style={[styles.input, { color: colors.fg }]}
              editable={!generatePending}
              onFocus={() => {
                ignoreSizeRef.current = true;
                onFieldFocus();
                requestAnimationFrame(() => {
                  requestAnimationFrame(() => {
                    ignoreSizeRef.current = false;
                  });
                });
              }}
              accessibilityLabel="Prompt"
              textAlignVertical={Platform.OS === "android" ? "center" : undefined}
            />
          </View>
        </View>

        {showVoice ? (
          <Pressable
            onPress={onToggleVoicePicker}
            hitSlop={6}
            accessibilityLabel={`Voice, ${selectedVoiceLabel}`}
            accessibilityRole="button"
            accessibilityState={{ selected: picker === "voice" }}
            style={({ pressed }) => [styles.iconBtn, { opacity: pressed ? 0.55 : 1 }]}
          >
            <SymbolView
              name={{ ios: "mic.circle.fill", android: "mic", web: "mic" }}
              size={34}
              tintColor={picker === "voice" ? colors.brand : colors.muted}
              weight="regular"
              fallback={
                <Text style={{ color: picker === "voice" ? colors.brand : colors.muted, fontSize: 13 }}>
                  Voice
                </Text>
              }
            />
          </Pressable>
        ) : null}

        <Pressable
          onPress={() => {
            void hapticMedium();
            onSend();
          }}
          disabled={sendInactive}
          accessibilityRole="button"
          accessibilityLabel={assistReady ? "Generate" : "Send"}
          accessibilityState={{ disabled: sendInactive }}
          hitSlop={6}
          style={({ pressed }) => [
            styles.iconBtn,
            { opacity: pressed && !sendInactive ? 0.7 : 1 },
          ]}
        >
          {generatePending || assistPending ? (
            <ActivityIndicator color={colors.brand} size="small" />
          ) : (
            <SymbolView
              name={{ ios: "arrow.up.circle.fill", android: "arrow_upward", web: "arrow_upward" }}
              size={34}
              tintColor={sendInactive ? colors.chipOff : colors.brand}
              weight="regular"
              fallback={
                <Text
                  style={{
                    color: sendInactive ? colors.muted : colors.brand,
                    fontWeight: "800",
                    fontSize: 18,
                  }}
                >
                  ↑
                </Text>
              }
            />
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  dock: {
    paddingHorizontal: 10,
    paddingTop: 6,
    backgroundColor: "transparent",
  },
  bar: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 8,
  },
  iconBtn: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
  },
  pill: {
    flex: 1,
    flexDirection: "row",
    alignItems: "flex-end",
    borderRadius: 20,
    paddingLeft: 6,
    paddingRight: 10,
    paddingVertical: 4,
    minHeight: 36,
    maxHeight: INPUT_MAX + 12,
    gap: 6,
    overflow: "hidden",
  },
  extendBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderRadius: 16,
    padding: 8,
    marginBottom: 8,
  },
  extendThumb: {
    width: 32,
    height: 44,
    borderRadius: 8,
    backgroundColor: "#111",
  },
  faceAdd: {
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 12,
    paddingVertical: 8,
    justifyContent: "center",
  },
  facePick: {
    alignItems: "center",
    gap: 4,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 6,
  },
  faceThumb: {
    width: 48,
    height: 48,
    borderRadius: 24,
  },
  faceBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  faceBtnImg: {
    width: 28,
    height: 28,
    borderRadius: 14,
  },
  inputWrap: {
    flex: 1,
    minHeight: INPUT_MIN,
    maxHeight: INPUT_MAX,
    overflow: "hidden",
    justifyContent: "center",
  },
  input: {
    width: "100%",
    paddingTop: 4,
    paddingBottom: 4,
    margin: 0,
    fontSize: 17,
    ...(Platform.OS === "android" ? { lineHeight: 22 } : null),
  },
});
