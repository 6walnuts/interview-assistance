"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import type { Level } from "@/lib/types";

const LEVELS: Level[] = ["junior", "mid", "senior", "staff"];
const COMPANIES = ["Google", "Meta", "Amazon", "Microsoft", "OpenAI", "Other"];
const AREAS = [
  "arrays", "dynamic-programming", "system-design", "api-design", "caching",
  "kafka", "kubernetes", "concurrency", "llm-serving",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [targetRole, setTargetRole] = useState("Backend Engineer");
  const [currentLevel, setCurrentLevel] = useState<Level>("mid");
  const [targetLevel, setTargetLevel] = useState<Level>("senior");
  const [companies, setCompanies] = useState<string[]>([]);
  const [interviewDate, setInterviewDate] = useState("");
  const [weeklyHours, setWeeklyHours] = useState(8);
  const [language, setLanguage] = useState("python");
  const [strengths, setStrengths] = useState<string[]>([]);
  const [weaknesses, setWeaknesses] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(list: string[], setList: (v: string[]) => void, value: string) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.updateProfile({
        target_role: targetRole,
        current_level: currentLevel,
        target_level: targetLevel,
        target_companies: companies,
        interview_date: interviewDate || null,
        weekly_hours: weeklyHours,
        preferred_language: language,
        strengths,
        weaknesses,
        onboarding_completed: true,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Set up your prep plan</h1>
      <p className="mt-1 text-slate-600">This calibrates your coach, interviewer and study plan.</p>
      <form onSubmit={onSubmit} className="card mt-6 space-y-5">
        {error && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <div>
          <label className="label">Target role</label>
          <input className="input" value={targetRole} onChange={(e) => setTargetRole(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Current level</label>
            <select className="input" value={currentLevel} onChange={(e) => setCurrentLevel(e.target.value as Level)}>
              {LEVELS.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Target level</label>
            <select className="input" value={targetLevel} onChange={(e) => setTargetLevel(e.target.value as Level)}>
              {LEVELS.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="label">Target companies</label>
          <div className="flex flex-wrap gap-2">
            {COMPANIES.map((c) => (
              <button type="button" key={c} onClick={() => toggle(companies, setCompanies, c)}
                className={`rounded-full border px-3 py-1 text-sm ${companies.includes(c) ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-600"}`}>
                {c}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Interview date (optional)</label>
            <input className="input" type="date" value={interviewDate} onChange={(e) => setInterviewDate(e.target.value)} />
          </div>
          <div>
            <label className="label">Hours per week</label>
            <input className="input" type="number" min={1} max={80} value={weeklyHours}
              onChange={(e) => setWeeklyHours(Number(e.target.value))} />
          </div>
        </div>
        <div>
          <label className="label">Preferred language</label>
          <select className="input" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="python">Python</option>
          </select>
        </div>
        <div>
          <label className="label">Strong areas</label>
          <div className="flex flex-wrap gap-2">
            {AREAS.map((a) => (
              <button type="button" key={a} onClick={() => toggle(strengths, setStrengths, a)}
                className={`rounded-full border px-3 py-1 text-sm ${strengths.includes(a) ? "border-green-600 bg-green-50 text-green-700" : "border-slate-300 text-slate-600"}`}>
                {a}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="label">Weak areas</label>
          <div className="flex flex-wrap gap-2">
            {AREAS.map((a) => (
              <button type="button" key={a} onClick={() => toggle(weaknesses, setWeaknesses, a)}
                className={`rounded-full border px-3 py-1 text-sm ${weaknesses.includes(a) ? "border-red-600 bg-red-50 text-red-700" : "border-slate-300 text-slate-600"}`}>
                {a}
              </button>
            ))}
          </div>
        </div>
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Saving…" : "Finish setup"}</button>
      </form>
    </div>
  );
}
