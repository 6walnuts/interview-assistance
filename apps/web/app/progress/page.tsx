"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import type { InterviewHistoryItem, ProgressOverview, Skill } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

export default function ProgressPage() {
  const { t } = useI18n();
  const [overview, setOverview] = useState<ProgressOverview | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [history, setHistory] = useState<InterviewHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.progress(), api.skills(), api.interviewHistory()])
      .then(([o, s, h]) => { setOverview(o); setSkills(s); setHistory(h); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">{t("Progress")}</h1>
      {error && <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}

      <div className="mt-6 grid gap-4 sm:grid-cols-4">
        <Stat label={t("Streak")} value={overview ? `${overview.streak_days}d` : "—"} />
        <Stat label={t("Tasks completed")} value={overview?.tasks_completed ?? "—"} />
        <Stat label={t("Interviews")} value={overview?.interviews_completed ?? "—"} />
        <Stat label={t("Recent avg score")} value={overview?.avg_recent_score ?? "—"} />
      </div>

      <div className="card mt-6">
        <h2 className="font-semibold">{t("Skill mastery")}</h2>
        {skills.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">{t("Complete tasks and interviews to build your skill map.")}</p>
        ) : (
          <div className="mt-3 space-y-2">
            {skills.map((s) => (
              <div key={s.topic_slug} className="flex items-center gap-3 text-sm">
                <span className="w-52 shrink-0 text-slate-600">{s.name}</span>
                <span className="w-28 shrink-0 text-xs text-slate-400">{s.category}</span>
                <div className="h-2 flex-1 rounded-full bg-slate-100">
                  <div className="h-2 rounded-full bg-brand-500" style={{ width: `${s.mastery_score}%` }} />
                </div>
                <span className="w-10 text-right font-medium">{s.mastery_score}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card mt-6">
        <h2 className="font-semibold">{t("Interview history")}</h2>
        {history.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">{t("No interviews yet.")}</p>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-400">
                <th className="py-2">{t("Date")}</th><th>{t("Type")}</th><th>{t("Role")}</th><th>{t("Score")}</th><th>{t("Signal")}</th><th></th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.session_id} className="border-b border-slate-100">
                  <td className="py-2">{h.ended_at ? new Date(h.ended_at).toLocaleDateString() : t("in progress")}</td>
                  <td>{h.interview_type}</td>
                  <td>{h.role} ({h.level})</td>
                  <td>{h.overall_score ?? "—"}</td>
                  <td>{h.hire_signal?.replaceAll("_", " ") ?? "—"}</td>
                  <td>
                    {h.overall_score !== null && (
                      <Link className="text-brand-600" href={`/interviews/${h.session_id}/report`}>{t("Report")}</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
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
