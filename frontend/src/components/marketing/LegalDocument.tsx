import type { ReactNode } from "react";
import { MessageBar } from "../../ui";
import { marketingPageCardClass } from "./MarketingPageLayout";

export function LegalDocument({
  title,
  lastUpdated,
  provisional = true,
  children,
}: {
  title: string;
  lastUpdated: string;
  provisional?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-3xl">
      <article className={marketingPageCardClass}>
        <header className="grid gap-2">
          <h1 className="m-0 text-[clamp(1.5rem,3vw,2rem)] font-bold tracking-tight text-[var(--studio-fg)]">{title}</h1>
          <p className="m-0 text-sm text-[var(--studio-fg-subtle)]">Last updated: {lastUpdated}</p>
        </header>
        {provisional ? (
          <div>
            {/* autoHideMs=0 pins it. An info MessageBar self-dismisses after six
                seconds, which quietly removed the disclaimer from a legal page. */}
            <MessageBar intent="info" autoHideMs={0}>
              <strong>Sample text.</strong> Replace this page with your own before you run a public service. A lawyer
              has not reviewed it. It is not legal advice.
              Questions: <a href="mailto:privacy@example.com">privacy@example.com</a>.
            </MessageBar>
          </div>
        ) : null}
        <div className="grid gap-4 text-[var(--studio-fg-muted)] [&_a]:text-[var(--studio-brand)] [&_h2]:mt-2 [&_h2]:text-lg [&_h2]:font-bold [&_h2]:text-[var(--studio-fg)] [&_p]:m-0 [&_p]:leading-relaxed [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5">
          {children}
        </div>
      </article>
    </div>
  );
}

export function LegalSection({ id, title, children }: { id?: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="grid gap-2">
      <h2 className="m-0 text-lg font-bold text-[var(--studio-fg)]">{title}</h2>
      <div className="grid gap-2 text-sm leading-relaxed text-[var(--studio-fg-muted)]">{children}</div>
    </section>
  );
}
