/** Plan product modes, keep aligned with backend app/plan_features.py */

export type PlanTrack = "content";

export type PlanFeature = "studio" | "billing" | "static_ads";

export function hasFeature(features: string[] | undefined | null, feature: PlanFeature): boolean {
  if (!features || !features.length) {
    return feature === "studio" || feature === "billing" || feature === "static_ads";
  }
  return features.includes(feature);
}

export function featureLabel(feature: PlanFeature): string {
  const labels: Record<PlanFeature, string> = {
    studio: "Studio",
    billing: "Billing",
    static_ads: "Images",
  };
  return labels[feature];
}
