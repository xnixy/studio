import { Badge } from "../../ui";

export function EarlyAccessBadge({ className }: { className?: string }) {
  return (
    <Badge appearance="tint" color="brand" className={className}>
      Early access
    </Badge>
  );
}
