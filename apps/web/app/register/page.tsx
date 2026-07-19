"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, setToken } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  // In single-user local mode there is no auth — go straight to the app.
  useEffect(() => {
    api.health().then((h) => h.local_mode && router.replace("/dashboard")).catch(() => undefined);
  }, [router]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const resp = await api.register(email, password, name);
      setToken(resp.access_token);
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={onSubmit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold">Create your account</h1>
        {error && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <div>
          <label className="label">Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="label">Password (min 8 chars)</label>
          <input className="input" type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Creating…" : "Start free"}</button>
        <p className="text-center text-sm text-slate-600">
          Have an account? <Link className="text-brand-600" href="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
