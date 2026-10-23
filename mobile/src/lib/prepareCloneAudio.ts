/**
 * Copy a clone sample to cache with a real audio filename.
 *
 * expo-file-system uploadAsync uses the path's last component as the multipart
 * filename. Native AudioRecorder only sees flattened options: nested `ios` /
 * `android` keys from RecordingPresets are ignored, so HIGH_QUALITY used to
 * write Linear PCM into a .m4a name that ffmpeg could not demux.
 */
import { Platform } from "react-native";
import { ApiError } from "@/src/api/client";
import { normalizeUploadUri } from "@/src/lib/prepareImageUpload";

export type CloneAudioPart = {
  uri: string;
  name: string;
  type: string;
};

/** Flattened native recorder options. Do not pass RecordingPresets through as-is. */
export function cloneRecordingOptions() {
  if (Platform.OS === "ios") {
    return {
      extension: ".wav",
      sampleRate: 44100,
      numberOfChannels: 1,
      bitRate: 128000,
      isMeteringEnabled: false,
      outputFormat: "lpcm",
      audioQuality: 0x7f,
      linearPCMBitDepth: 16,
      linearPCMIsBigEndian: false,
      linearPCMIsFloat: false,
    };
  }
  return {
    extension: ".m4a",
    sampleRate: 44100,
    numberOfChannels: 1,
    bitRate: 128000,
    isMeteringEnabled: false,
    outputFormat: "mpeg4",
    audioEncoder: "aac",
  };
}

export const CLONE_AUDIO_PICKER_TYPES =
  Platform.OS === "ios"
    ? [
        "com.apple.m4a-audio",
        "com.apple.coreaudio-format",
        "public.mpeg-4-audio",
        "public.audio",
        "public.mp3",
        "com.microsoft.waveform-audio",
      ]
    : ["audio/mp4", "audio/x-m4a", "audio/mpeg", "audio/wav", "audio/aac", "audio/*"];

function guessCloneExt(name: string, type: string, uri: string): string {
  const fromName = name.match(/\.(m4a|mp3|wav|aac|mp4|caf|ogg|aiff|aif)$/i);
  if (fromName) return `.${fromName[1].toLowerCase()}`;
  const fromUri = uri.match(/\.(m4a|mp3|wav|aac|mp4|caf|ogg|aiff|aif)(?:\?|$)/i);
  if (fromUri) return `.${fromUri[1].toLowerCase()}`;
  const mime = (type || "").toLowerCase();
  if (mime.includes("mpeg") || mime.includes("mp3")) return ".mp3";
  if (mime.includes("wav")) return ".wav";
  if (mime.includes("caf")) return ".caf";
  if (mime.includes("aiff") || mime.includes("aif")) return ".aiff";
  if (mime.includes("aac") && !mime.includes("mp4")) return ".aac";
  return ".m4a";
}

function mimeForExt(ext: string): string {
  if (ext === ".mp3") return "audio/mpeg";
  if (ext === ".wav") return "audio/wav";
  if (ext === ".caf") return "audio/x-caf";
  if (ext === ".ogg") return "audio/ogg";
  if (ext === ".aac") return "audio/aac";
  if (ext === ".aiff" || ext === ".aif") return "audio/aiff";
  return "audio/mp4";
}

function extFromMagic(bytes: Uint8Array): string | null {
  if (bytes.length >= 4 && bytes[0] === 0x63 && bytes[1] === 0x61 && bytes[2] === 0x66 && bytes[3] === 0x66) {
    return ".caf";
  }
  if (
    bytes.length >= 12 &&
    bytes[0] === 0x52 &&
    bytes[1] === 0x49 &&
    bytes[2] === 0x46 &&
    bytes[3] === 0x46 &&
    bytes[8] === 0x57 &&
    bytes[9] === 0x41 &&
    bytes[10] === 0x56 &&
    bytes[11] === 0x45
  ) {
    return ".wav";
  }
  if (bytes.length >= 12 && bytes[4] === 0x66 && bytes[5] === 0x74 && bytes[6] === 0x79 && bytes[7] === 0x70) {
    return ".m4a";
  }
  if (bytes.length >= 4 && bytes[0] === 0x46 && bytes[1] === 0x4f && bytes[2] === 0x52 && bytes[3] === 0x4d) {
    return ".aiff";
  }
  if (bytes.length >= 3 && bytes[0] === 0x49 && bytes[1] === 0x44 && bytes[2] === 0x33) {
    return ".mp3";
  }
  if (bytes.length >= 2 && bytes[0] === 0xff && (bytes[1] & 0xf0) === 0xf0) {
    const layer = (bytes[1] >> 1) & 0x03;
    return layer === 0 ? ".aac" : ".mp3";
  }
  return null;
}

function bytesFromB64(b64: string): Uint8Array {
  const bin = globalThis.atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
  return out;
}

async function sniffCloneExt(
  FileSystem: typeof import("expo-file-system/legacy"),
  uri: string,
): Promise<string | null> {
  try {
    const b64 = await FileSystem.readAsStringAsync(uri, {
      encoding: FileSystem.EncodingType.Base64,
      position: 0,
      length: 16,
    });
    return extFromMagic(bytesFromB64(b64));
  } catch {
    return null;
  }
}

export async function prepareCloneAudioFile(file: CloneAudioPart): Promise<CloneAudioPart> {
  const FileSystem = await import("expo-file-system/legacy");
  const src = normalizeUploadUri(file.uri);
  if (!src) {
    throw new ApiError("Record or pick an audio file first.", 400);
  }
  let info: { exists: boolean; isDirectory?: boolean; size?: number };
  try {
    info = await FileSystem.getInfoAsync(src);
  } catch {
    throw new ApiError("Could not read that recording. Record or pick a file again.", 400);
  }
  if (!info.exists || info.isDirectory) {
    throw new ApiError("Could not read that recording. Record or pick a file again.", 400);
  }
  if (typeof info.size === "number" && info.size < 1000) {
    throw new ApiError("That recording is empty. Record again.", 400);
  }

  const sniffed = await sniffCloneExt(FileSystem, src);
  const ext = sniffed || guessCloneExt(file.name, file.type, src);
  const destName = `voice-sample-${Date.now()}${ext}`;
  const dest = `${FileSystem.cacheDirectory ?? ""}${destName}`;
  try {
    await FileSystem.copyAsync({ from: src, to: dest });
  } catch {
    throw new ApiError("Could not prepare that recording. Try again.", 400);
  }
  try {
    const copied = await FileSystem.getInfoAsync(dest);
    if (!copied.exists || copied.isDirectory) {
      throw new ApiError("Could not prepare that recording. Try again.", 400);
    }
    if (typeof copied.size === "number" && copied.size < 1000) {
      throw new ApiError("That recording is empty. Record again.", 400);
    }
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError("Could not prepare that recording. Try again.", 400);
  }
  return { uri: dest, name: destName, type: mimeForExt(ext) };
}
