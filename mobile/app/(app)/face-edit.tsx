import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams, useNavigation } from "expo-router";
import { api, ApiError } from "@/src/api/client";
import type { PlayFace } from "@/src/api/types";
import { BeforeAfterCompare } from "@/src/components/BeforeAfterCompare";
import { Screen } from "@/src/components/Screen";
import { SettingsGroup, SettingsRow } from "@/src/components/SettingsList";
import { hapticSuccess } from "@/src/lib/haptics";
import { mediaImageSource } from "@/src/lib/media";
import { liquidGlassStackHeaderOptions } from "@/src/ui/nav";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";

const TOUCHUP_CHIPS = ["Polish", "Softer skin", "Better light", "Tidy hair", "Sharper"] as const;
const LOOK_CHIPS = ["Black blazer", "White tee", "Glasses", "Tied-back hair", "Clean shave"] as const;

export default function FaceEditScreen() {
  const colors = useAppColors();
  const navigation = useNavigation();
  const qc = useQueryClient();
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const params = useLocalSearchParams<{ id?: string | string[] }>();
  const faceId = Array.isArray(params.id) ? params.id[params.id.length - 1] : params.id;

  const [kind, setKind] = useState<"touchup" | "look">("touchup");
  const [chip, setChip] = useState<string | null>(null);
  const [field, setField] = useState("");
  const [compare, setCompare] = useState(50);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlayFace | null>(null);

  useEffect(() => {
    navigation.setOptions({
      title: "Edit face",
      ...liquidGlassStackHeaderOptions(colors),
    });
  }, [navigation, colors]);

  const facesQuery = useQuery({
    queryKey: ["play-faces", workspaceId],
    queryFn: () => api.listPlayFaces(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 15_000,
  });
  const face = (facesQuery.data ?? []).find((f) => f.id === faceId) ?? null;

  const voicesQuery = useQuery({
    queryKey: ["play-voices", workspaceId],
    queryFn: () => api.listPlayVoices(workspaceId!),
    enabled: Boolean(workspaceId),
    staleTime: 30_000,
  });
  const boundName = (voicesQuery.data?.voices || []).find((v) => v.id === face?.bound_voice_id)?.name;

  const instruction = useMemo(() => {
    const extra = field.trim();
    if (chip && extra) return `${chip}. ${extra}`;
    return extra || chip || "";
  }, [chip, field]);

  const apply = useMutation({
    mutationFn: () => {
      if (!workspaceId || !face) throw new ApiError("No face.", 400);
      return api.editPlayFace({
        faceId: face.id,
        workspace_id: workspaceId,
        instruction,
        kind,
        save: kind === "look" ? "new" : "replace",
      });
    },
    onSuccess: (next) => {
      setResult(next);
      setCompare(50);
      setError(null);
      void qc.invalidateQueries({ queryKey: ["play-faces", workspaceId] });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not edit this face.");
    },
  });

  const undo = useMutation({
    mutationFn: () => {
      if (!workspaceId || !face) throw new ApiError("No face.", 400);
      return api.restorePlayFace(face.id, workspaceId);
    },
    onSuccess: (next) => {
      setResult(null);
      void qc.invalidateQueries({ queryKey: ["play-faces", workspaceId] });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not undo.");
    },
  });

  const bind = useMutation({
    mutationFn: (boundVoiceId: string | null) => {
      if (!workspaceId || !face) throw new ApiError("No face.", 400);
      return api.bindPlayFaceVoice(face.id, workspaceId, boundVoiceId);
    },
    onSuccess: () => {
      void hapticSuccess();
      void qc.invalidateQueries({ queryKey: ["play-faces", workspaceId] });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not bind that voice.");
    },
  });

  const beforeUrl = mediaImageSource(result?.previous_url || face?.url);
  const afterUrl = mediaImageSource(result?.url || face?.url);
  const chips = kind === "touchup" ? TOUCHUP_CHIPS : LOOK_CHIPS;

  if (!faceId || (!facesQuery.isPending && !face)) {
    return (
      <Screen contentContainerStyle={{ padding: 16 }}>
        <Text style={{ color: colors.muted }}>That face is gone.</Text>
      </Screen>
    );
  }

  return (
    <Screen contentContainerStyle={{ padding: 16, gap: 14 }}>
      <View style={{ flexDirection: "row", gap: 8 }}>
        <Pressable
          onPress={() => {
            setKind("touchup");
            setChip(null);
            setResult(null);
          }}
          style={[
            styles.seg,
            {
              backgroundColor: kind === "touchup" ? colors.chipOn : colors.chipOff,
              borderColor: kind === "touchup" ? colors.brand : "transparent",
            },
          ]}
        >
          <Text style={{ color: kind === "touchup" ? colors.brand : colors.fg, fontWeight: "700" }}>
            Touch up
          </Text>
        </Pressable>
        <Pressable
          onPress={() => {
            setKind("look");
            setChip(null);
            setResult(null);
          }}
          style={[
            styles.seg,
            {
              backgroundColor: kind === "look" ? colors.chipOn : colors.chipOff,
              borderColor: kind === "look" ? colors.brand : "transparent",
            },
          ]}
        >
          <Text style={{ color: kind === "look" ? colors.brand : colors.fg, fontWeight: "700" }}>
            New look
          </Text>
        </Pressable>
      </View>
      <Text style={{ color: colors.muted, fontSize: 13, lineHeight: 18 }}>
        {kind === "touchup" ? "Same person. Cleaner plate." : "Keeps this face. Saves a new avatar."}
      </Text>

      <BeforeAfterCompare
        colors={colors}
        after={afterUrl}
        before={result ? beforeUrl : null}
        compare={compare}
        onCompare={result ? setCompare : undefined}
      />

      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {chips.map((item) => {
          const on = chip === item;
          return (
            <Pressable
              key={item}
              onPress={() => setChip((cur) => (cur === item ? null : item))}
              style={[
                styles.seg,
                {
                  backgroundColor: on ? colors.chipOn : colors.chipOff,
                  borderColor: on ? colors.brand : "transparent",
                },
              ]}
            >
              <Text style={{ color: on ? colors.brand : colors.fg, fontWeight: "600", fontSize: 13 }}>
                {item}
              </Text>
            </Pressable>
          );
        })}
      </View>
      <TextInput
        value={field}
        onChangeText={setField}
        placeholder={kind === "look" ? "red silk shirt, gold hoops" : "optional notes"}
        placeholderTextColor={colors.muted}
        style={{
          backgroundColor: colors.field,
          color: colors.fg,
          borderRadius: 14,
          paddingHorizontal: 12,
          paddingVertical: 10,
          minHeight: 44,
          fontSize: 16,
        }}
      />
      {error ? (
        <Text style={{ color: colors.danger, fontSize: 14, fontWeight: "600" }}>{error}</Text>
      ) : null}
      <Text style={{ color: colors.muted, fontSize: 12 }}>Uses 1 face credit.</Text>
      <Pressable
        onPress={() => apply.mutate()}
        disabled={!instruction.trim() || apply.isPending}
        style={[
          styles.primary,
          { backgroundColor: instruction.trim() && !apply.isPending ? colors.brand : colors.border },
        ]}
      >
        {apply.isPending ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.primaryText}>Apply · 1 credit</Text>
        )}
      </Pressable>
      {result ? (
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Pressable
            onPress={() => setResult(null)}
            style={[styles.seg, { backgroundColor: colors.chipOff }]}
          >
            <Text style={{ color: colors.fg, fontWeight: "700" }}>Keep</Text>
          </Pressable>
          {result.previous_url || face?.previous_url ? (
            <Pressable
              onPress={() => undo.mutate()}
              style={[styles.seg, { backgroundColor: colors.chipOff }]}
            >
              <Text style={{ color: colors.fg, fontWeight: "700" }}>Back to original</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}

      <SettingsGroup footer="This Face uses that voice on Talking and spoken Scene.">
        <SettingsRow
          label="Voice"
          detail={boundName || "None"}
          symbol={{ ios: "waveform", android: "graphic_eq", web: "graphic_eq" }}
          onPress={() =>
            router.push(`/(app)/face-voice?id=${encodeURIComponent(face?.id || "")}` as never)
          }
          last={!face?.bound_voice_id}
        />
        {face?.bound_voice_id ? (
          <SettingsRow
            label="Remove voice"
            symbol={{ ios: "xmark", android: "close", web: "close" }}
            onPress={() => bind.mutate(null)}
            destructive
            last
          />
        ) : null}
      </SettingsGroup>
    </Screen>
  );
}

const styles = StyleSheet.create({
  seg: {
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: StyleSheet.hairlineWidth,
  },
  primary: {
    borderRadius: 14,
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  primaryText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
