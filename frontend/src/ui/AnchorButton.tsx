import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import type { ButtonSize, ButtonVariant } from "./Button";
import { tw } from "./tw";

function sizeClass(size: ButtonSize) {
  if (size === "small") return tw.btnSm;
  if (size === "large") return tw.btnLg;
  return tw.btnMd;
}

function variantClass(variant: ButtonVariant) {
  if (variant === "primary") return tw.btnPrimary;
  if (variant === "secondary") return tw.btnSecondary;
  if (variant === "outline") return tw.btnOutline;
  return tw.btnSubtle;
}

export function AnchorButton({
  href,
  variant = "primary",
  size = "medium",
  className,
  children,
  download,
  target,
  rel,
  title,
  "aria-label": ariaLabel,
}: {
  href: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children?: ReactNode;
  download?: string | boolean;
  target?: string;
  rel?: string;
  title?: string;
  "aria-label"?: string;
}) {
  return (
    <a
      href={href}
      className={cn(tw.btn, sizeClass(size), variantClass(variant), className)}
      download={download}
      target={target}
      rel={rel}
      title={title}
      aria-label={ariaLabel}
    >
      {children}
    </a>
  );
}
