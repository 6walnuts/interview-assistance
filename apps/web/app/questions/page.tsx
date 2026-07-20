"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { QuestionSummary } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const TYPES = [
  { id: "", name: "All types" },
  { id: "coding", name: "Coding" },
  { id: "system_design", name: "System Design" },
];
const DIFFICULTIES = ["", "easy", "medium", "hard"];

const DIFF_COLORS: Record<string, string> = {
  easy: "bg-green-50 text-green-700",
  medium: "bg-amber-50 text-amber-700",
  hard: "bg-red-50 text-red-700",
};

export default function QuestionsPage() {
  const { t } = useI18n();
  const [questions, setQuestions] = useState<QuestionSummary[]>([]);
  const [type, setType] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  // Custom question form
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newPrompt, setNewPrompt] = useState("");
  const [newType, setNewType] = useState("system_design");
  const [newDifficulty, setNewDifficulty] = useState("medium");
  const [creating, setCreating] = useState(false);

  async function createCustom() {
    if (newTitle.trim().length < 3 || newPrompt.trim().length < 10) return;
    setCreating(true);
    setError(null);
    try {
      const q = await api.createCustomQuestion({
        title: newTitle, prompt: newPrompt,
        interview_type: newType, difficulty: newDifficulty,
      });
      setQuestions((all) => [q, ...all]);
      setShowCreate(false);
      setNewTitle("");
      setNewPrompt("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    api.listQuestions({ interview_type: type || undefined, difficulty: difficulty || undefined })
      .then(setQuestions)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [type, difficulty]);

  const categories = Array.from(new Set(questions.map((q) => q.category))).sort();
  const visible = category ? questions.filter((q) => q.category === category) : questions;

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("Question bank")}</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500">{visible.length} {t("questions_count")}</span>
          <button className="btn-primary !py-1.5 text-sm" onClick={() => setShowCreate((v) => !v)}>
            ➕ {t("Custom question")}
          </button>
        </div>
      </div>
      {error && <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}

      {showCreate && (
        <div className="card mt-4">
          <p className="text-sm font-semibold text-slate-700">{t("Write your own question")}</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <input className="input sm:col-span-2" placeholder={t("Question title")}
              value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            <select className="input" value={newType} onChange={(e) => setNewType(e.target.value)}>
              <option value="system_design">{t("System Design")}</option>
              <option value="coding">{t("Coding")}</option>
            </select>
            <select className="input" value={newDifficulty} onChange={(e) => setNewDifficulty(e.target.value)}>
              {["easy", "medium", "hard"].map((d) => <option key={d} value={d}>{t(d)}</option>)}
            </select>
            <textarea className="input h-28 resize-none sm:col-span-2"
              placeholder={t("Describe the question: scenario, requirements, constraints…")}
              value={newPrompt} onChange={(e) => setNewPrompt(e.target.value)} />
          </div>
          <button className="btn-primary mt-3" disabled={creating || newTitle.trim().length < 3 || newPrompt.trim().length < 10}
            onClick={() => void createCustom()}>
            {creating ? t("Saving…") : t("Create question")}
          </button>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {TYPES.map((ty) => (
          <button key={ty.id} onClick={() => { setType(ty.id); setCategory(""); }}
            className={`rounded-full border px-3 py-1 text-sm ${type === ty.id ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-600"}`}>
            {t(ty.name)}
          </button>
        ))}
        <span className="mx-1 text-slate-300">|</span>
        {DIFFICULTIES.map((d) => (
          <button key={d} onClick={() => setDifficulty(d)}
            className={`rounded-full border px-3 py-1 text-sm ${difficulty === d ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-600"}`}>
            {d === "" ? t("All difficulties") : t(d)}
          </button>
        ))}
      </div>

      {categories.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          <button onClick={() => setCategory("")}
            className={`rounded px-2 py-0.5 text-xs ${category === "" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"}`}>
            {t("all")}
          </button>
          {categories.map((c) => (
            <button key={c} onClick={() => setCategory(c === category ? "" : c)}
              className={`rounded px-2 py-0.5 text-xs ${category === c ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"}`}>
              {c}
            </button>
          ))}
        </div>
      )}

      <div className="mt-4 space-y-3">
        {visible.map((q) => (
          <div key={q.id} className="card flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium">{q.title}</p>
                <span className={`rounded px-1.5 py-0.5 text-xs ${DIFF_COLORS[q.difficulty] ?? "bg-slate-100 text-slate-600"}`}>
                  {t(q.difficulty)}
                </span>
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{q.category}</span>
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                  {q.interview_type === "coding" ? t("Coding") : t("System Design")}
                </span>
                {q.custom && (
                  <span className="rounded bg-violet-50 px-1.5 py-0.5 text-xs text-violet-700">{t("custom")}</span>
                )}
              </div>
              <p className="mt-1 text-sm text-slate-600">{q.prompt_preview}</p>
            </div>
            <div className="flex shrink-0 flex-col gap-1.5">
              <Link
                className="btn-primary !py-1 text-center text-xs"
                href={`/interviews/new?question_id=${q.id}&type=${q.interview_type}&title=${encodeURIComponent(q.title)}`}
              >
                {t("Interview with this question")}
              </Link>
              <Link
                className="rounded-lg bg-green-50 px-3 py-1 text-center text-xs font-medium text-green-700 hover:bg-green-100"
                href={`/tutor/${q.category}?question_id=${q.id}&title=${encodeURIComponent(q.title)}`}
              >
                {t("Learn with this question")}
              </Link>
              <Link
                className="rounded-lg bg-violet-50 px-3 py-1 text-center text-xs font-medium text-violet-700 hover:bg-violet-100"
                href={`/duo/${q.category}?question_id=${q.id}&title=${encodeURIComponent(q.title)}`}
              >
                🎭 {t("Watch AI × AI Q&A")}
              </Link>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
