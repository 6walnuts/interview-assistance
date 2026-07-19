"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Quiz, QuizResult } from "@/lib/types";

export default function QuizPage() {
  const { slug } = useParams<{ slug: string }>();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setQuiz(null);
    setAnswers({});
    setResult(null);
    setError(null);
    api.getQuiz(slug, 5)
      .then(setQuiz)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load quiz"));
  }, [slug]);

  useEffect(load, [load]);

  async function submit() {
    if (!quiz) return;
    setBusy(true);
    setError(null);
    try {
      const payload = quiz.questions.map((q) => ({
        question_id: q.id,
        selected_index: answers[q.id],
      }));
      setResult(await api.submitQuiz(slug, payload));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit");
    } finally {
      setBusy(false);
    }
  }

  const allAnswered = quiz !== null && quiz.questions.every((q) => answers[q.id] !== undefined);

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">
            {quiz ? `${quiz.topic_name} · Chapter quiz` : "Chapter quiz"}
          </h1>
          <Link href="/learn" className="text-sm text-brand-600">Back to Learn</Link>
        </div>
        {error && <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        {!quiz && !error && <p className="mt-4 text-slate-500">Preparing questions…</p>}

        {result && (
          <div className="card mt-4 text-center">
            <p className="text-4xl font-bold">
              {result.correct}<span className="text-xl text-slate-400"> / {result.total}</span>
            </p>
            <p className="mt-1 text-sm text-slate-600">
              Mastery is now <span className="font-semibold">{result.mastery_score}/100</span>
              {result.completed_task_ids.length > 0 && (
                <span className="ml-2 rounded bg-green-50 px-2 py-0.5 text-xs text-green-700">
                  {result.completed_task_ids.length} learning task completed ✓
                </span>
              )}
            </p>
            <div className="mt-3 flex justify-center gap-2">
              <button className="btn-secondary" onClick={load}>Try another set</button>
              <Link href="/tasks" className="btn-primary">Back to tasks</Link>
            </div>
          </div>
        )}

        <div className="mt-4 space-y-4">
          {quiz?.questions.map((q, qi) => {
            const graded = result?.results.find((r) => r.question_id === q.id);
            return (
              <div key={q.id} className="card">
                <p className="font-medium">
                  <span className="mr-2 text-slate-400">{qi + 1}.</span>
                  {q.question}
                </p>
                <div className="mt-3 space-y-2">
                  {q.options.map((opt, oi) => {
                    const selected = answers[q.id] === oi;
                    let cls = selected ? "border-brand-600 bg-brand-50" : "border-slate-200 hover:border-slate-300";
                    if (graded) {
                      if (oi === graded.correct_index) cls = "border-green-600 bg-green-50";
                      else if (selected && !graded.is_correct) cls = "border-red-500 bg-red-50";
                      else cls = "border-slate-200 opacity-60";
                    }
                    return (
                      <button
                        key={oi}
                        disabled={result !== null}
                        onClick={() => setAnswers((a) => ({ ...a, [q.id]: oi }))}
                        className={`block w-full rounded-lg border p-3 text-left text-sm transition ${cls}`}
                      >
                        <span className="mr-2 font-mono text-slate-400">{String.fromCharCode(65 + oi)}.</span>
                        {opt}
                      </button>
                    );
                  })}
                </div>
                {graded && (
                  <p className={`mt-3 rounded-lg p-3 text-sm ${graded.is_correct ? "bg-green-50 text-green-800" : "bg-amber-50 text-amber-800"}`}>
                    {graded.is_correct ? "✓ Correct. " : "✗ Not quite. "}
                    {graded.explanation}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {quiz && !result && (
          <button className="btn-primary mt-4 w-full" disabled={!allAnswered || busy} onClick={submit}>
            {busy ? "Grading…" : allAnswered ? "Submit answers" : "Answer all questions to submit"}
          </button>
        )}
      </div>
    </AppShell>
  );
}
