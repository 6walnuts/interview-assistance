"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { QuestionSummary, Topic } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { useSpeaker, useVoiceInput } from "@/lib/voice";
import SpeedSelect from "@/components/SpeedSelect";
import Markdown from "@/components/Markdown";

const CATEGORIES = [
  { id: "coding", name: "Coding" },
  { id: "backend", name: "Backend" },
  { id: "system_design", name: "System Design" },
  { id: "cs_fundamentals", name: "CS Fundamentals" },
  { id: "infrastructure", name: "Infrastructure" },
  { id: "ai_infrastructure", name: "AI Infrastructure" },
  { id: "machine_learning", name: "Machine Learning" },
  { id: "bagu", name: "CN Interview Canon" },
];

type ChatMsg = { role: "user" | "coach"; text: string };

const CHATS_KEY = "aic_coach_chats";

export default function LearnPage() {
  return (
    <Suspense>
      <LearnContent />
    </Suspense>
  );
}

function LearnContent() {
  const { t: tr } = useI18n();
  const params = useSearchParams();
  const [category, setCategory] = useState(params.get("category") ?? "coding");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selected, setSelected] = useState<Topic | null>(null);
  // Chat history is kept per topic slug so switching topics never loses it.
  const [chats, setChats] = useState<Record<string, ChatMsg[]>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const speaker = useSpeaker(setError);
  const voice = useVoiceInput(
    useCallback((text: string) => setInput((v) => (v ? `${v} ${text}` : text)), []),
    setError
  );

  const chat = selected ? chats[selected.slug] ?? [] : [];

  // Classic questions tagged with the selected topic, if any.
  const [related, setRelated] = useState<QuestionSummary[]>([]);
  useEffect(() => {
    if (!selected) {
      setRelated([]);
      return;
    }
    api.listQuestions({ category: selected.slug })
      .then(setRelated)
      .catch(() => setRelated([]));
  }, [selected]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(CHATS_KEY);
      if (saved) setChats(JSON.parse(saved));
    } catch {
      // Corrupt or unavailable storage — start with empty histories.
    }
  }, []);

  useEffect(() => {
    api.listTopics(category)
      .then((t) => { setTopics(t); setSelected(null); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [category]);

  function appendTo(slug: string, msg: ChatMsg) {
    setChats((all) => {
      const next = { ...all, [slug]: [...(all[slug] ?? []), msg] };
      try {
        localStorage.setItem(CHATS_KEY, JSON.stringify(next));
      } catch {
        // Storage full/unavailable — keep the in-memory history anyway.
      }
      return next;
    });
  }

  function persistChats() {
    setChats((all) => {
      try {
        localStorage.setItem(CHATS_KEY, JSON.stringify(all));
      } catch {
        /* keep in-memory */
      }
      return all;
    });
  }

  function setLast(slug: string, text: string) {
    setChats((all) => {
      const msgs = all[slug] ?? [];
      if (msgs.length === 0 || msgs[msgs.length - 1].role !== "coach") return all;
      return { ...all, [slug]: [...msgs.slice(0, -1), { role: "coach" as const, text }] };
    });
  }

  async function ask(message: string, mode = "explain") {
    if (!message.trim() || busy || !selected) return;
    const slug = selected.slug;
    setBusy(true);
    const history = (chats[slug] ?? []).slice(-12).map((m) => ({
      role: m.role === "coach" ? ("assistant" as const) : ("user" as const),
      content: m.text,
    }));
    appendTo(slug, { role: "user", text: message });
    setInput("");
    try {
      // Stream the reply into a live bubble.
      appendTo(slug, { role: "coach", text: "" });
      let streamed = "";
      const resp = await api.streamCoachChat(message, mode, slug, history, (delta) => {
        streamed += delta;
        setLast(slug, streamed);
      });
      setLast(slug, resp.reply);
      persistChats();
      if (speaker.enabled) speaker.speak(resp.reply);
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
              onClick={() => setSelected(t)}
              onKeyDown={(e) => e.key === "Enter" && setSelected(t)}
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
                <div className="flex gap-1">
                  <Link href={`/tutor/${t.slug}`} onClick={(e) => e.stopPropagation()}
                    className="rounded bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 hover:bg-green-100">
                    {tr("Lesson →")}
                  </Link>
                  <Link href={`/quiz/${t.slug}`} onClick={(e) => e.stopPropagation()}
                    className="rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 hover:bg-brand-100">
                    {tr("Chapter quiz →")}
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="card flex h-[32rem] flex-col">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">
              {tr("Coach")}{selected ? ` — ${selected.name}` : ""}
            </h2>
            <div className="flex items-center gap-1.5">
              <button
                className={`rounded-full border px-2.5 py-0.5 text-xs ${speaker.enabled ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-500"}`}
                onClick={() => speaker.setEnabled(!speaker.enabled)}
                title={tr("Read the coach's replies aloud")}
              >
                {speaker.enabled ? "🔊" : "🔇"} {tr("Auto-read")}
              </button>
              <SpeedSelect rate={speaker.rate} onChange={speaker.setRate} />
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {["explain", "quiz", "flashcards", "review_mistakes"].map((m) => (
              <button key={m} className="btn-secondary !px-2 !py-1 text-xs" disabled={!selected || busy}
                onClick={() => ask(`Start ${m.replaceAll("_", " ")} mode for ${selected?.name}.`, m)}>
                {tr(m.replaceAll("_", " "))}
              </button>
            ))}
            {selected && (
              <Link href={`/duo/${selected.slug}`}
                className="rounded-lg bg-violet-50 px-2 py-1 text-xs font-medium text-violet-700 hover:bg-violet-100">
                🎭 {tr("Watch AI × AI Q&A")}
              </Link>
            )}
          </div>
          <div className="mt-3 flex-1 space-y-2 overflow-y-auto">
            {chat.length === 0 && (
              <p className="text-sm text-slate-500">
                {selected ? tr("Ask the coach anything about this topic.") : tr("Pick a topic to start learning.")}
              </p>
            )}
            {chat.map((m, i) => (
              <div key={i} className={`max-w-[90%] rounded-xl px-3 py-2 text-sm ${m.role === "coach" ? "bg-slate-100" : "ml-auto bg-brand-50"}`}>
                <Markdown text={m.text} />
              </div>
            ))}
            {busy && <p className="text-xs text-slate-400">{tr("Coach is thinking…")}</p>}
          </div>
          {selected && related.length > 0 && (
            <div className="mt-3 border-t border-slate-100 pt-2">
              <p className="text-xs font-semibold text-slate-500">
                🎯 {tr("Classic questions on this topic")} ({related.length})
              </p>
              <div className="mt-1.5 max-h-28 space-y-1.5 overflow-y-auto">
                {related.map((q) => (
                  <div key={q.id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate text-slate-700">
                      {q.title}
                      <span className="ml-1.5 text-xs text-slate-400">{tr(q.difficulty)}</span>
                    </span>
                    <Link
                      className="shrink-0 rounded bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 hover:bg-green-100"
                      href={`/tutor/${selected.slug}?question_id=${q.id}&title=${encodeURIComponent(q.title)}`}
                    >
                      {tr("Learn with this question")}
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="mt-2 flex gap-2">
            <input className="input" placeholder={tr("Ask the coach…")} value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask(input)} disabled={!selected} />
            <button
              className={voice.recording ? "rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white" : "btn-secondary"}
              disabled={!selected || busy || voice.transcribing}
              onClick={voice.toggle}
              title={voice.recording ? tr("Stop recording") : tr("Voice input")}
            >
              {voice.recording ? "⏹" : voice.transcribing ? "…" : "🎙"}
            </button>
            <button className="btn-primary" disabled={!selected || busy || !input.trim()} onClick={() => ask(input)}>{tr("Send")}</button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
