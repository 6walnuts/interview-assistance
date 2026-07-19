"use client";

import { useI18n } from "@/lib/i18n";
import { PLAYBACK_RATES } from "@/lib/voice";

/** Read-aloud playback speed picker, shown next to the Auto-read toggle. */
export default function SpeedSelect({
  rate,
  onChange,
}: {
  rate: number;
  onChange: (r: number) => void;
}) {
  const { t } = useI18n();
  return (
    <select
      className="rounded-full border border-slate-300 bg-white px-2 py-1 text-xs text-slate-600"
      value={String(rate)}
      onChange={(e) => onChange(Number(e.target.value))}
      title={t("Read-aloud speed")}
    >
      {PLAYBACK_RATES.map((r) => (
        <option key={r} value={String(r)}>{r}x</option>
      ))}
    </select>
  );
}
