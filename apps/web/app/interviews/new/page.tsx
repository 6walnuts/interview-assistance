"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";

const FOCUS_BY_TYPE: Record<string, string[]> = {
  coding: ["hash-map", "sliding-window", "binary-search", "tree", "dynamic-programming"],
  system_design: ["rate-limiter", "message-queue", "caching", "sharding", "consistency"],
};

export default function InterviewSetupPage() {
  const router = useRouter();
  const [interviewType, setInterviewType] = useState("coding");
  const [role, setRole] = useState("Backend Engineer");
  const [level, setLevel] = useState("mid");
  const [company, setCompany] = useState("Generic Big Tech");
  const [duration, setDuration] = useState(45);
  const [difficulty, setDifficulty] = useState("medium");
  const [focus, setFocus] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const resp = await api.createInterview({
        interview_type: interviewType, role, level, company_style: company,
        duration_minutes: duration, difficulty, language: "python", focus_areas: focus,
      });
      router.push(`/interviews/${resp.session.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create interview");
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">New mock interview</h1>
      <form onSubmit={onSubmit} className="card mt-6 max-w-2xl space-y-5">
        {error && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <div>
          <label className="label">Interview type</label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { id: "coding", name: "Coding", desc: "Algorithm problem with a live Python sandbox" },
              { id: "system_design", name: "System Design", desc: "Backend design with a text whiteboard" },
            ].map((t) => (
              <button type="button" key={t.id}
                onClick={() => { setInterviewType(t.id); setFocus([]); }}
                className={`rounded-xl border p-4 text-left ${interviewType === t.id ? "border-brand-600 bg-brand-50" : "border-slate-300"}`}>
                <p className="font-medium">{t.name}</p>
                <p className="mt-1 text-xs text-slate-600">{t.desc}</p>
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Role</label>
            <input className="input" value={role} onChange={(e) => setRole(e.target.value)} />
          </div>
          <div>
            <label className="label">Level</label>
            <select className="input" value={level} onChange={(e) => setLevel(e.target.value)}>
              {["junior", "mid", "senior", "staff"].map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Company style</label>
            <select className="input" value={company} onChange={(e) => setCompany(e.target.value)}>
              {["Generic Big Tech", "Google", "Meta", "Amazon", "Microsoft", "OpenAI"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Duration (minutes)</label>
            <select className="input" value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
              {[30, 45, 60].map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Difficulty</label>
            <select className="input" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              {["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Language</label>
            <select className="input" defaultValue="python"><option value="python">Python</option></select>
          </div>
        </div>
        <div>
          <label className="label">Focus areas (optional)</label>
          <div className="flex flex-wrap gap-2">
            {FOCUS_BY_TYPE[interviewType].map((f) => (
              <button type="button" key={f}
                onClick={() => setFocus(focus.includes(f) ? focus.filter((x) => x !== f) : [...focus, f])}
                className={`rounded-full border px-3 py-1 text-sm ${focus.includes(f) ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-600"}`}>
                {f}
              </button>
            ))}
          </div>
        </div>
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? "Preparing your interviewer…" : "Start interview"}
        </button>
      </form>
    </AppShell>
  );
}
