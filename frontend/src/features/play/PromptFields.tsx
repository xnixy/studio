import type { PlayMode } from "../../types";
import { PROMPT_PLACEHOLDER } from "../../pages/playPageChrome";
import { avatarPromptForField } from "../../lib/playPricing";

type Props = {
  mode: PlayMode;
  /** Extending a clip is always what happens next, not a fresh description. */
  isExtending: boolean;
  prompt: string;
  onPromptChange: (next: string) => void;
  disabled?: boolean;
  /** Marketing shell passes its own recipes; min-heights stay owned here. */
  classNames?: { shell?: string; field?: string };
  /** Lets the draft card's Change action put the cursor in the box. */
  inputRef?: React.Ref<HTMLTextAreaElement>;
};

const SHELL =
  "grid w-full min-w-0 rounded-[20px] border border-[var(--studio-border)] bg-[var(--input-bg,var(--studio-fill-quiet))] focus-within:border-[var(--studio-brand)] focus-within:ring-2 focus-within:ring-[var(--focus-ring)] sm:rounded-[22px]";
const FIELD =
  "w-full min-w-0 resize-y border-0 bg-transparent px-3.5 py-2.5 text-base text-[var(--studio-fg)] outline-none placeholder:text-[var(--studio-fg-subtle)] sm:px-4 sm:py-3";

/**
 * Prompt entry for Create. One box, every mode.
 *
 * Talking used to split into scene and spoken line here. The draft card in the
 * thread is where the line is read and changed now, so a second copy in a field
 * would be a rival source of truth, and fields appearing mid-flow was the part
 * nobody could follow. The says: marker never surfaces either way.
 */
export function PromptFields({
  mode,
  isExtending,
  prompt,
  onPromptChange,
  disabled,
  classNames,
  inputRef,
}: Props) {
  return (
    <div className={classNames?.shell ?? SHELL}>
      <textarea
        ref={inputRef}
        className={`${classNames?.field ?? FIELD} min-h-[3.75rem] sm:min-h-[5rem]`}
        value={mode === "avatar" ? avatarPromptForField(prompt) : prompt}
        onChange={(e) => onPromptChange(e.target.value)}
        placeholder={
          isExtending
            ? "What happens next in this scene…"
            : (PROMPT_PLACEHOLDER[mode] ?? "Describe the scene…")
        }
        aria-label="Prompt"
        disabled={disabled}
        rows={2}
      />
    </div>
  );
}
