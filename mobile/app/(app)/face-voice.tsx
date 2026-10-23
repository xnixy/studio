import { useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams, useNavigation } from "expo-router";
import { SymbolView } from "expo-symbols";
import { api, ApiError } from "@/src/api/client";
import { GlassSurface } from "@/src/components/GlassSurface";
import { Screen } from "@/src/components/Screen";
import { SettingsGroup } from "@/src/components/SettingsList";
import { alertError } from "@/src/lib/alerts";
import { hapticSuccess } from "@/src/lib/haptics";
import {
  FALLBACK_VOICES,
  isClonedVoice,
  matchesVoiceSearch,
} from "@/src/lib/stockVoices";
import { liquidGlassStackHeaderOptions } from "@/src/ui/nav";
import { useAppColors } from "@/src/ui/theme";
import { useWorkspace } from "@/src/workspace/WorkspaceContext";

function lastParam(value: string | string[] | undefined): string {
  const raw = Array.isArray(value) ? value[value.length - 1] : value;
  return (raw || "").trim();
}

export default function FaceVoiceScreen() {
  const colors = useAppColors();
  const navigation = useNavigation();
  const qc = useQueryClient();
  const workspace = useWorkspace();
  const workspaceId = workspace.activeWorkspaceId;
  const params = useLocalSearchParams<{ id?: string | string[] }>();
  const faceId = lastParam(params.id);
  const [query, setQuery] = useState("");

  useEffect(() => {
    navigation.setOptions({
      title: "Voice",
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
  const rows = voicesQuery.data?.voices?.length ? voicesQuery.data.voices : FALLBACK_VOICES;
  const matched = useMemo(
    () => rows.filter((v) => matchesVoiceSearch(v, query)),
    [query, rows],
  );
  const custom = matched.filter(isClonedVoice);
  const builtin = matched.filter((v) => !isClonedVoice(v));

  const bind = useMutation({
    mutationFn: (boundVoiceId: string | null) => {
      if (!workspaceId || !faceId) throw new ApiError("No face.", 400);
      return api.bindPlayFaceVoice(faceId, workspaceId, boundVoiceId);
    },
    onSuccess: async () => {
      void hapticSuccess();
      await qc.invalidateQueries({ queryKey: ["play-faces", workspaceId] });
      router.back();
    },
    onError: (err) => {
      const raw = err instanceof ApiError ? err.message : "Could not save that voice.";
      const msg = /uuid/i.test(raw) ? "Could not save that voice. Try again in a moment." : raw;
      alertError("Voice", msg);
    },
  });

  const pick = (id: string) => {
    if (bind.isPending) return;
    if (face?.bound_voice_id === id) {
      router.back();
      return;
    }
    bind.mutate(id);
  };

  return (
    <Screen contentContainerStyle={{ padding: 16, gap: 18 }}>
      <GlassSurface intensity={40} radius={12} contentStyle={styles.searchWrap}>
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder="Search"
          placeholderTextColor={colors.muted}
          accessibilityLabel="Search voices"
          autoCorrect={false}
          autoCapitalize="none"
          style={[styles.search, { color: colors.fg }]}
        />
      </GlassSurface>

      {custom.length ? (
        <SettingsGroup header="Custom">
          {custom.map((v, i) => (
            <PickRow
              key={v.id}
              name={v.name}
              selected={face?.bound_voice_id === v.id}
              last={i === custom.length - 1}
              onPress={() => pick(v.id)}
            />
          ))}
        </SettingsGroup>
      ) : null}

      <SettingsGroup
        header="Built-in"
        footer="This Face uses that voice on Talking and spoken Scene."
      >
        {builtin.length ? (
          builtin.map((v, i) => (
            <PickRow
              key={v.id}
              name={v.name}
              selected={face?.bound_voice_id === v.id}
              last={i === builtin.length - 1}
              onPress={() => pick(v.id)}
            />
          ))
        ) : (
          <View style={styles.empty}>
            <Text style={{ color: colors.muted, fontSize: 15 }}>No matches</Text>
          </View>
        )}
      </SettingsGroup>

      {face?.bound_voice_id ? (
        <SettingsGroup>
          <PickRow
            name="None"
            selected={false}
            last
            destructive
            onPress={() => bind.mutate(null)}
          />
        </SettingsGroup>
      ) : null}
    </Screen>
  );
}

function PickRow({
  name,
  selected,
  last,
  destructive,
  onPress,
}: {
  name: string;
  selected: boolean;
  last: boolean;
  destructive?: boolean;
  onPress: () => void;
}) {
  const colors = useAppColors();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      accessibilityLabel={`${name}${selected ? ", selected" : ""}`}
      style={({ pressed }) => [
        styles.row,
        !last ? { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.separator } : null,
        { opacity: pressed ? 0.55 : 1 },
      ]}
    >
      <Text
        style={{
          flex: 1,
          fontSize: 17,
          color: destructive ? colors.danger : selected ? colors.brand : colors.fg,
        }}
      >
        {name}
      </Text>
      {selected ? (
        <SymbolView
          name={{ ios: "checkmark", android: "check", web: "check" }}
          size={18}
          tintColor={colors.brand}
          weight="semibold"
        />
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  searchWrap: { paddingHorizontal: 12, paddingVertical: 2 },
  search: { paddingVertical: 10, fontSize: 17 },
  row: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    gap: 10,
  },
  empty: { minHeight: 44, justifyContent: "center", paddingHorizontal: 16 },
});
