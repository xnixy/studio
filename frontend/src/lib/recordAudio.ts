/** Safari-safe MediaRecorder helpers. iPhone Safari rejects the default webm type. */

/** iOS `audio/*` opens Music and greys out Voice Memos .m4a. Extensions first. */
export const CLONE_AUDIO_ACCEPT =
  ".m4a,.mp3,.wav,.aac,.mp4,audio/mp4,audio/x-m4a,audio/mpeg,audio/wav,audio/aac";


const RECORDER_MIME_CANDIDATES = [
  "audio/mp4",
  "audio/mp4;codecs=mp4a.40.2",
  "audio/aac",
  "audio/webm;codecs=opus",
  "audio/webm",
];

export function pickAudioRecorderMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return RECORDER_MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type));
}

export function fileFromRecording(blob: Blob, mimeType: string): File {
  const type = (blob.type || mimeType || "audio/mp4").split(";")[0].trim() || "audio/mp4";
  const ext = type.includes("mp4") || type.includes("aac") || type.includes("m4a") ? "m4a" : "webm";
  return new File([blob], `voice-sample.${ext}`, { type });
}

export function micRecordErrorMessage(err: unknown): string {
  if (typeof window !== "undefined" && !window.isSecureContext) {
    return "Safari will not open the mic on http. Open this page on https, or upload a Voice Memos file.";
  }
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") {
    return "Mic access was blocked. Allow the microphone for this site, or upload a file.";
  }
  if (name === "NotFoundError") {
    return "No microphone found. Upload a file instead.";
  }
  if (name === "NotSupportedError" || name === "TypeError") {
    return "This browser cannot record. Upload a file instead.";
  }
  if (name === "AbortError") {
    return "Mic prompt timed out. Allow the microphone, or upload a file.";
  }
  return "Could not start the mic. Upload a file instead.";
}

export function startMediaRecorder(rec: MediaRecorder): void {
  try {
    rec.start(250);
  } catch {
    rec.start();
  }
}
