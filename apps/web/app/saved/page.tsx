"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { useI18n } from "@/lib/i18n";

type SavedTurn = { speaker: "asker" | "answerer" | "user"; text: string };
type SavedDuo = { id: string; title: string; kind: string; savedAt: string; turns: SavedTurn[] };

const KEY = "aic_saved_duos";

export default function SavedPage() {
  const { t } = useI18n();
  const [items, setItems] = useState<SavedDuo[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    try {
      setItems(JSON.parse(localStorage.getItem(KEY) ?? "[]") as SavedDuo[]);
    } catch {
      setItems([]);
    }
  }, []);

  function remove(id: string) {
    const next = items.filter((it) => it.id !== id);
    setItems(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  }

  function exportOne(item: SavedDuo) {
    const lines = [`# ${item.title}`, ""];
    for (const turn of item.turns) {
      const label = turn.speaker === "asker" ? t("Asker") : turn.speaker === "answerer" ? t("Answerer") : t("You");
      lines.push(`**${label}**:`, "", turn.text, "");
    }
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${item.kind}-${item.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const roleStyle: Record<SavedTurn["speaker"], string> = {
    asker: "bg-slate-100",
    answerer: "ml-auto bg-brand-50",
    user: "ml-auto bg-green-50",
  };

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">🗂 {t("Saved dialogues")}</h1>
      {items.length === 0 && (
        <p className="mt-4 text-slate-500">
          {t("Nothing saved yet — favorite a dialogue from the AI Q&A or Resume BQ Battle pages.")}
        </p>
      )}
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={item.id} className="card">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-medium">{item.title}</p>
                <p className="text-xs text-slate-400">
                  {new Date(item.savedAt).toLocaleString()} · {item.turns.length} {t("turns")}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button className="btn-secondary !py-1 text-xs"
                  onClick={() => setOpenId(openId === item.id ? null : item.id)}>
                  {openId === item.id ? t("Collapse") : t("View")}
                </button>
                <button className="btn-secondary !py-1 text-xs" onClick={() => exportOne(item)}>
                  ⬇️ {t("Export")}
                </button>
                <button className="btn-secondary !py-1 text-xs text-red-600" onClick={() => remove(item.id)}>
                  {t("Delete")}
                </button>
              </div>
            </div>
            {openId === item.id && (
              <div className="mt-3 max-h-96 space-y-2 overflow-y-auto border-t border-slate-100 pt-3">
                {item.turns.map((turn, i) => (
                  <div key={i} className={`max-w-[85%] whitespace-pre-wrap rounded-xl px-3 py-2 text-sm ${roleStyle[turn.speaker]}`}>
                    {turn.text}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
