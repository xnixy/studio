import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export type BadgeProps = {
  children?: ReactNode;
  appearance?: "filled" | "ghost" | "outline" | "tint";
  color?: "brand" | "danger" | "important" | "informative" | "severe" | "subtle" | "success" | "warning";
  size?: "tiny" | "extra-small" | "small" | "medium" | "large" | "extra-large";
  shape?: "circular" | "rounded" | "square";
  icon?: ReactNode;
  className?: string;
  title?: string;
};

function colorClass(color: BadgeProps["color"]) {
  if (color === "success") return tw.badgeSuccess;
  if (color === "danger" || color === "severe") return tw.badgeDanger;
  if (color === "warning") return tw.badgeWarning;
  if (color === "subtle" || color === "informative") return tw.badgeSubtle;
  return tw.badgeBrand;
}

export function Badge({ children, color = "brand", icon, className, title }: BadgeProps) {
  return (
    <span className={cn(tw.badge, colorClass(color), className)} title={title}>
      {icon}
      {children}
    </span>
  );
}
