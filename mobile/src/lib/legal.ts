import * as WebBrowser from "expo-web-browser";
import { Linking } from "react-native";
import { MARKETING_BASE_URL } from "./config";

// Trailing slash required: apex host 308s bare /privacy|/terms|/contact to /.
export const PRIVACY_URL = `${MARKETING_BASE_URL}/privacy/`;
export const TERMS_URL = `${MARKETING_BASE_URL}/terms/`;
export const CONTACT_URL = `${MARKETING_BASE_URL}/contact/`;

/** Apple subscription management (required for auto-renewable IAP UX). */
export const MANAGE_SUBSCRIPTIONS_URL = "https://apps.apple.com/account/subscriptions";

export async function openExternalUrl(url: string) {
  try {
    await WebBrowser.openBrowserAsync(url, {
      presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET,
    });
  } catch {
    await Linking.openURL(url);
  }
}

export function openPrivacyPolicy() {
  return openExternalUrl(PRIVACY_URL);
}

export function openTermsOfUse() {
  return openExternalUrl(TERMS_URL);
}

export function openContact() {
  return openExternalUrl(CONTACT_URL);
}

export function openManageSubscriptions() {
  return openExternalUrl(MANAGE_SUBSCRIPTIONS_URL);
}
