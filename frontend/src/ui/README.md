# Studio UI

## Tailwind only

| Source | Role |
|--------|------|
| `src/styles/tailwind.css` | Single CSS entry |
| `ui/tw.ts` | Kit + shell recipes |
| `ui/*Styles.ts` | Dashboard / marketing / docs / studio maps |
| `ui/theme/*` | Brand + materials → CSS vars |

```ts
import { Button, Field, Select, Tabs } from "../ui";
import { tw } from "../ui/tw";
import { cn } from "../lib/cn";
```

No Radix. No `productTw` / plain CSS sheets. New UI = Tailwind utilities or `tw.*`.
