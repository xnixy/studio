import {
  forwardRef,
  type CSSProperties,
  type MouseEventHandler,
  type ReactNode,
} from "react";
import { Link, type To } from "react-router-dom";
import { cn } from "../lib/cn";
import { tw } from "./tw";

export type ButtonVariant = "primary" | "secondary" | "subtle" | "outline" | "transparent";
export type ButtonSize = "small" | "medium" | "large";

function sizeClass(size: ButtonSize) {
  if (size === "small") return tw.btnSm;
  if (size === "large") return tw.btnLg;
  return tw.btnMd;
}

function variantClass(variant: ButtonVariant) {
  switch (variant) {
    case "primary":
      return tw.btnPrimary;
    case "secondary":
      return tw.btnSecondary;
    case "outline":
      return tw.btnOutline;
    case "transparent":
    case "subtle":
    default:
      return tw.btnSubtle;
  }
}

export type ButtonProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  iconPosition?: "before" | "after";
  disabled?: boolean;
  className?: string;
  children?: ReactNode;
  title?: string;
  type?: "button" | "submit" | "reset";
  onClick?: MouseEventHandler<HTMLButtonElement>;
  form?: string;
  name?: string;
  value?: string;
  "aria-label"?: string;
  "aria-expanded"?: boolean | "true" | "false";
  "aria-haspopup"?: boolean | "dialog" | "menu" | "true" | "false" | "listbox" | "tree" | "grid";
  "aria-controls"?: string;
  id?: string;
  style?: CSSProperties;
  asChild?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "medium",
    className,
    children,
    type = "button",
    onClick,
    icon,
    iconPosition = "before",
    asChild: _asChild,
    ...rest
  },
  ref,
) {
  const classes = cn(tw.btn, sizeClass(size), variantClass(variant), className);
  const content =
    icon != null ? (
      <>
        {iconPosition !== "after" ? icon : null}
        {children}
        {iconPosition === "after" ? icon : null}
      </>
    ) : (
      children
    );

  return (
    <button ref={ref} type={type} className={classes} onClick={onClick} {...rest}>
      {content}
    </button>
  );
});

export type LinkButtonProps = {
  to: To;
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  iconPosition?: "before" | "after";
  disabled?: boolean;
  className?: string;
  children?: ReactNode;
  title?: string;
  replace?: boolean;
  state?: unknown;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
  "aria-label"?: string;
};

export function LinkButton({
  to,
  variant = "primary",
  size = "medium",
  className,
  children,
  icon,
  iconPosition = "before",
  disabled,
  replace,
  state,
  onClick,
  title,
  "aria-label": ariaLabel,
}: LinkButtonProps) {
  const classes = cn(tw.btn, sizeClass(size), variantClass(variant), className);
  const content =
    icon != null ? (
      <>
        {iconPosition !== "after" ? icon : null}
        {children}
        {iconPosition === "after" ? icon : null}
      </>
    ) : (
      children
    );

  if (disabled) {
    return (
      <button type="button" className={classes} disabled title={title} aria-label={ariaLabel}>
        {content}
      </button>
    );
  }

  return (
    <Link
      to={to}
      replace={replace}
      state={state}
      onClick={onClick}
      className={classes}
      title={title}
      aria-label={ariaLabel}
    >
      {content}
    </Link>
  );
}

export const IconButton = forwardRef<HTMLButtonElement, ButtonProps>(function IconButton(
  { variant = "subtle", size = "medium", children, className, ...rest },
  ref,
) {
  return (
    <Button ref={ref} variant={variant} size={size} className={cn(tw.btnIcon, className)} {...rest}>
      {children}
    </Button>
  );
});
