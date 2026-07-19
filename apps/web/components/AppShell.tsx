"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, setToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/learn", label: "Learn" },
  { href: "/practice", label: "Practice" },
  { href: "/interviews/new", label: "Mock Interview" },
  { href: "/tasks", label: "Tasks" },
  { href: "/progress", label: "Progress" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [localMode, setLocalMode] = useState(false);

  useEffect(() => {
    api.health().then((h) => setLocalMode(h.local_mode)).catch(() => undefined);
  }, []);

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/dashboard" className="text-lg font-bold text-brand-700">
            AI Interview Coach
          </Link>
          <nav className="flex items-center gap-1">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-lg px-3 py-1.5 text-sm ${
                  pathname.startsWith(item.href)
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {item.label}
              </Link>
            ))}
            {localMode ? (
              <span className="ml-2 rounded-lg bg-slate-100 px-3 py-1.5 text-sm text-slate-500">
                Local mode
              </span>
            ) : (
              <button
                className="ml-2 rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
                onClick={() => {
                  setToken(null);
                  router.push("/login");
                }}
              >
                Sign out
              </button>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
