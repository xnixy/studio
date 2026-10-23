import type {
  ChangeEvent,
  InputHTMLAttributes,
  ReactElement,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export function Field({
  label,
  hint,
  required,
  validationMessage,
  validationState,
  children,
  className,
}: {
  label?: string;
  hint?: string;
  required?: boolean;
  validationMessage?: string;
  validationState?: "error" | "warning" | "success" | "none";
  children: ReactElement | ReactNode;
  className?: string;
}) {
  const state = validationState ?? (validationMessage ? "error" : "none");
  const isError = state === "error";
  const isWarning = state === "warning";
  const isSuccess = state === "success";
  const controlTone = isError
    ? "[&_input]:border-[var(--color-danger)] [&_textarea]:border-[var(--color-danger)] [&_select]:border-[var(--color-danger)]"
    : isWarning
      ? "[&_input]:border-[var(--color-warning)] [&_textarea]:border-[var(--color-warning)] [&_select]:border-[var(--color-warning)]"
      : isSuccess
        ? "[&_input]:border-[var(--color-success)] [&_textarea]:border-[var(--color-success)] [&_select]:border-[var(--color-success)]"
        : "";
  const messageTone = isError
    ? tw.fieldError
    : isWarning
      ? tw.fieldWarning
      : isSuccess
        ? tw.fieldSuccess
        : tw.fieldHint;
  return (
    <div className={cn(tw.field, controlTone, className)}>
      {label ? (
        <label className={tw.fieldLabel}>
          {label}
          {required ? <span className="ml-0.5 text-[var(--color-danger)]">*</span> : null}
        </label>
      ) : null}
      {children}
      {hint && !validationMessage ? <p className={tw.fieldHint}>{hint}</p> : null}
      {validationMessage ? <p className={messageTone}>{validationMessage}</p> : null}
    </div>
  );
}

/** Optional second arg for legacy form handlers that expected `{ value }`. */
export type FieldChangeHandler<E extends HTMLElement> = (
  ev: ChangeEvent<E>,
  data: { value: string },
) => void;

export type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "size"> & {
  onChange?: FieldChangeHandler<HTMLInputElement>;
  contentAfter?: ReactNode;
  contentBefore?: ReactNode;
  size?: "small" | "medium" | "large" | number;
};

export type TextareaProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "onChange"> & {
  onChange?: FieldChangeHandler<HTMLTextAreaElement>;
};

export function Input({ className, onChange, contentAfter, contentBefore, size, ...props }: InputProps) {
  // Keep ≥16px text so iOS does not zoom on focus.
  const sizeCls =
    size === "small"
      ? "min-h-10 px-2.5 py-1.5 text-base"
      : size === "large"
        ? "min-h-11 px-3.5 py-2 text-base"
        : "";
  const nativeSize = typeof size === "number" ? size : undefined;
  const input = (
    <input
      className={cn(tw.control, tw.input, sizeCls, className)}
      size={nativeSize}
      onChange={(ev) => onChange?.(ev, { value: ev.target.value })}
      {...props}
    />
  );
  if (contentAfter == null && contentBefore == null) return input;
  return (
    <div className="flex w-full items-center gap-2">
      {contentBefore}
      {input}
      {contentAfter}
    </div>
  );
}

export function Textarea({ className, onChange, ...props }: TextareaProps) {
  return (
    <textarea
      className={cn(tw.control, tw.textarea, className)}
      onChange={(ev) => onChange?.(ev, { value: ev.target.value })}
      {...props}
    />
  );
}
