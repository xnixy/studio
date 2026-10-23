import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { cn } from "../lib/cn";
import { Body1 } from "../ui/Text";
import { CtaRow } from "../components/marketing/CtaRow";
import { MarketingPageLayout, MarketingPanel } from "../components/marketing/MarketingPageLayout";
import { MarketingSection } from "../components/marketing/MarketingSection";
import { usePageMeta } from "../components/marketing/usePageMeta";
import { useMarketingStyles } from "../ui/marketingStyles";

const flowSteps = [
  {
    title: "One prompt",
    body: "Clip or Still. Describe the clip in one box. Clothes, place, and what they say can all live in that line.",
  },
  {
    title: "Confirm the kind",
    body: "We talk it through and confirm Talking or Scene before you spend credits.",
  },
  {
    title: "Face, voice, generate",
    body: "Face and Voice sit on the bar. Seedance Fast is the default. Cost in credits shows before you run.",
  },
  {
    title: "Download",
    body: "Export the file. Post where you already publish. We do not post for you.",
  },
];

const faqItems = [
  {
    question: "How do I get started?",
    answer:
      "Create a free account on the site or in the app. Then open Create, write a prompt, and we confirm Talking or Scene before you spend credits.",
  },
  {
    question: "What can I make?",
    answer:
      "Talking, Scene, and stills. Vertical or square. Write one prompt. We confirm Talking or Scene. Clips run on Seedance. Stills stay on Grok and Nano Banana. Clone your voice once for Talking and Face lines in Scene.",
  },
  {
    question: "How do credits work?",
    answer:
      "Your plan comes with separate credits for clips, stills, and photo. Talking and Scene share the Clip pool. A fast still is 1 credit. A Talking Fast clip at about 5s is 8 clip credits. Your clone on Talking adds a few voice seconds. You always see the number before you spend it.",
  },
  {
    question: "Does Studio post for me?",
    answer:
      "No. You generate and download the file, then post it wherever you already publish. Your accounts stay yours.",
  },
  {
    question: "Can I use my own face?",
    answer:
      "Yes, when you have rights to use it. Generate or upload once in Faces, reuse free. Clone your voice under Voices. Review every cut before it goes public.",
  },
  {
    question: "How much does it cost?",
    answer:
      "Free, Starter, Creator, and Studio. See Pricing for the numbers. Credit packs top up a busy month without changing your plan.",
  },
];

export function AboutPage() {
  const styles = useMarketingStyles();
  const [openItems, setOpenItems] = useState<string[]>(["0"]);

  usePageMeta(
    "About Studio · finished clips, not another dashboard",
    "Studio is for creators who need clips they can post today. Talking, Scene, and stills on Seedance and Grok. Clone your voice. You download the file and publish it yourself.",
  );

  return (
    <MarketingPageLayout
      eyebrow="About"
      title="Finished clips, not another dashboard"
      lede="Studio is for creators and freelancers who need files they can post today: Talking, Scene, or a still. Pick a face, write the line, download it. Clone your voice once if you want it to sound like you."
      actions={
        <CtaRow
          primaryTo="/register"
          primaryLabel={
            <>
              Create account
              <ArrowRight size={16} />
            </>
          }
          secondaryTo="/login"
          secondaryLabel="Sign in"
        />
      }
    >
      <MarketingSection label="Who it is for" title="Built for people who ship clips">
        <Body1>
          <strong className="font-semibold text-[var(--studio-fg)]">Good fit:</strong> freelancers, solo creators, and
          small teams who make Reels, TikToks, Shorts, and feed stills. You want a clear prompt, a model picker, and a
          file you can download today.
        </Body1>
        <Body1>
          <strong className="font-semibold text-[var(--studio-fg)]">Not a fit:</strong> anyone who wants a scheduler, a
          team workspace product, or a tool that publishes on their behalf. You make the file here and post it
          yourself.
        </Body1>
      </MarketingSection>

      <MarketingSection label="Why we built it" title="One place to make the clip">
        <Body1>
          Short-form is the job. The tools were either toys or heavyweight suites, and neither one just hands you a
          file. We wanted the middle: write a line, pick a model, see the cost, download the clip.
        </Body1>
        <Body1>
          Create is the center of it. One box, then a draft card that confirms the kind. Faces holds the faces you
          reuse, Voices holds your clone, Library holds everything you have made, and your plan shows the credits you
          have left. That is the whole loop.
        </Body1>
      </MarketingSection>

      <MarketingSection label="How it works" title="From example to file">
        <div className={styles.grid2}>
          {flowSteps.map((step, i) => (
            <MarketingPanel key={step.title}>
              <p className="m-0 text-[0.72rem] font-bold uppercase tracking-wide text-[var(--studio-brand)]">
                0{i + 1}
              </p>
              <h3 className={styles.featureTitle}>{step.title}</h3>
              <p className={styles.featureBody}>{step.body}</p>
            </MarketingPanel>
          ))}
        </div>
      </MarketingSection>

      <MarketingSection label="What you can do" title="Make · Pick · Export">
        <dl className={styles.propList}>
          <div className={styles.propItem}>
            <dt className={styles.propTerm}>Make</dt>
            <dd className={styles.propDesc}>
              Talking with a saved face, Scene, or a still. Vertical or square. One
              prompt at a time. We confirm the kind before you spend.
            </dd>
          </div>
          <div className={styles.propItem}>
            <dt className={styles.propTerm}>Pick</dt>
            <dd className={styles.propDesc}>
              Seedance Fast is the default. 2.5 costs more credits. Face and Voice sit on the bar.
              Length follows the line. Cost sits on the draft card.
            </dd>
          </div>
          <div className={styles.propItem}>
            <dt className={styles.propTerm}>Export</dt>
            <dd className={styles.propDesc}>
              Download the file. Post in the apps you already use. We never publish anything for you.
            </dd>
          </div>
        </dl>
      </MarketingSection>

      <MarketingSection label="Credits" title="Better models cost more">
        <Body1>
          Plans come with separate credits for clips, stills, and photo. Fast models stretch the month.
          Seedance 2.5 and Talking with your clone cost more per run. Credit packs cover a busy month without
          changing your plan. Full numbers live on{" "}
          <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/pricing">
            pricing
          </Link>
          .
        </Body1>
      </MarketingSection>

      <MarketingSection label="FAQ" title="Straight answers">
        <p className="m-0 mb-3 text-sm text-[var(--studio-fg-muted)]">
          For walkthroughs, open the{" "}
          <Link className="font-semibold text-[var(--studio-brand)] no-underline hover:underline" to="/docs">
            docs
          </Link>
          .
        </p>
        <div className={styles.faq}>
          {faqItems.map((item, index) => {
            const value = String(index);
            const isOpen = openItems.includes(value);
            return (
              <details
                key={item.question}
                className={cn(styles.faqItem, isOpen && styles.faqItemOpen)}
                open={isOpen}
                onToggle={(ev) => {
                  const nextOpen = (ev.currentTarget as HTMLDetailsElement).open;
                  setOpenItems((prev) => {
                    const set = new Set(prev);
                    if (nextOpen) set.add(value);
                    else set.delete(value);
                    return Array.from(set);
                  });
                }}
              >
                <summary className={cn(styles.faqHeader, styles.faqHeaderButton)}>
                  <span className={styles.faqQuestion}>{item.question}</span>
                </summary>
                <div className={styles.faqPanel}>
                  <p className={styles.faqAnswer}>{item.answer}</p>
                </div>
              </details>
            );
          })}
        </div>
      </MarketingSection>

      <MarketingSection label="Get started" title="Create an account and make a clip">
        <Body1>
          Sign up on the site or in the iOS app. Your workspace opens with Create, Faces, Voices, Library, and Billing.
        </Body1>
      </MarketingSection>
    </MarketingPageLayout>
  );
}
