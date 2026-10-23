import type { InputHTMLAttributes, ReactNode } from "react";
import { cn } from "../lib/cn";

export type CheckboxProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "type" | "onChange" | "checked"
> & {
  label?: ReactNode;
  checked?: boolean | "mixed";
  defaultChecked?: boolean;
  onChange?: (ev: React.ChangeEvent<HTMLInputElement>, data: { checked: boolean }) => void;
  indicator?: ReactNode;
};

export function Checkbox({
  label,
  className,
  checked,
  defaultChecked,
  disabled,
  onChange,
  id,
  ...rest
}: CheckboxProps) {
  const nativeChecked = checked === "mixed" ? false : checked;
  return (
    <label
      className={cn(
        "inline-flex cursor-pointer select-none items-start gap-2 text-sm text-[var(--studio-fg)]",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
      data-disabled={disabled ? "true" : undefined}
    >
      <input
        type="checkbox"
        id={id}
        checked={nativeChecked}
        defaultChecked={defaultChecked}
        disabled={disabled}
        className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--studio-brand)]"
        ref={(el) => {
          if (el) el.indeterminate = checked === "mixed";
        }}
        onChange={(ev) => onChange?.(ev, { checked: ev.target.checked })}
        {...rest}
      />
      {label != null ? <span>{label}</span> : null}
    </label>
  );
}
