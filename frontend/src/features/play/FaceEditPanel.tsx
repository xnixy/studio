import { Loader2, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api";
import type { PlayFace } from "../../types";
import { resolveMediaUrl } from "../../lib/mediaUrl";
import { Button, Field, Input, MessageBar } from "../../ui";
import { Caption1 } from "../../ui/Text";
import { cn } from "../../lib/cn";

const TOUCHUP_CHIPS = ["Polish", "Softer skin", "Better light", "Tidy hair", "Sharper"] as const;
const LOOK_CHIPS = ["Black blazer", "White tee", "Glasses", "Tied-back hair", "Clean shave"] as const;

export function FaceEditPanel({
  token,
  workspaceId,
  face,
  onUpdated,
}: {
  token: string;
  workspaceId: string;
  face: PlayFace;
  onUpdated: (face: PlayFace) => void;
}) {
  const qc = useQueryClient();
  const [kind, setKind] = useState<"touchup" | "look">("touchup");
  const [chip, setChip] = useState<string | null>(null);
  const [field, setField] = useState("");
  const [compare, setCompare] = useState(50);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlayFace | null>(null);

  const voicesQuery = useQuery({
    queryKey: ["play", "voices", workspaceId],
    queryFn: () => api.listPlayVoices(token, workspaceId),
    enabled: Boolean(workspaceId),
    staleTime: 30_000,
  });
  const bound = (voicesQuery.data?.voices || []).find((v) => v.id === face.bound_voice_id);

  const instruction = useMemo(() => {
    const extra = field.trim();
    if (chip && extra) return `${chip}. ${extra}`;
    return extra || chip || "";
  }, [chip, field]);

  const apply = useMutation({
    mutationFn: () =>
      api.editPlayFace(token, face.id, {
        workspace_id: workspaceId,
        instruction,
        kind,
        save: kind === "look" ? "new" : "replace",
      }),
    onSuccess: (next) => {
      setResult(next);
      setError(null);
      void qc.invalidateQueries({ queryKey: ["play", "faces", workspaceId] });
      onUpdated(next);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not edit this face.");
    },
  });

  const undo = useMutation({
    mutationFn: () => api.restorePlayFace(token, face.id, workspaceId),
    onSuccess: (next) => {
      setResult(null);
      void qc.invalidateQueries({ queryKey: ["play", "faces", workspaceId] });
      onUpdated(next);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not undo.");
    },
  });

  const bind = useMutation({
    mutationFn: (boundVoiceId: string | null) =>
      api.bindPlayFaceVoice(token, face.id, workspaceId, boundVoiceId),
    onSuccess: (next) => {
      void qc.invalidateQueries({ queryKey: ["play", "faces", workspaceId] });
      onUpdated(next);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not bind this voice.");
    },
  });

  const beforeUrl = resolveMediaUrl(result?.previous_url || face.url);
  const afterUrl = resolveMediaUrl(result?.url || face.url);
  const chips = kind === "touchup" ? TOUCHUP_CHIPS : LOOK_CHIPS;

  return (
    <div className="grid gap-4 rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] p-3 md:grid-cols-[minmax(12rem,20rem)_1fr] md:items-start md:gap-5">
      <div className="grid gap-3">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={cn(
            "rounded-full border px-3 py-1.5 text-sm font-semibold",
            kind === "touchup"
              ? "border-[var(--studio-brand)] text-[var(--studio-brand)]"
              : "border-transparent bg-[var(--studio-fill-quiet)] text-[var(--studio-fg-muted)]",
          )}
          onClick={() => {
            setKind("touchup");
            setChip(null);
            setResult(null);
          }}
        >
          Touch up
        </button>
        <button
          type="button"
          className={cn(
            "rounded-full border px-3 py-1.5 text-sm font-semibold",
            kind === "look"
              ? "border-[var(--studio-brand)] text-[var(--studio-brand)]"
              : "border-transparent bg-[var(--studio-fill-quiet)] text-[var(--studio-fg-muted)]",
          )}
          onClick={() => {
            setKind("look");
            setChip(null);
            setResult(null);
          }}
        >
          New look
        </button>
      </div>
      <Caption1>
        {kind === "touchup" ? "Same person. Cleaner plate." : "Keeps this face. Saves a new avatar."}
      </Caption1>
      <div className="relative mx-auto w-full max-w-[20rem] overflow-hidden rounded-xl bg-[var(--studio-fill-quiet)] md:mx-0">
        {afterUrl ? (
          <img src={afterUrl} alt="" className="block aspect-square w-full object-cover" />
        ) : null}
        {result && beforeUrl ? (
          <div
            className="absolute inset-0 overflow-hidden"
            style={{ width: `${compare}%` }}
          >
            <img src={beforeUrl} alt="" className="h-full w-[100%] max-w-none object-cover" />
          </div>
        ) : null}
        {result ? (
          <input
            type="range"
            min={0}
            max={100}
            value={compare}
            onChange={(e) => setCompare(Number(e.target.value))}
            className="absolute bottom-3 left-3 right-3"
            aria-label="Compare before and after"
          />
        ) : null}
      </div>
      </div>
      <div className="grid gap-3 content-start">
      <div className="flex flex-wrap gap-2">
        {chips.map((item) => (
          <button
            key={item}
            type="button"
            className={cn(
              "rounded-full border px-3 py-1 text-sm",
              chip === item
                ? "border-[var(--studio-brand)] text-[var(--studio-brand)]"
                : "border-[var(--studio-border)] text-[var(--studio-fg-muted)]",
            )}
            onClick={() => setChip((cur) => (cur === item ? null : item))}
          >
            {item}
          </button>
        ))}
      </div>
      <Field label={kind === "look" ? "Outfit or hair" : "Anything else"}>
        <Input
          value={field}
          onChange={(e) => setField(e.target.value)}
          placeholder={kind === "look" ? "red silk shirt, gold hoops" : "optional notes"}
        />
      </Field>
      {error ? <MessageBar intent="error">{error}</MessageBar> : null}
      <Caption1>Uses 1 face credit.</Caption1>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          disabled={!instruction.trim() || apply.isPending}
          onClick={() => apply.mutate()}
        >
          {apply.isPending ? <Loader2 size={14} className="animate-spin" aria-hidden /> : null}
          Apply · 1 credit
        </Button>
        {result ? (
          <>
            <Button type="button" variant="secondary" onClick={() => setResult(null)}>
              Keep
            </Button>
            {result.previous_url || face.previous_url ? (
              <Button type="button" variant="secondary" onClick={() => undo.mutate()}>
                <RotateCcw size={14} aria-hidden />
                Back to original
              </Button>
            ) : null}
          </>
        ) : null}
      </div>
      <div className="grid gap-1">
        <Caption1>Voice</Caption1>
        <Caption1>
          This Face uses that voice on Talking and spoken Scene.
        </Caption1>
        <select
          className="min-h-10 max-w-xs rounded-lg border border-[var(--studio-border)] bg-[var(--studio-panel)] px-3 text-sm"
          value={face.bound_voice_id || ""}
          disabled={bind.isPending}
          onChange={(e) => bind.mutate(e.target.value || null)}
        >
          <option value="">None</option>
          {(voicesQuery.data?.voices || []).map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
        <Caption1>
          <Link
            className="font-semibold text-[var(--studio-brand)] no-underline"
            to={`/voices?bind_face_id=${encodeURIComponent(face.id)}&return=play`}
          >
            {bound ? "More voices" : "Add your voice"}
          </Link>
        </Caption1>
      </div>
      </div>
    </div>
  );
}
