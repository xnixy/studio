import { Link } from "react-router-dom";
import { cn } from "../../lib/cn";

import type { DocBlock } from "../../docs/types";
import { useDocsStyles } from "../../ui/docsStyles";

export function DocProse({ body }: { body: DocBlock[] }) {
  const styles = useDocsStyles();
  return (
    <div className={styles.prose}>
      {body.map((block, index) => {
        switch (block.type) {
          case "p":
            return (
              <p key={index} className={styles.p}>
                {block.text}
              </p>
            );
          case "h2":
            return (
              <h2 key={index} id={block.id} className={styles.h2}>
                {block.text}
              </h2>
            );
          case "h3":
            return (
              <h3 key={index} className={styles.h3}>
                {block.text}
              </h3>
            );
          case "ul":
            return (
              <ul key={index} className={styles.proseList}>
                {block.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            );
          case "ol":
            return (
              <ol key={index} className={styles.proseList}>
                {block.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            );
          case "steps":
            return (
              <ol key={index} className={styles.steps}>
                {block.items.map((item, stepIndex) => (
                  <li key={item} className={styles.step}>
                    <span className={styles.stepNum}>{stepIndex + 1}</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ol>
            );
          case "callout":
            return (
              <aside
                key={index}
                className={cn(
                  styles.callout,
                  block.tone === "tip" && styles.calloutTip,
                  block.tone === "note" && styles.calloutNote,
                  block.tone === "warning" && styles.calloutWarning,
                )}
                role="note"
              >
                {block.title ? <strong>{block.title}</strong> : null}
                <p className={styles.p}>{block.text}</p>
              </aside>
            );
          case "links":
            return (
              <ul key={index} className={styles.linkList}>
                {block.items.map((item) => (
                  <li key={item.to}>
                    <Link to={item.to}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
