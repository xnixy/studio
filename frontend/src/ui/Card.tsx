import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export function Card({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { children?: ReactNode }) {
  return (
    <div className={cn(tw.card, "overflow-hidden", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardHeader({
  children,
  className,
  header,
  description,
  ...rest
}: HTMLAttributes<HTMLDivElement> & {
  children?: ReactNode;
  header?: ReactNode;
  description?: ReactNode;
}) {
  return (
    <div className={cn("flex flex-col gap-1 px-4 py-3.5", className)} {...rest}>
      {header}
      {description}
      {children}
    </div>
  );
}

export function CardPreview({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { children?: ReactNode }) {
  return (
    <div className={cn("block w-full", className)} {...rest}>
      {children}
    </div>
  );
}
