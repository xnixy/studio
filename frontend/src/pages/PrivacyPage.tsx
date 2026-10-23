import { Link } from "react-router-dom";
import { LegalDocument, LegalSection } from "../components/marketing/LegalDocument";
import { usePageMeta } from "../components/marketing/usePageMeta";

const LAST_UPDATED = "August 26, 2026";

export function PrivacyPage() {
  usePageMeta(
    "Privacy Policy · Studio",
    "How Studio handles your account, workspace, and contact data, which providers process it, and how to request deletion.",
  );

  return (
    <LegalDocument title="Privacy Policy" lastUpdated={LAST_UPDATED} provisional>
        <LegalSection title="1. Introduction">
          <p>
            This Privacy Policy describes how <strong>Studio</strong> (“Studio,” “we,” “us”) handles personal
            information when you use our websites, applications, and related services (the “Service”). The operator of
            this Service is the controller of the personal information described here.
          </p>
          <p>
            Contact for privacy questions and data requests:{" "}
            <a href="mailto:privacy@example.com">privacy@example.com</a> or the{" "}
            <Link to="/contact">Contact form</Link>.
          </p>
        </LegalSection>

        <LegalSection title="2. Information we collect">
          <p>Depending on how you use Studio, we may process:</p>
          <ul>
            <li>
              <strong>Account data</strong>, email, name/profile fields, role, password hashes (not plain passwords).
            </li>
            <li>
              <strong>Session & security data</strong>, authentication tokens/session metadata, IP-based rate-limit
              signals, approximate request logs needed to operate and secure the Service.
            </li>
            <li>
              <strong>Contact submissions</strong>, name, email, topic, and message content you send via Contact.
            </li>
            <li>
              <strong>Workspace content</strong>, prompts, scripts, face and reference media, generated clips and stills,
              and related project data you enter or generate.
            </li>
            <li>
              <strong>Usage & billing metadata</strong>, plan, seats, usage counters, and Stripe-related identifiers when
              billing is enabled.
            </li>
          </ul>
        </LegalSection>

        <LegalSection title="3. How we use information">
          <ul>
            <li>Provide, maintain, and improve the Service (including AI-assisted create features).</li>
            <li>Authenticate users, enforce seats and plan limits, and prevent abuse.</li>
            <li>Respond to support and contact requests.</li>
            <li>Process payments and invoices when billing is active.</li>
            <li>Comply with law and protect the security of Studio, our users, and the public.</li>
          </ul>
        </LegalSection>

        <LegalSection title="4. AI and model processing">
          <p>
            Some features send prompts, scripts, face or reference images, and other media to third-party AI and media
            providers (for example image or video generation, or voice synthesis) to produce outputs for your
            workspace. Treat generated outputs as <strong>drafts</strong> until a human reviews them.
          </p>
          <p>
            The providers we send generation requests to today are xAI (Grok chat and stills), Google (Nano Banana
            stills), BytePlus (Seedance clips), and ElevenLabs (speech). Which one runs a given job depends on
            what you are making. The draft card names the spend before you generate.
          </p>
          <p>
            Each provider processes your prompt and any media that job needs under its own terms, and regions may
            change as the product evolves. Do not submit sensitive personal data in prompts unless you have a lawful
            basis and are comfortable with that processing.
          </p>
        </LegalSection>

        <LegalSection title="5. Legal bases">
          <p>
            Where data-protection laws such as the UK or EU GDPR apply, we rely on these bases: <strong>contract</strong>
            for running your account, workspaces, and generations; <strong>legitimate interests</strong> for securing
            the Service, preventing abuse, and improving it; <strong>consent</strong> where we ask for it, such as
            optional email; and <strong>legal obligation</strong> for tax, accounting, and lawful requests.
          </p>
        </LegalSection>

        <LegalSection title="6. Sharing and processors">
          <p>We share personal information only as needed to run Studio. Our processors today are:</p>
          <ul>
            <li><strong>Hosting and database</strong> providers, for the application and its data.</li>
            <li><strong>Storage and CDN</strong>, Cloudflare R2, for your uploads and generated media.</li>
            <li><strong>Bot protection</strong>, Cloudflare Turnstile, on public forms.</li>
            <li><strong>AI and media</strong>, xAI, Google, BytePlus, and ElevenLabs, as described above.</li>
            <li><strong>Email</strong>, SendGrid, for verification, password resets, and notifications.</li>
            <li><strong>Payments</strong>, Stripe on the web and Apple for in-app purchases on iOS.</li>
            <li><strong>Error reporting</strong>, Sentry, for crash and exception diagnostics.</li>
            <li>Professional advisors or authorities when required by law or to protect rights and safety.</li>
          </ul>
          <p>
            We do not sell personal information, and we do not share it for cross-context behavioral advertising.
          </p>
        </LegalSection>

        <LegalSection title="7. International transfers">
          <p>
            We are based in the United States and our providers may process data there or elsewhere, so using Studio
            from outside the US involves an international transfer. Where a transfer mechanism is required, we rely on
            the European Commission's Standard Contractual Clauses, or the UK Addendum, as incorporated into our
            agreements with those providers.
          </p>
        </LegalSection>

        <LegalSection title="8. Retention">
          <p>
            We keep account and workspace data while your account is active. When you delete your account we remove
            your workspace content, including uploaded faces and generated media, within 30 days, apart from anything
            we must keep for tax, accounting, or legal reasons. Request deletion at{" "}
            <a href="mailto:privacy@example.com">privacy@example.com</a>.
          </p>
        </LegalSection>

        <LegalSection title="9. Security">
          <p>
            We use industry-standard controls appropriate to a SaaS product: transport encryption (HTTPS), access-controlled
            APIs, hashed passwords, rate limiting on public endpoints, and encryption of integration secrets at rest. No
            method of transmission or storage is 100% secure; please use strong unique passwords.
          </p>
        </LegalSection>

        <LegalSection title="10. Your rights">
          <p>
            Depending on your location, you may have rights to access, correct, delete, or export personal information, or
            to object to or restrict certain processing. To exercise rights, email{" "}
            <a href="mailto:privacy@example.com">privacy@example.com</a> or use <Link to="/contact">Contact</Link>. We may need
            to verify your identity first. We aim to respond within 30 days and will tell you if we need longer. If you
            disagree with our answer you can ask us to review it, and you can complain to your local data-protection
            authority.
          </p>
        </LegalSection>

        <LegalSection title="11. Cookies and local storage">
          <p>
            We use essential storage to operate the Service, including authentication/session mechanisms and theme
            preference (e.g. <code>studio.theme</code> in local storage). We do not run a third-party advertising pixel on
            the marketing site as of this version. If analytics are added later, this section will be updated.
          </p>
        </LegalSection>

        <LegalSection title="12. Children">
          <p>
            Studio is directed at business users and is not intended for anyone under 18. We do not knowingly collect
            personal information from children. If you believe a child has given us personal information, email{" "}
            <a href="mailto:privacy@example.com">privacy@example.com</a> and we will delete it.
          </p>
        </LegalSection>

        <LegalSection title="13. Changes">
          <p>
            We may update this policy as the product or legal requirements change. Material updates will be reflected by
            revising the “Last updated” date and, where appropriate, additional notice in-product or by email.
          </p>
        </LegalSection>

        <LegalSection title="14. Contact">
          <p>
            Privacy: <a href="mailto:privacy@example.com">privacy@example.com</a>
            <br />
            General: <a href="mailto:contact@example.com">contact@example.com</a> ·{" "}
            <Link to="/contact">Contact form</Link>
          </p>
        </LegalSection>
    </LegalDocument>
  );
}
