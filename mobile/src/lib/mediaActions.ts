import { Platform } from "react-native";
import * as FileSystem from "expo-file-system/legacy";
import { Asset, requestPermissionsAsync } from "expo-media-library";
import * as Sharing from "expo-sharing";
import { mediaAuthHeaders, resolveMediaUrl } from "./media";
import { alertError, alertInfo } from "./alerts";
import { hapticSuccess } from "./haptics";

async function downloadToCache(url: string, filename: string): Promise<string> {
  const resolved = resolveMediaUrl(url);
  if (!resolved) throw new Error("No media URL");
  const dir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory;
  if (!dir) throw new Error("No cache directory");
  // Keep filenames filesystem-safe.
  const safe = filename.replace(/[^a-zA-Z0-9._-]/g, "-") || `studio-${Date.now()}`;
  const path = `${dir}${safe}`;
  // Bearer when private media has a stale/missing sig (same as expo-image).
  const headers = mediaAuthHeaders(resolved);
  const result = await FileSystem.downloadAsync(
    resolved,
    path,
    headers ? { headers } : undefined,
  );
  if (result.status !== 200) throw new Error(`Download failed (${result.status})`);
  // iOS needs a real file:// URI for Asset.create / share.
  const uri = result.uri;
  return uri.startsWith("file://") || uri.startsWith("content://") ? uri : `file://${uri}`;
}

export async function shareMedia(url: string | null | undefined, filename: string) {
  try {
    const local = await downloadToCache(url || "", filename);
    const can = await Sharing.isAvailableAsync();
    if (!can) {
      alertError("Share", "Sharing is not available on this device.");
      return;
    }
    await Sharing.shareAsync(local, {
      dialogTitle: "Share clip",
      mimeType: filename.endsWith(".mp4") ? "video/mp4" : "image/jpeg",
      UTI: filename.endsWith(".mp4") ? "public.mpeg-4" : "public.jpeg",
    });
  } catch (e) {
    alertError("Share failed", e instanceof Error ? e.message : "Could not share.");
  }
}

/**
 * Save a remote clip/face into the device photo library.
 * Expo SDK 57+: use `Asset.create(uri)` (saveToLibraryAsync throws as deprecated).
 */
export async function saveMediaToPhotos(url: string | null | undefined, filename: string) {
  try {
    // writeOnly: we only add files, we do not need full library read access.
    const perm = await requestPermissionsAsync(true);
    if (!perm.granted) {
      alertError("Photos", "Allow photo library access to save clips.");
      return;
    }
    const local = await downloadToCache(url || "", filename);
    await Asset.create(local);
    void hapticSuccess();
    alertInfo("Saved", Platform.OS === "ios" ? "Saved to Photos." : "Saved to gallery.");
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Could not save.";
    // Surface a clearer line when the legacy API is still referenced somewhere.
    if (/saveToLibraryAsync|deprecated/i.test(msg)) {
      alertError("Save failed", "Photo save API is outdated. Update the app and try again.");
      return;
    }
    alertError("Save failed", msg);
  }
}
