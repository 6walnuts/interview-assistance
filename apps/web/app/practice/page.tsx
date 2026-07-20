"use client";

import Link from "next/link";
import AppShell from "@/components/AppShell";
import { useI18n } from "@/lib/i18n";

const DRILLS = [
  { name: "Daily Drill", desc: "A 15-minute mixed drill from your weakest topics.", href: "/learn", time: "15 min" },
  { name: "Coding Practice", desc: "Take a focused coding mock interview instead.", href: "/interviews/new", time: "30 min" },
  { name: "System Design Mini Drill", desc: "One design prompt with coach feedback.", href: "/learn", time: "30 min" },
  { name: "Quiz", desc: "Topic quizzes via the coach (quiz mode).", href: "/learn", time: "5 min" },
  { name: "Flashcards", desc: "Rapid-fire concept cards via the coach.", href: "/learn", time: "5 min" },
  { name: "Mistake Review", desc: "Re-test the mistakes from your last interviews.", href: "/tasks", time: "15 min" },
  { name: "Resume BQ Battle", desc: "Watch an interviewer AI grill a candidate AI on your resume — with model STAR answers.", href: "/duo/bq", time: "15 min" },
  { name: "CN Canon Drill", desc: "The domestic interview canon: JVM, MySQL, Redis, networking, OS — lessons, quizzes and AI dialogues per topic.", href: "/learn?category=bagu", time: "15 min" },
];

export default function PracticePage() {
  const { t } = useI18n();
  return (
    <AppShell>
      <h1 className="text-2xl font-bold">{t("Practice")}</h1>
      <p className="mt-1 text-slate-600">{t("Short, targeted sessions — 5, 15 or 30 minutes.")}</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {DRILLS.map((d) => (
          <Link key={d.name} href={d.href} className="card transition hover:border-brand-500">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">{t(d.name)}</h2>
              <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{d.time.replace("min", t("min"))}</span>
            </div>
            <p className="mt-2 text-sm text-slate-600">{t(d.desc)}</p>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}
