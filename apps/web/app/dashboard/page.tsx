"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { ProgressOverview, Task } from "@/lib/types";

export default function DashboardPage() {
  const [overview, setOverview] = useState<ProgressOverview | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.progress(), api.listTasks("pending")])
      .then(([o, t]) => {
        setOverview(o);
        setTasks(t.slice(0, 5));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Link href="/interviews/new" className="btn-primary">Start a mock interview</Link>
      </div>
      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Streak" value={overview ? `${overview.streak_days} days` : "—"} />
        <Stat label="Interviews completed" value={overview?.interviews_completed ?? "—"} />
        <Stat label="Recent avg score" value={overview?.avg_recent_score ?? "—"} />
        <Stat label="Tasks pending" value={overview?.tasks_pending ?? "—"} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Today&apos;s tasks</h2>
            <Link href="/tasks" className="text-sm text-brand-600">View all</Link>
          </div>
          {tasks.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              No pending tasks. Finish a mock interview to generate a study plan.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {tasks.map((t) => (
                <li key={t.id} className="rounded-lg border border-slate-200 p-3 text-sm">
                  <span className="mr-2 rounded bg-brand-50 px-1.5 py-0.5 text-xs text-brand-700">{t.task_type}</span>
                  {t.title}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card">
          <h2 className="font-semibold">Weak areas</h2>
          {overview && overview.weak_topics.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {overview.weak_topics.map((t) => (
                <span key={t} className="rounded-full bg-red-50 px-3 py-1 text-sm text-red-700">{t}</span>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-500">No weak areas identified yet.</p>
          )}
          <h2 className="mt-6 font-semibold">This week</h2>
          <p className="mt-2 text-sm text-slate-600">
            Complete your pending tasks, then take the recommended mock interview to measure progress.
          </p>
        </div>
      </div>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}
