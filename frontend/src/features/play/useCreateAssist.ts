import { useCallback, useRef, useState } from "react";
import { api, ApiError } from "../../api";
import type { PlayAssistDraft, PlayAssistMessage, PlayAssistOptions, PlayAssistSource, PlayMode } from "../../types";

/**
 * The Create pre-flight conversation.
 *
 * Generation is a one shot spend, so every send talks the clip through first:
 * the planner drafts the spoken line, states what it assumed, and hands back a
 * draft the composer shows for editing. Nothing here costs credits.
 *
 * A failure here must not spend. The next send retries the helper. Do not mark
 * the draft ready on error, or the composer skips Assist and generates the raw box.
 */
export type AssistState = {
  messages: PlayAssistMessage[];
  draft: PlayAssistDraft | null;
  pending: boolean;
  ready: boolean;
  summary: string[];
  options: PlayAssistOptions | null;
  error: string | null;
};

const EMPTY: AssistState = {
  messages: [],
  draft: null,
  pending: false,
  ready: false,
  summary: [],
  options: null,
  error: null,
};

export type AssistTurn = {
  reply: string | null;
  draft: PlayAssistDraft | null;
  ready: boolean;
  summary: string[];
  options: PlayAssistOptions | null;
  /** False only while a call is in flight. Never false because one failed. */
  canGenerate: boolean;
};

export function useCreateAssist() {
  const [state, setState] = useState<AssistState>(EMPTY);
  // Guards a reply landing after the user moved on (new draft, mode switch).
  const runRef = useRef(0);

  const reset = useCallback(() => {
    runRef.current += 1;
    setState(EMPTY);
  }, []);

  const send = useCallback(
    async (params: {
      token: string;
      workspaceId: string;
      mode: PlayMode;
      draft: Partial<PlayAssistDraft>;
      /** What the user just typed: their opening prompt or a mid-conversation reply. */
      userText: string;
      /** Set when this follows an existing clip: extend, revoice, or a failed retry. */
      source?: PlayAssistSource | null;
    }): Promise<AssistTurn> => {
      const run = ++runRef.current;
      const outgoing: PlayAssistMessage[] = [
        ...state.messages,
        { role: "user", content: params.userText },
      ];
      setState((s) => ({ ...s, messages: outgoing, pending: true, error: null }));

      try {
        const res = await api.playAssist(params.token, {
          workspace_id: params.workspaceId,
          mode: params.mode,
          draft: params.draft,
          messages: outgoing,
          source: params.source ?? null,
        });
        if (run !== runRef.current) {
          return {
            reply: null,
            draft: null,
            ready: false,
            summary: [],
            options: null,
            canGenerate: true,
          };
        }
        setState({
          messages: [...outgoing, { role: "assistant", content: res.reply }],
          draft: res.draft,
          pending: false,
          ready: res.ready,
          summary: res.summary,
          options: res.options ?? null,
          error: null,
        });
        return {
          reply: res.reply,
          draft: res.draft,
          ready: res.ready,
          summary: res.summary,
          options: res.options ?? null,
          canGenerate: true,
        };
      } catch (err) {
        if (run !== runRef.current) {
          return {
            reply: null,
            draft: null,
            ready: false,
            summary: [],
            options: null,
            canGenerate: true,
          };
        }
        const message =
          err instanceof ApiError
            ? err.message
            : "Could not work that out. Send again. Nothing was spent.";
        setState((s) => ({
          ...s,
          pending: false,
          ready: false,
          draft: null,
          options: null,
          summary: [],
          error: message,
        }));
        return { reply: null, draft: null, ready: false, summary: [], options: null, canGenerate: true };
      }
    },
    [state.messages],
  );

  return { ...state, send, reset };
}
