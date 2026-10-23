import { cloneElement, isValidElement, useId, useState, type ReactElement, type ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export function Tooltip({
  content,
  children,
  positioning = "above",
}: {
  content: ReactNode;
  relationship?: string;
  children: ReactElement;
  positioning?: "above" | "below" | "before" | "after" | string;
  withArrow?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const pos =
    positioning === "below"
      ? "top-full left-1/2 mt-1.5 -translate-x-1/2"
      : positioning === "before"
        ? "right-full top-1/2 mr-1.5 -translate-y-1/2"
        : positioning === "after"
          ? "left-full top-1/2 ml-1.5 -translate-y-1/2"
          : "bottom-full left-1/2 mb-1.5 -translate-x-1/2";

  const trigger = isValidElement(children)
    ? cloneElement(children as ReactElement<Record<string, unknown>>, {
        "aria-describedby": open ? id : undefined,
      })
    : children;

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {trigger}
      {open ? (
        <span role="tooltip" id={id} className={cn(tw.tooltip, "absolute", pos, "pointer-events-none whitespace-normal")}>
          {content}
        </span>
      ) : null}
    </span>
  );
}
