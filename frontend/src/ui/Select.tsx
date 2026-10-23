import { forwardRef, type ChangeEvent, type ReactNode, type SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

type SelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "size" | "onChange"> & {
  size?: "md" | "sm";
  fullWidth?: boolean;
  onChange?: (event: ChangeEvent<HTMLSelectElement>) => void;
  children?: ReactNode;
};

/**
 * Native select with stable closed-state paint.
 * Chevron is an overlay icon (not background-image) so Windows does not wipe
 * text color / fill after a choice is picked.
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  {
    value,
    defaultValue,
    onChange,
    disabled,
    children,
    className,
    id,
    name,
    size = "md",
    fullWidth = true,
    "aria-label": ariaLabel,
    "aria-labelledby": ariaLabelledBy,
    title,
    required,
    multiple,
    autoFocus,
    form,
  },
  ref,
) {
  return (
    <div
      className={cn(
        "relative min-w-0",
        fullWidth ? "w-full" : "inline-block w-auto max-w-[18rem] min-w-[7.5rem]",
        disabled && "opacity-45",
      )}
    >
      <select
        ref={ref}
        id={id}
        name={name}
        value={value}
        defaultValue={defaultValue as string | undefined}
        disabled={disabled}
        required={required}
        multiple={multiple}
        autoFocus={autoFocus}
        form={form}
        title={title}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        className={cn(
          tw.control,
          tw.select,
          size === "sm" && tw.selectSm,
          // Wrapper owns width; select always fills it.
          "w-full pr-9",
          !fullWidth && "min-w-[7.5rem]",
          className,
        )}
        onChange={(event) => onChange?.(event)}
      >
        {children}
      </select>
      {!multiple ? (
        <ChevronDown
          aria-hidden
          size={size === "sm" ? 14 : 16}
          strokeWidth={2}
          className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--studio-fg-muted)]"
        />
      ) : null}
    </div>
  );
});
