import { Platform } from "react-native";
import {
  endConnection,
  fetchProducts,
  finishTransaction,
  getAvailablePurchases,
  initConnection,
  purchaseErrorListener,
  purchaseUpdatedListener,
  requestPurchase,
  type Product,
  type ProductSubscription,
  type Purchase,
} from "expo-iap";
import { api } from "../api/client";
import { alertError, alertInfo } from "../lib/alerts";
import { hapticSuccess } from "../lib/haptics";

export type ServerIapProduct = {
  apple_product_id: string;
  kind: "plan" | "pack";
  sku: string;
  title: string;
  description: string;
  store_type: "subscription" | "consumable";
  price_cents: number;
};

export type StoreProductRow = ServerIapProduct & {
  storePrice?: string;
  storeTitle?: string;
};

type PendingPurchase = {
  workspaceId: string;
  product: ServerIapProduct;
  resolve: (ok: boolean) => void;
  reject: (err: Error) => void;
};

let connected = false;
let pending: PendingPurchase | null = null;
let listenersAttached = false;
/** Last workspace used for IAP so late StoreKit deliveries can still confirm. */
let lastWorkspaceId: string | null = null;

export function setIapWorkspaceId(workspaceId: string | null) {
  lastWorkspaceId = workspaceId?.trim() || null;
}

function purchaseFields(purchase: Purchase): {
  productId: string;
  transactionId: string;
  signed: string | null;
} {
  const productId = String(
    ("productId" in purchase && purchase.productId) ||
      (purchase as { id?: string }).id ||
      "",
  );
  const transactionId = String(
    ("transactionId" in purchase && purchase.transactionId) ||
      (purchase as { id?: string }).id ||
      "",
  );
  const signed =
    ("purchaseToken" in purchase && purchase.purchaseToken) ||
    ("jwsRepresentationIOS" in purchase
      ? (purchase as { jwsRepresentationIOS?: string }).jwsRepresentationIOS
      : null) ||
    null;
  return {
    productId,
    transactionId,
    signed: signed ? String(signed) : null,
  };
}

async function confirmPurchaseForWorkspace(
  workspaceId: string,
  purchase: Purchase,
  product: ServerIapProduct,
): Promise<void> {
  const { productId, transactionId, signed } = purchaseFields(purchase);
  if (!transactionId) {
    throw new Error("Purchase missing transaction id");
  }
  await api.confirmIapPurchase({
    workspace_id: workspaceId,
    apple_product_id: productId || product.apple_product_id,
    transaction_id: transactionId,
    signed_transaction: signed,
  });
  await finishTransaction({
    purchase,
    isConsumable: product.store_type === "consumable",
  });
}

function attachListeners() {
  if (listenersAttached) return;
  listenersAttached = true;

  purchaseUpdatedListener(async (purchase: Purchase) => {
    const current = pending;
    if (current) {
      try {
        await confirmPurchaseForWorkspace(current.workspaceId, purchase, current.product);
        current.resolve(true);
      } catch (e) {
        current.reject(e instanceof Error ? e : new Error("Purchase failed"));
      } finally {
        pending = null;
      }
      return;
    }

    // Late StoreKit delivery (resume, queue flush) when no in-flight purchase().
    const workspaceId = lastWorkspaceId;
    if (!workspaceId) return;
    try {
      const catalog = await api.listIapProducts();
      const { productId } = purchaseFields(purchase);
      const product = catalog.find((p) => p.apple_product_id === productId);
      if (!product) return;
      await confirmPurchaseForWorkspace(workspaceId, purchase, product);
    } catch {
      // Leave unfinished for processUnfinishedPurchases / restore.
    }
  });

  purchaseErrorListener((error) => {
    if (!pending) return;
    const msg = error?.message || "Purchase cancelled or failed";
    pending.reject(new Error(msg));
    pending = null;
  });
}

export async function ensureIapReady(): Promise<boolean> {
  if (Platform.OS !== "ios") return false;
  if (connected) return true;
  try {
    await initConnection();
    attachListeners();
    connected = true;
    return true;
  } catch {
    return false;
  }
}

/**
 * Confirm + finish any StoreKit purchases left unfinished (app killed mid-confirm).
 * Call after auth + workspace are ready (e.g. billing screen mount or app foreground).
 */
export async function processUnfinishedPurchases(workspaceId: string): Promise<number> {
  if (Platform.OS !== "ios" || !workspaceId) return 0;
  const ready = await ensureIapReady();
  if (!ready) return 0;
  try {
    return await restorePurchases(workspaceId);
  } catch {
    return 0;
  }
}

export async function shutdownIap() {
  if (!connected) return;
  try {
    await endConnection();
  } catch {
    /* ignore */
  }
  connected = false;
}

export async function loadPaywallProducts(): Promise<StoreProductRow[]> {
  const catalog = await api.listIapProducts();
  const ready = await ensureIapReady();
  if (!ready) {
    return catalog.map((p) => ({ ...p }));
  }

  const subIds = catalog.filter((p) => p.store_type === "subscription").map((p) => p.apple_product_id);
  const inAppIds = catalog.filter((p) => p.store_type === "consumable").map((p) => p.apple_product_id);

  const storeById = new Map<string, Product | ProductSubscription>();
  try {
    if (subIds.length) {
      const subs = (await fetchProducts({ skus: subIds, type: "subs" })) as ProductSubscription[] | null;
      for (const s of subs || []) {
        const id = (s as { id?: string }).id || (s as { productId?: string }).productId;
        if (id) storeById.set(String(id), s);
      }
    }
    if (inAppIds.length) {
      const apps = (await fetchProducts({ skus: inAppIds, type: "in-app" })) as Product[] | null;
      for (const p of apps || []) {
        const id = (p as { id?: string }).id || (p as { productId?: string }).productId;
        if (id) storeById.set(String(id), p);
      }
    }
  } catch {
    // Store not available (Expo Go / no products). Fall back to catalog prices.
  }

  return catalog.map((row) => {
    const store = storeById.get(row.apple_product_id);
    const displayPrice =
      store && "displayPrice" in store
        ? String((store as { displayPrice?: string }).displayPrice || "")
        : store && "localizedPrice" in store
          ? String((store as { localizedPrice?: string }).localizedPrice || "")
          : undefined;
    const storeTitle =
      store && "title" in store ? String((store as { title?: string }).title || "") : undefined;
    return {
      ...row,
      storePrice: displayPrice || undefined,
      storeTitle: storeTitle || undefined,
    };
  });
}

export function formatCatalogPrice(cents: number): string {
  return `$${(cents / 100).toFixed(cents % 100 === 0 ? 0 : 2)}`;
}

/**
 * Start StoreKit purchase then wait for confirm + finish.
 * Requires a development/production build (not Expo Go).
 */
export function purchaseProduct(workspaceId: string, product: ServerIapProduct): Promise<boolean> {
  return new Promise(async (resolve, reject) => {
    if (Platform.OS !== "ios") {
      reject(new Error("In-app purchases are only available on iOS."));
      return;
    }
    const ready = await ensureIapReady();
    if (!ready) {
      reject(new Error("Store is not available. Use a development build, not Expo Go."));
      return;
    }
    if (pending) {
      reject(new Error("Another purchase is already in progress."));
      return;
    }
    lastWorkspaceId = workspaceId;
    pending = { workspaceId, product, resolve, reject };
    try {
      await requestPurchase({
        request: {
          apple: { sku: product.apple_product_id },
          google: { skus: [product.apple_product_id] },
        },
        type: product.store_type === "subscription" ? "subs" : "in-app",
      });
    } catch (e) {
      pending = null;
      reject(e instanceof Error ? e : new Error("Could not start purchase"));
    }
  });
}

export async function buyWithFeedback(workspaceId: string, product: ServerIapProduct) {
  try {
    await purchaseProduct(workspaceId, product);
    void hapticSuccess();
    alertInfo("Purchase complete", product.title);
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Purchase failed";
    if (/cancel/i.test(msg)) return false;
    alertError("Purchase failed", msg);
    return false;
  }
}

/**
 * Re-sync unfinished / already-owned StoreKit purchases with the server.
 * Required for App Store subscription guidelines.
 */
export async function restorePurchases(workspaceId: string): Promise<number> {
  if (Platform.OS !== "ios") {
    throw new Error("Restore is only available on iOS.");
  }
  const ready = await ensureIapReady();
  if (!ready) {
    throw new Error("Store is not available. Use a development or TestFlight build.");
  }

  const catalog = await api.listIapProducts();
  const byId = new Map(catalog.map((p) => [p.apple_product_id, p]));
  const purchases = (await getAvailablePurchases()) as Purchase[];
  let restored = 0;

  for (const purchase of purchases || []) {
    const productId =
      ("productId" in purchase && purchase.productId) ||
      (purchase as { id?: string }).id ||
      "";
    const product = byId.get(String(productId));
    if (!product) continue;

    const transactionId =
      ("transactionId" in purchase && purchase.transactionId) ||
      (purchase as { id?: string }).id ||
      "";
    if (!transactionId) continue;

    const signed =
      ("purchaseToken" in purchase && purchase.purchaseToken) ||
      ("jwsRepresentationIOS" in purchase
        ? (purchase as { jwsRepresentationIOS?: string }).jwsRepresentationIOS
        : null) ||
      null;

    try {
      await api.confirmIapPurchase({
        workspace_id: workspaceId,
        apple_product_id: product.apple_product_id,
        transaction_id: String(transactionId),
        signed_transaction: signed ? String(signed) : null,
      });
      await finishTransaction({
        purchase,
        isConsumable: product.store_type === "consumable",
      });
      restored += 1;
    } catch {
      // Skip individual failures; continue restoring others.
    }
  }

  return restored;
}

export async function restoreWithFeedback(workspaceId: string) {
  try {
    const count = await restorePurchases(workspaceId);
    if (count > 0) {
      void hapticSuccess();
      alertInfo("Restored", `Synced ${count} purchase${count === 1 ? "" : "s"} with your account.`);
    } else {
      alertInfo("Nothing to restore", "No prior App Store purchases found for this Apple ID.");
    }
    return count;
  } catch (e) {
    alertError("Restore failed", e instanceof Error ? e.message : "Could not restore purchases.");
    return 0;
  }
}
