import type { CSSProperties, ElementType, HTMLAttributes, ReactNode } from "react";
import { cn } from "../lib/cn";
import { tw } from "./tw";

type TextProps = HTMLAttributes<HTMLElement> & {
  children?: ReactNode;
  as?: ElementType;
  className?: string;
  weight?: "regular" | "medium" | "semibold" | "bold" | string;
  size?: number | string;
  style?: CSSProperties;
};

function weightClass(weight?: string) {
  if (weight === "bold") return "font-bold";
  if (weight === "semibold") return "font-semibold";
  if (weight === "medium") return "font-medium";
  return undefined;
}

export function Body1({ as: Tag = "p", className, children, weight, size: _size, style, ...rest }: TextProps) {
  return (
    <Tag className={cn(tw.body, weightClass(weight), className)} style={style} {...rest}>
      {children}
    </Tag>
  );
}

export function Caption1({ as: Tag = "p", className, children, weight, size: _size, style, ...rest }: TextProps) {
  return (
    <Tag className={cn(tw.caption, weightClass(weight), className)} style={style} {...rest}>
      {children}
    </Tag>
  );
}

export function Title1({ as: Tag = "h1", className, children, weight, size: _size, style, ...rest }: TextProps) {
  return (
    <Tag className={cn(tw.title1, weightClass(weight), className)} style={style} {...rest}>
      {children}
    </Tag>
  );
}

export function Title2({ as: Tag = "h2", className, children, weight, size: _size, style, ...rest }: TextProps) {
  return (
    <Tag className={cn(tw.title2, weightClass(weight), className)} style={style} {...rest}>
      {children}
    </Tag>
  );
}

export function Subtitle2({ as: Tag = "h3", className, children, weight, size: _size, style, ...rest }: TextProps) {
  return (
    <Tag className={cn(tw.subtitle2, weightClass(weight), className)} style={style} {...rest}>
      {children}
    </Tag>
  );
}

export function Text({ as: Tag = "span", className, children, weight, size: _size, style, ...rest }: TextProps) {
  return (
    <Tag className={cn(weightClass(weight), className)} style={style} {...rest}>
      {children}
    </Tag>
  );
}
