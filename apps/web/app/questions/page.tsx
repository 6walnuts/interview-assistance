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
        <span className="text-sm text-slate-500">{visible.length} {t("questions_count")}</span>
      </div>
      {error && <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}

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
              </div>
              <p className="mt-1 text-sm text-slate-600">{q.prompt_preview}</p>
            </div>
            <Link
              className="btn-primary shrink-0 !py-1.5 text-center text-sm"
              href={`/interviews/new?question_id=${q.id}&type=${q.interview_type}&title=${encodeURIComponent(q.title)}`}
            >
              {t("Interview with this question")}
            </Link>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
