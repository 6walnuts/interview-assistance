"use client";

import { useEffect } from "react";

const RELOAD_GUARD_KEY = "aic_chunk_reload_at";

/**
 * Self-heal stale-chunk states: after a deploy/rebuild the browser can hold
 * an old page manifest and fail to load renamed chunks (ChunkLoadError,
 * often with a /_next/undefined URL). One reload fetches the fresh manifest.
 * A session guard prevents reload loops if the error is genuine.
 */
export default function ChunkErrorRecovery() {
  useEffect(() => {
    const maybeRecover = (message: string) => {
      if (!/ChunkLoadError|Loading chunk .+ failed/i.test(message)) return;
      try {
        const last = Number(sessionStorage.getItem(RELOAD_GUARD_KEY) ?? 0);
        if (Date.now() - last < 30_000) return;
        sessionStorage.setItem(RELOAD_GUARD_KEY, String(Date.now()));
      } catch {
        /* storage unavailable — still try one reload */
      }
      window.location.reload();
    };
    const onError = (e: ErrorEvent) => maybeRecover(e.message ?? "");
    const onRejection = (e: PromiseRejectionEvent) => {
      const reason = e.reason as { name?: string; message?: string } | undefined;
      maybeRecover(`${reason?.name ?? ""} ${reason?.message ?? String(e.reason ?? "")}`);
    };
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);
  return null;
}
