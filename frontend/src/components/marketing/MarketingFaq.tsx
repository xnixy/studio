import { Body1 } from "../../ui/Text";

export interface FaqItem {
  question: string;
  answer: string;
}

export function MarketingFaq({ items }: { items: FaqItem[] }) {
  return (
    <div className="grid gap-2">
      {items.map((item, index) => (
        <details
          key={item.question}
          className="rounded-2xl border border-[var(--studio-border)] bg-[var(--studio-glass,var(--studio-panel))] shadow-[var(--studio-card-shadow)] backdrop-blur-md open:border-[var(--studio-border)] open:bg-[var(--studio-fill-soft)]"
          open={index === 0}
        >
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3.5 text-left text-[0.95rem] font-semibold text-[var(--studio-fg)] [&::-webkit-details-marker]:hidden">
            {item.question}
          </summary>
          <div className="px-4 pb-4">
            <Body1 className="text-[var(--studio-fg-muted)]">{item.answer}</Body1>
          </div>
        </details>
      ))}
    </div>
  );
}
