"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { Report, Task } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const SIGNAL_COLORS: Record<string, string> = {
  strong_hire: "bg-green-600", hire: "bg-green-500", lean_hire: "bg-lime-500",
  mixed: "bg-amber-500", lean_no_hire: "bg-orange-500", no_hire: "bg-red-500",
  strong_no_hire: "bg-red-700",
};

export default function ReportPage() {
  const { t } = useI18n();
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [notGenerated, setNotGenerated] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getReport(id)
      .then(setReport)
      .catch((e) => {
        // 404 = the interview ended without scoring; offer to generate now.
        if (e instanceof ApiError && e.status === 404) setNotGenerated(true);
        else setError(e instanceof Error ? e.message : "Failed to load report");
      });
    api.listTasks().then((all) => setTasks(all.filter((t) => t.source_session_id === id)))
      .catch(() => undefined);
  }, [id]);

  async function generateNow() {
    setGenerating(true);
    setError(null);
    try {
      await api.endInterview(id, true);
      setReport(await api.getReport(id));
      setNotGenerated(false);
      api.listTasks().then((all) => setTasks(all.filter((t) => t.source_session_id === id)))
        .catch(() => undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  }

  if (error) return <AppShell><p className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p></AppShell>;
  if (notGenerated) {
    return (
      <AppShell>
        <div className="card mx-auto mt-10 max-w-md text-center">
          <h1 className="text-xl font-bold">{t("No report yet")}</h1>
          <p className="mt-2 text-sm text-slate-600">
            {t("This interview ended without scoring. Generate the report now to get your scores and study plan.")}
          </p>
          <button className="btn-primary mt-4" onClick={generateNow} disabled={generating}>
            {generating ? t("Generating report…") : t("Generate report")}
          </button>
        </div>
      </AppShell>
    );
  }
  if (!report) return <AppShell><p className="text-slate-500">{t("Generating report…")}</p></AppShell>;

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("Interview report")}</h1>
        <Link href="/tasks" className="btn-primary">{t("Start your study plan")}</Link>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="card text-center">
          <p className="text-sm text-slate-500">{t("Overall score")}</p>
          <p className="mt-1 text-4xl font-bold">{report.overall_score.toFixed(1)}<span className="text-lg text-slate-400"> / 5</span></p>
        </div>
        <div className="card text-center">
          <p className="text-sm text-slate-500">{t("Hire signal")}</p>
          <span className={`mt-2 inline-block rounded-full px-4 py-1 font-semibold text-white ${SIGNAL_COLORS[report.hire_signal] ?? "bg-slate-500"}`}>
            {report.hire_signal.replaceAll("_", " ")}
          </span>
        </div>
        <div className="card text-center">
          <p className="text-sm text-slate-500">{t("Level assessment")}</p>
          <p className="mt-2 font-medium">{report.level_assessment || "—"}</p>
        </div>
      </div>

      <div className="card mt-4">
        <h2 className="font-semibold">{t("Summary")}</h2>
        <p className="mt-2 text-sm text-slate-700">{report.interview_summary}</p>
      </div>

      <div className="card mt-4">
        <h2 className="font-semibold">{t("Dimension scores")}</h2>
        <div className="mt-3 space-y-2">
          {Object.entries(report.scores).map(([dim, score]) => (
            <div key={dim} className="flex items-center gap-3 text-sm">
              <span className="w-56 shrink-0 text-slate-600">{dim.replaceAll("_", " ")}</span>
              <div className="h-2 flex-1 rounded-full bg-slate-100">
                <div className={`h-2 rounded-full ${score >= 4 ? "bg-green-500" : score >= 3 ? "bg-brand-500" : "bg-red-500"}`}
                  style={{ width: `${(score / 5) * 100}%` }} />
              </div>
              <span className="w-8 text-right font-medium">{score}/5</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <ListCard title={t("Strengths")} items={report.strengths} tone="text-green-700" />
        <ListCard title={t("Weaknesses")} items={report.weaknesses} tone="text-red-700" />
        <ListCard title={t("Key mistakes")} items={report.key_mistakes} tone="text-red-700" />
        <ListCard title={t("Missed opportunities")} items={report.missed_opportunities} tone="text-amber-700" />
        <ListCard title={t("Ideal answer outline")} items={report.ideal_answer_outline} tone="text-slate-700" />
        <ListCard title={t("Evidence")} items={report.evidence} tone="text-slate-500" />
      </div>

      <div className="card mt-4">
        <h2 className="font-semibold">{t("Your auto-generated study plan")}</h2>
        {tasks.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">{t("No tasks generated for this session.")}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {tasks.map((t, i) => (
              <li key={t.id} className="flex items-start gap-3 rounded-lg border border-slate-200 p-3 text-sm">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">{i + 1}</span>
                <div>
                  <p className="font-medium">{t.title}</p>
                  <p className="text-slate-600">{t.description}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
}

function ListCard({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  return (
    <div className="card">
      <h2 className="font-semibold">{title}</h2>
      <ul className={`mt-2 list-inside list-disc space-y-1 text-sm ${tone}`}>
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
    </div>
  );
}
