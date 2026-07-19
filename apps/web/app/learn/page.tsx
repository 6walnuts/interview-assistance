"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Topic } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const CATEGORIES = [
  { id: "coding", name: "Coding" },
  { id: "backend", name: "Backend" },
  { id: "system_design", name: "System Design" },
  { id: "cs_fundamentals", name: "CS Fundamentals" },
  { id: "infrastructure", name: "Infrastructure" },
  { id: "ai_infrastructure", name: "AI Infrastructure" },
];

export default function LearnPage() {
  const { t: tr } = useI18n();
  const [category, setCategory] = useState("coding");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selected, setSelected] = useState<Topic | null>(null);
  const [chat, setChat] = useState<{ role: "user" | "coach"; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listTopics(category)
      .then((t) => { setTopics(t); setSelected(null); setChat([]); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [category]);

  async function ask(message: string, mode = "explain") {
    if (!message.trim() || busy) return;
    setBusy(true);
    setChat((c) => [...c, { role: "user", text: message }]);
    setInput("");
    try {
      const resp = await api.coachChat(message, mode, selected?.slug);
      setChat((c) => [...c, { role: "coach", text: resp.reply }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Coach unavailable");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">{tr("Learn")}</h1>
      {error && <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      <div className="mt-4 flex flex-wrap gap-2">
        {CATEGORIES.map((c) => (
          <button key={c.id} onClick={() => setCategory(c.id)}
            className={`rounded-full border px-4 py-1.5 text-sm ${category === c.id ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-600"}`}>
            {tr(c.name)}
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="grid gap-3 sm:grid-cols-2">
          {topics.map((t) => (
            <div key={t.id} role="button" tabIndex={0}
              onClick={() => { setSelected(t); setChat([]); }}
              onKeyDown={(e) => e.key === "Enter" && (setSelected(t), setChat([]))}
              className={`card cursor-pointer text-left transition ${selected?.id === t.id ? "!border-brand-600" : "hover:border-slate-300"}`}>
              <div className="flex items-center justify-between">
                <p className="font-medium">{t.name}</p>
                <span className="text-xs text-slate-400">D{t.difficulty}</span>
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-slate-100">
                <div className="h-1.5 rounded-full bg-brand-500" style={{ width: `${t.mastery?.mastery_score ?? 0}%` }} />
              </div>
              <div className="mt-1 flex items-center justify-between">
                <p className="text-xs text-slate-500">{tr("Mastery")} {t.mastery?.mastery_score ?? 0}/100</p>
                <Link href={`/quiz/${t.slug}`} onClick={(e) => e.stopPropagation()}
                  className="rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 hover:bg-brand-100">
                  {tr("Chapter quiz →")}
                </Link>
              </div>
            </div>
          ))}
        </div>

        <div className="card flex h-[32rem] flex-col">
          <h2 className="font-semibold">
            {tr("Coach")}{selected ? ` — ${selected.name}` : ""}
          </h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {["explain", "quiz", "flashcards", "review_mistakes"].map((m) => (
              <button key={m} className="btn-secondary !px-2 !py-1 text-xs" disabled={!selected || busy}
                onClick={() => ask(`Start ${m.replaceAll("_", " ")} mode for ${selected?.name}.`, m)}>
                {tr(m.replaceAll("_", " "))}
              </button>
            ))}
          </div>
          <div className="mt-3 flex-1 space-y-2 overflow-y-auto">
            {chat.length === 0 && (
              <p className="text-sm text-slate-500">
                {selected ? tr("Ask the coach anything about this topic.") : tr("Pick a topic to start learning.")}
              </p>
            )}
            {chat.map((m, i) => (
              <div key={i} className={`max-w-[90%] whitespace-pre-wrap rounded-xl px-3 py-2 text-sm ${m.role === "coach" ? "bg-slate-100" : "ml-auto bg-brand-50"}`}>
                {m.text}
              </div>
            ))}
            {busy && <p className="text-xs text-slate-400">{tr("Coach is thinking…")}</p>}
          </div>
          <div className="mt-2 flex gap-2">
            <input className="input" placeholder={tr("Ask the coach…")} value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask(input)} disabled={!selected} />
            <button className="btn-primary" disabled={!selected || busy || !input.trim()} onClick={() => ask(input)}>{tr("Send")}</button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
