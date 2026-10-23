/**
 * Convert a library/camera image to a JPEG file React Native FormData can upload.
 * iOS often returns HEIC or ph://-backed assets that the API rejects.
 */
import * as ImageManipulator from "expo-image-manipulator";
import * as ImagePicker from "expo-image-picker";
import { ApiError } from "@/src/api/client";

export type UploadFilePart = {
  uri: string;
  name: string;
  type: string;
};

/** RN FormData on iOS needs a real file:// (or content://) URI, not a bare path. */
export function normalizeUploadUri(uri: string): string {
  const u = (uri || "").trim();
  if (!u) return u;
  if (
    u.startsWith("file://") ||
    u.startsWith("content://") ||
    u.startsWith("http://") ||
    u.startsWith("https://") ||
    u.startsWith("ph://") ||
    u.startsWith("assets-library://")
  ) {
    return u;
  }
  // Bare absolute path from some Expo native modules
  if (u.startsWith("/")) return `file://${u}`;
  return u;
}

export async function ensureMediaLibraryAccess(): Promise<void> {
  const current = await ImagePicker.getMediaLibraryPermissionsAsync();
  if (current.granted || current.accessPrivileges === "limited") return;

  const asked = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (asked.granted || asked.accessPrivileges === "limited") return;

  throw new ApiError(
    "Allow photo access in Settings to upload a face (Settings → Studio → Photos).",
    400,
  );
}

/**
 * Pick a single library image and return a JPEG upload part ready for FormData.
 */
export async function pickAndPrepareFaceImage(): Promise<UploadFilePart> {
  await ensureMediaLibraryAccess();

  const picked = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ["images"],
    quality: 1,
    // Prefer a decode-friendly representation when iOS offers one (avoids raw HEIC).
    preferredAssetRepresentationMode:
      ImagePicker.UIImagePickerPreferredAssetRepresentationMode?.Compatible,
    exif: false,
  });

  if (picked.canceled || !picked.assets?.[0]) {
    throw new ApiError("No photo selected.", 400);
  }

  return prepareImageForUpload(picked.assets[0]);
}

export async function prepareImageForUpload(
  asset: {
    uri: string;
    width?: number | null;
    height?: number | null;
    fileName?: string | null;
    mimeType?: string | null;
  },
  opts?: { maxWidth?: number; namePrefix?: string },
): Promise<UploadFilePart> {
  const maxWidth = opts?.maxWidth ?? 1600;
  const prefix = opts?.namePrefix ?? "face";
  const src = normalizeUploadUri(asset.uri);
  if (!src) {
    throw new ApiError("Could not read that photo. Try another image.", 400);
  }

  const w = typeof asset.width === "number" && asset.width > 0 ? asset.width : null;
  const actions: ImageManipulator.Action[] =
    w != null && w > maxWidth ? [{ resize: { width: maxWidth } }] : [];

  let jpeg: ImageManipulator.ImageResult;
  try {
    jpeg = await ImageManipulator.manipulateAsync(src, actions, {
      compress: 0.88,
      format: ImageManipulator.SaveFormat.JPEG,
    });
  } catch {
    // Retry without resize (some iCloud/HEIC assets fail on resize but convert OK).
    try {
      jpeg = await ImageManipulator.manipulateAsync(src, [], {
        compress: 0.85,
        format: ImageManipulator.SaveFormat.JPEG,
      });
    } catch {
      throw new ApiError(
        "Could not convert that photo. Try a screenshot or a JPEG from Files.",
        400,
      );
    }
  }

  const uri = normalizeUploadUri(jpeg.uri);
  if (!uri) {
    throw new ApiError("Could not save the converted photo. Try again.", 400);
  }

  return {
    uri,
    name: `${prefix}-${Date.now()}.jpg`,
    type: "image/jpeg",
  };
}
