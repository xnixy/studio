import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export type TabItem = {
  value: string;
  label: ReactNode;
  icon?: ReactNode;
  disabled?: boolean;
};

/** Lightweight tablist (no Radix). */
export function TabList({
  className,
  children,
  "aria-label": ariaLabel,
}: {
  className?: string;
  children?: ReactNode;
  "aria-label"?: string;
}) {
  return (
    <div role="tablist" className={cn(tw.tabList, className)} aria-label={ariaLabel}>
      {children}
    </div>
  );
}

export function Tab({
  value,
  selected,
  disabled,
  onSelect,
  children,
  className,
}: {
  value: string;
  selected?: boolean;
  disabled?: boolean;
  onSelect?: (value: string) => void;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={selected}
      data-active={selected ? "true" : "false"}
      disabled={disabled}
      className={cn(tw.tab, className)}
      onClick={() => onSelect?.(value)}
    >
      {children}
    </button>
  );
}

export function Tabs({
  value,
  onChange,
  items,
  className,
  appearance: _appearance = "subtle",
  size: _size = "medium",
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  items: TabItem[];
  className?: string;
  appearance?: "subtle" | "transparent";
  size?: "small" | "medium" | "large";
  "aria-label"?: string;
}) {
  return (
    <TabList className={className} aria-label={ariaLabel}>
      {items.map((item) => (
        <Tab
          key={item.value}
          value={item.value}
          selected={item.value === value}
          disabled={item.disabled}
          onSelect={onChange}
        >
          {item.icon}
          {item.label}
        </Tab>
      ))}
    </TabList>
  );
}
