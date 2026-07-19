"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";

const MODULES = [
  { name: "Learn", desc: "AI Coach explains every interview topic at your level, from arrays to LLM serving." },
  { name: "Practice", desc: "Daily drills, quizzes and flashcards targeted at your weakest skills." },
  { name: "Interview", desc: "Realistic mock interviews with a stage-driven AI interviewer and a real code sandbox." },
  { name: "Review", desc: "An independent scoring agent grades you like a bar raiser — with evidence." },
  { name: "Progress", desc: "Mastery scores, score trends and readiness tracking toward your target role." },
];

export default function LandingPage() {
  const { t } = useI18n();
  return (
    <div className="min-h-screen bg-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <span className="text-lg font-bold text-brand-700">AI Interview Coach</span>
        <div className="flex gap-2">
          <Link href="/login" className="btn-secondary">{t("Sign in")}</Link>
          <Link href="/register" className="btn-primary">{t("Start free")}</Link>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-4 py-20 text-center">
        <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
          {t("Mock interviews that turn into a")}<br />
          <span className="text-brand-600">{t("personalized study plan")}</span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600">
          {t("Learn → practice → mock interview → automatic scoring → review → new plan. The loop that most interview tools are missing.")}
        </p>
        <Link href="/register" className="btn-primary mt-8 inline-block px-8 py-3 text-base">
          {t("Start your free mock interview")}
        </Link>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-4 pb-16 sm:grid-cols-2 lg:grid-cols-5">
        {MODULES.map((m) => (
          <div key={m.name} className="card">
            <h3 className="font-semibold text-brand-700">{m.name}</h3>
            <p className="mt-2 text-sm text-slate-600">{m.desc}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-4 pb-24 lg:grid-cols-2">
        <div className="card">
          <h3 className="font-semibold">Example interview report</h3>
          <div className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between"><span>Hire signal</span><span className="font-semibold text-amber-600">lean_hire</span></div>
            <div className="flex justify-between"><span>problem_solving</span><span>4 / 5</span></div>
            <div className="flex justify-between"><span>correctness</span><span>3 / 5</span></div>
            <div className="flex justify-between"><span>testing</span><span className="text-red-600">2 / 5</span></div>
            <p className="pt-2 text-slate-600">
              “Did not test edge cases before submitting; could not explain Kafka offset management.”
            </p>
          </div>
        </div>
        <div className="card">
          <h3 className="font-semibold">…automatically becomes a study plan</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            <li>1. Learn the core concepts of idempotency</li>
            <li>2. Complete 5 edge-case testing drills</li>
            <li>3. Pass the Kafka offset quiz</li>
            <li>4. Design a consumer failure-recovery flow</li>
            <li>5. Streaming-system mock interview in 3 days</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
