"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const FOCUS_BY_TYPE: Record<string, string[]> = {
  coding: ["hash-map", "sliding-window", "binary-search", "tree", "dynamic-programming"],
  system_design: ["rate-limiter", "message-queue", "caching", "sharding", "consistency"],
};

export default function InterviewSetupPage() {
  return (
    <Suspense>
      <InterviewSetupForm />
    </Suspense>
  );
}

function InterviewSetupForm() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const [interviewType, setInterviewType] = useState(params.get("type") ?? "coding");
  const [role, setRole] = useState("Backend Engineer");
  const [level, setLevel] = useState("mid");
  const [company, setCompany] = useState("Generic Big Tech");
  const [duration, setDuration] = useState(45);
  const [difficulty, setDifficulty] = useState("medium");
  const [language, setLanguage] = useState("python");
  const [focus, setFocus] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Question picked from the bank browser (?question_id=...&title=...)
  const [questionId, setQuestionId] = useState<string | null>(params.get("question_id"));
  const questionTitle = params.get("title");
  // Resume editing (used by the interviewer to probe real experience).
  const [resume, setResume] = useState("");
  const [showResume, setShowResume] = useState(false);
  const [resumeLoaded, setResumeLoaded] = useState(false);

  useEffect(() => {
    api.getProfile()
      .then(({ profile }) => {
        setResume(profile.resume_text ?? "");
        setResumeLoaded(true);
      })
      .catch(() => setResumeLoaded(true));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (resumeLoaded) {
        await api.updateProfile({ resume_text: resume }).catch(() => undefined);
      }
      const resp = await api.createInterview({
        interview_type: interviewType, role, level, company_style: company,
        duration_minutes: duration, difficulty, language, focus_areas: focus,
        question_id: questionId,
      });
      router.push(`/interviews/${resp.session.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create interview");
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">{t("New mock interview")}</h1>
      <form onSubmit={onSubmit} className="card mt-6 max-w-2xl space-y-5">
        {error && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        {questionId && (
          <div className="flex items-center justify-between rounded-lg bg-brand-50 p-3 text-sm">
            <span className="text-brand-800">
              📌 {t("Selected question")}: <span className="font-medium">{questionTitle ?? questionId}</span>
            </span>
            <button type="button" className="text-xs text-brand-600 hover:text-brand-800"
              onClick={() => setQuestionId(null)}>
              ✕ {t("Use random question instead")}
            </button>
          </div>
        )}
        <div>
          <label className="label">{t("Interview type")}</label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { id: "coding", name: "Coding", desc: "Algorithm problem with a live Python sandbox" },
              { id: "system_design", name: "System Design", desc: "Backend design with a text whiteboard" },
            ].map((ty) => (
              <button type="button" key={ty.id}
                onClick={() => { setInterviewType(ty.id); setFocus([]); }}
                className={`rounded-xl border p-4 text-left ${interviewType === ty.id ? "border-brand-600 bg-brand-50" : "border-slate-300"}`}>
                <p className="font-medium">{t(ty.name)}</p>
                <p className="mt-1 text-xs text-slate-600">{t(ty.desc)}</p>
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">{t("Role")}</label>
            <input className="input" value={role} onChange={(e) => setRole(e.target.value)} />
          </div>
          <div>
            <label className="label">{t("Level")}</label>
            <select className="input" value={level} onChange={(e) => setLevel(e.target.value)}>
              {["junior", "mid", "senior", "staff"].map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="label">{t("Company style")}</label>
            <select className="input" value={company} onChange={(e) => setCompany(e.target.value)}>
              {["Generic Big Tech", "Google", "Meta", "Amazon", "Microsoft", "OpenAI"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="label">{t("Duration (minutes)")}</label>
            <select className="input" value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
              {[30, 45, 60].map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="label">{t("Difficulty")}</label>
            <select className="input" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              {["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="label">{t("Language")}</label>
            <select className="input" value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="go">Go</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
            </select>
          </div>
        </div>
        <div>
          <label className="label">{t("Focus areas (optional)")}</label>
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
        <div>
          <button type="button" className="text-sm text-brand-600 hover:text-brand-800"
            onClick={() => setShowResume((v) => !v)}>
            {showResume ? "▾" : "▸"} {t("Resume (optional — the interviewer will probe your experience)")}
          </button>
          {showResume && (
            <textarea
              className="input mt-2 h-28 resize-none text-sm"
              placeholder={t("Paste your resume as plain text…")}
              value={resume}
              onChange={(e) => setResume(e.target.value)}
            />
          )}
        </div>
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? t("Preparing your interviewer…") : t("Start interview")}
        </button>
      </form>
    </AppShell>
  );
}
