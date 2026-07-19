"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Task } from "@/lib/types";

function actionLink(t: Task): { href: string; label: string } | null {
  if (t.task_type === "quiz" && t.topic_slug) return { href: `/quiz/${t.topic_slug}`, label: "Take quiz" };
  if (t.task_type === "mock_interview") return { href: "/interviews/new", label: "Start interview" };
  if (t.topic_slug) return { href: "/learn", label: "Open Learn" };
  return null;
}

function TaskCard({ t, onComplete }: { t: Task; onComplete: (t: Task) => void }) {
  const link = actionLink(t);
  return (
    <div className="card flex items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <span className="rounded bg-brand-50 px-1.5 py-0.5 text-xs text-brand-700">{t.task_type}</span>
          {t.topic_slug && <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{t.topic_slug}</span>}
          {t.source === "interview_report" && (
            <span className="rounded bg-amber-50 px-1.5 py-0.5 text-xs text-amber-700">from interview</span>
          )}
          {t.source === "study_plan" && (
            <span className="rounded bg-sky-50 px-1.5 py-0.5 text-xs text-sky-700">study plan</span>
          )}
        </div>
        <p className="mt-2 font-medium">{t.title}</p>
        <p className="text-sm text-slate-600">{t.description}</p>
        {t.due_at && <p className="mt-1 text-xs text-slate-400">Due {new Date(t.due_at).toLocaleDateString()}</p>}
      </div>
      <div className="flex shrink-0 flex-col gap-2">
        {link && <Link href={link.href} className="btn-primary text-center !py-1.5">{link.label}</Link>}
        <button className="btn-secondary !py-1.5" onClick={() => onComplete(t)}>Mark done</button>
      </div>
    </div>
  );
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [planSummary, setPlanSummary] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.listTasks().then(setTasks).catch((e) => setError(e instanceof Error ? e.message : "Failed"));
  }, []);
  useEffect(load, [load]);

  async function complete(task: Task) {
    try {
      const updated = await api.completeTask(task.id);
      setTasks((all) => all.map((t) => (t.id === task.id ? updated : t)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to complete");
    }
  }

  async function regenerate() {
    if (!window.confirm("Rebuild the study plan? Pending plan tasks will be replaced.")) return;
    setRegenerating(true);
    setError(null);
    try {
      const plan = await api.generatePlan();
      setPlanSummary(plan.summary);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate plan");
    } finally {
      setRegenerating(false);
    }
  }

  const pending = tasks.filter((t) => t.status !== "completed");
  const done = tasks.filter((t) => t.status === "completed");

  // Plan tasks group by week; everything else (interview follow-ups, coach
  // tasks) is shown first as "up next".
  const planTasks = pending.filter((t) => t.source === "study_plan");
  const otherTasks = pending.filter((t) => t.source !== "study_plan");
  const weeks = new Map<number, Task[]>();
  const ordered = [...planTasks].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  for (const t of ordered) {
    const week = Number((t.payload as { week?: number }).week ?? 1);
    weeks.set(week, [...(weeks.get(week) ?? []), t]);
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Learning tasks</h1>
        <button className="btn-secondary" onClick={regenerate} disabled={regenerating}>
          {regenerating ? "Planning…" : planTasks.length > 0 ? "Rebuild study plan" : "Generate study plan"}
        </button>
      </div>
      {planSummary && <p className="mt-3 rounded-lg bg-sky-50 p-3 text-sm text-sky-800">{planSummary}</p>}
      {error && <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      {tasks.length === 0 && (
        <p className="mt-4 text-slate-500">
          No tasks yet — finish onboarding to generate a study plan, or complete a mock interview.
        </p>
      )}

      {otherTasks.length > 0 && (
        <>
          <h2 className="mt-6 font-semibold text-slate-700">Up next</h2>
          <div className="mt-3 space-y-3">
            {otherTasks.map((t) => <TaskCard key={t.id} t={t} onComplete={complete} />)}
          </div>
        </>
      )}

      {Array.from(weeks.keys()).sort((a, b) => a - b).map((week) => (
        <div key={week}>
          <h2 className="mt-6 font-semibold text-slate-700">
            Week {week}
            <span className="ml-2 text-xs font-normal text-slate-400">
              {weeks.get(week)!.length} task{weeks.get(week)!.length > 1 ? "s" : ""}
            </span>
          </h2>
          <div className="mt-3 space-y-3">
            {weeks.get(week)!.map((t) => <TaskCard key={t.id} t={t} onComplete={complete} />)}
          </div>
        </div>
      ))}

      {done.length > 0 && (
        <>
          <h2 className="mt-8 font-semibold text-slate-500">Completed ({done.length})</h2>
          <div className="mt-3 space-y-2">
            {done.map((t) => (
              <div key={t.id} className="card !py-3 text-sm text-slate-400 line-through">{t.title}</div>
            ))}
          </div>
        </>
      )}
    </AppShell>
  );
}
