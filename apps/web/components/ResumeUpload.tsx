"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** PDF resume picker: uploads, backend extracts text, callback gets it. */
export default function ResumeUpload({
  onExtract,
  onError,
}: {
  onExtract: (text: string) => void;
  onError: (msg: string) => void;
}) {
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-picking the same file
    if (!file) return;
    setBusy(true);
    try {
      const resp = await api.uploadResumePdf(file);
      onExtract(resp.profile.resume_text ?? "");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="btn-secondary !py-1 text-xs"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {busy ? t("Parsing PDF…") : `📄 ${t("Upload PDF resume")}`}
      </button>
      <input ref={inputRef} type="file" accept="application/pdf,.pdf" hidden onChange={onFile} />
    </>
  );
}
