import { Link } from "react-router-dom";
import { LegalDocument, LegalSection } from "../components/marketing/LegalDocument";
import { usePageMeta } from "../components/marketing/usePageMeta";

const LAST_UPDATED = "August 26, 2026";

export function TermsPage() {
  usePageMeta(
    "Terms of Service · Studio",
    "Terms for using Studio, operated by Studio. Accounts, acceptable use, plans and credits, and liability.",
  );

  return (
    <LegalDocument title="Terms of Service" lastUpdated={LAST_UPDATED} provisional>
        <LegalSection title="1. Agreement">
          <p>
            These Terms of Service (“Terms”) govern access to and use of Studio websites, applications, and related services
            (the “Service”). “Studio,” “we,” and “us” refer to the operator of this Service.
          </p>
          <p>
            By creating an account or using the Service, you agree to these Terms. If you use Studio
            on behalf of an organization, you represent that you have authority to bind that organization.
          </p>
        </LegalSection>

        <LegalSection title="2. Eligibility and accounts">
          <p>
            You must provide accurate account information, keep credentials
            confidential, and promptly notify us of unauthorized use. You are responsible for activity under your account
            and workspaces you administer.
          </p>
        </LegalSection>

        <LegalSection title="3. Early access and product changes">
          <p>
            Studio may be offered as early access or beta. Features, limits, and availability can change. We may modify or
            discontinue features with or without notice as we improve the product, subject to any separate written
            commitments we make to paying customers.
          </p>
        </LegalSection>

        <LegalSection title="4. License">
          <p>
            Subject to these Terms, we grant you a limited, non-exclusive, non-transferable, non-sublicensable,
            revocable license to access and use the Service for your own business purposes, including creating,
            publishing, and monetizing the clips and stills you generate. You may not resell or white-label the
            Service itself, or use it to build a competing product. We reserve all rights not expressly granted.
          </p>
        </LegalSection>

        <LegalSection title="5. Acceptable use">
          <p>You agree not to:</p>
          <ul>
            <li>Use the Service for illegal, fraudulent, or harmful advertising or content.</li>
            <li>Attempt to bypass rate limits, plan limits, or security controls.</li>
            <li>Reverse engineer, scrape, or disrupt the Service except as allowed by law.</li>
            <li>Upload malware or content you do not have rights to use.</li>
            <li>Misrepresent AI-generated content as human-reviewed where disclosure is required by law or platform policy.</li>
          </ul>
        </LegalSection>

        <LegalSection title="6. Customer content">
          <p>
            You retain rights in what you submit (“Customer Content”), including prompts, scripts, faces, and reference
            media. You grant us a worldwide, royalty-free license to host, process, transmit, and display Customer
            Content solely to operate the Service for you. We do not use your Customer Content or your generated
            outputs to train our own models, and we do not publish your work as a public example without asking you
            first.
          </p>
          <p>
            As between you and us, the clips and stills you generate are yours to use. You represent that you have the
            rights to everything you submit, including permission from any person whose face or voice you upload, and
            that your use does not violate law or third-party rights.
          </p>
        </LegalSection>

        <LegalSection title="7. AI-generated content">
          <p>
            Outputs may be incomplete, inaccurate, or unsuitable for publication. You are solely responsible for
            reviewing every clip, still, and claim before you post it anywhere public. We do not guarantee the
            performance, compliance, or fitness of any output for a particular use.
          </p>
        </LegalSection>

        <LegalSection title="8. Third-party services">
          <p>
            AI and media providers are subject to their own terms. Your use of those services is your responsibility.
            Availability of third-party APIs may affect related Studio features.
          </p>
        </LegalSection>

        <LegalSection title="9. Plans and billing">
          <p>
            Generation is metered in credits, and plans carry limits on credits, seats, and storage. Paid plans are
            billed for the plan you select (Starter, Creator, Studio) plus any credit packs or add-ons. Prices are
            shown in-product before you spend a credit, and may change with notice for future terms.
          </p>
          <p>
            Subscriptions renew automatically for the same period until you cancel, and cancelling takes effect at the
            end of the period you have already paid for. Fees are stated exclusive of taxes, and you are responsible
            for any that apply. Credits are for use within the Service, do not carry a cash value, and are not
            redeemable for cash.
          </p>
          <p>
            Web payments are processed by Stripe. Purchases made inside the iOS app are processed by Apple, and refunds
            for those follow Apple's own policy rather than ours. For web purchases, contact{" "}
            <a href="mailto:contact@example.com">contact@example.com</a> and we will look at refund requests case by case,
            in addition to any refund rights the law gives you.
          </p>
        </LegalSection>

        <LegalSection title="10. Confidentiality">
          <p>
            Each party will use reasonable care to protect the other's non-public information obtained through the Service
            and use it only as needed to perform under these Terms, except where disclosure is required by law.
          </p>
        </LegalSection>

        <LegalSection title="11. Disclaimers">
          <p>
            THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE." TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE DISCLAIM
            ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,
            NON-INFRINGEMENT, AND ANY WARRANTY ARISING FROM COURSE OF DEALING OR TRADE USAGE. WE DO NOT WARRANT THAT
            THE SERVICE WILL BE UNINTERRUPTED OR ERROR FREE, THAT ANY GENERATION WILL SUCCEED, OR THAT OUTPUTS WILL BE
            ACCURATE, ORIGINAL, OR FIT TO PUBLISH. SOME JURISDICTIONS DO NOT ALLOW CERTAIN EXCLUSIONS, SO PARTS OF THIS
            SECTION MAY NOT APPLY TO YOU.
          </p>
        </LegalSection>

        <LegalSection title="12. Limitation of liability">
          <p>
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, OUR AGGREGATE LIABILITY ARISING OUT OF THESE TERMS OR THE SERVICE
            WILL NOT EXCEED THE GREATER OF ONE HUNDRED US DOLLARS (US$100) OR THE AMOUNT YOU PAID US IN THE TWELVE
            MONTHS BEFORE THE EVENT GIVING RISE TO THE CLAIM. WE WILL NOT BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL,
            CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR FOR LOST PROFITS, REVENUE, GOODWILL, OR DATA, EVEN IF WE WERE TOLD
            SUCH DAMAGES WERE POSSIBLE. THESE LIMITS APPLY TO EVERY THEORY OF LIABILITY AND DO NOT APPLY WHERE THE LAW
            DOES NOT ALLOW THEM.
          </p>
        </LegalSection>

        <LegalSection title="13. Indemnity">
          <p>
            You will defend and indemnify Studio and its members and staff against third-party claims, damages, and
            reasonable legal costs arising from your Customer Content, the clips you publish, your use of someone's
            face or voice without their permission, or your misuse of the Service. We will tell you promptly about any
            such claim and let you control the defense, and you will not settle in a way that admits fault on our
            behalf without asking us.
          </p>
        </LegalSection>

        <LegalSection title="14. Termination">
          <p>
            You may stop using the Service at any time. We may suspend or terminate access for violations of these Terms,
            abuse, non-payment, or risk to the Service or other users. Provisions that by nature should survive
            (including ownership, disclaimers, and liability limits) will survive termination.
          </p>
        </LegalSection>

        <LegalSection title="15. Governing law">
          <p>
            These Terms are governed by the laws of the place where the operator of this Service is established,
            without regard to its conflict-of-law rules. Before filing, please raise the issue with us
            at <a href="mailto:contact@example.com">contact@example.com</a> so we can try to resolve it directly.
          </p>
        </LegalSection>

        <LegalSection title="16. Contact">
          <p>
            Legal / terms: <a href="mailto:contact@example.com">contact@example.com</a>
            <br />
            Privacy: <a href="mailto:privacy@example.com">privacy@example.com</a>
            <br />
            <Link to="/contact">Contact form</Link> · <Link to="/privacy">Privacy Policy</Link>
          </p>
        </LegalSection>
    </LegalDocument>
  );
}
