import { useEffect, useState, type ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export type MessageBarIntent = "error" | "success" | "warning" | "info";

export function MessageBar({
  intent = "info",
  children,
  className,
  autoHideMs,
  onDismiss,
}: {
  intent?: MessageBarIntent | string;
  children: ReactNode;
  className?: string;
  autoHideMs?: number;
  onDismiss?: () => void;
}) {
  const mapped: MessageBarIntent =
    intent === "error" || intent === "success" || intent === "warning" || intent === "info"
      ? intent
      : "info";

  const defaultHide = mapped === "success" ? 4500 : mapped === "info" ? 6000 : undefined;
  const hideAfter = autoHideMs ?? defaultHide;
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);
    if (!hideAfter || mapped === "error" || mapped === "warning") return;
    const t = window.setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, hideAfter);
    return () => window.clearTimeout(t);
  }, [children, hideAfter, mapped, onDismiss]);

  if (!visible) return null;

  const tone =
    mapped === "error"
      ? tw.messageError
      : mapped === "success"
        ? tw.messageSuccess
        : mapped === "warning"
          ? tw.messageWarning
          : tw.messageInfo;

  return (
    <div role="status" className={cn(tw.messageBar, tone, className)}>
      <div>{children}</div>
    </div>
  );
}

export function bannerIntent(kind?: string): MessageBarIntent {
  if (kind === "error") return "error";
  if (kind === "success") return "success";
  if (kind === "warning") return "warning";
  return "info";
}
