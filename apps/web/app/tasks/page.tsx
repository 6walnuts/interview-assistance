"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Task } from "@/lib/types";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listTasks().then(setTasks).catch((e) => setError(e instanceof Error ? e.message : "Failed"));
  }, []);

  async function complete(task: Task) {
    try {
      const updated = await api.completeTask(task.id);
      setTasks((all) => all.map((t) => (t.id === task.id ? updated : t)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to complete");
    }
  }

  const pending = tasks.filter((t) => t.status !== "completed");
  const done = tasks.filter((t) => t.status === "completed");

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">Learning tasks</h1>
      {error && <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      {tasks.length === 0 && (
        <p className="mt-4 text-slate-500">No tasks yet — finish a mock interview to generate your plan.</p>
      )}
      <div className="mt-6 space-y-3">
        {pending.map((t) => (
          <div key={t.id} className="card flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded bg-brand-50 px-1.5 py-0.5 text-xs text-brand-700">{t.task_type}</span>
                {t.topic_slug && <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{t.topic_slug}</span>}
                {t.source === "interview_report" && (
                  <span className="rounded bg-amber-50 px-1.5 py-0.5 text-xs text-amber-700">from interview</span>
                )}
              </div>
              <p className="mt-2 font-medium">{t.title}</p>
              <p className="text-sm text-slate-600">{t.description}</p>
              {t.due_at && <p className="mt-1 text-xs text-slate-400">Due {new Date(t.due_at).toLocaleDateString()}</p>}
            </div>
            <button className="btn-secondary shrink-0" onClick={() => complete(t)}>Mark done</button>
          </div>
        ))}
      </div>
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
