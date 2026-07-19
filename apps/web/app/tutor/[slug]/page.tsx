"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Execution, Topic } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { useSpeaker, useVoiceInput } from "@/lib/voice";
import { startRealtimeCall, type RealtimeConnection } from "@/lib/realtime";
import SpeedSelect from "@/components/SpeedSelect";

const MonacoEditor = dynamic(
  async () => {
    const { loader, default: Editor } = await import("@monaco-editor/react");
    // Absolute origin so Monaco's language workers can fetch their modules
    // from inside a Worker context (see interview room editor).
    loader.config({ paths: { vs: `${window.location.origin}/monaco/vs` } });
    return Editor;
  },
  { ssr: false }
);

const LANGUAGES: Record<string, { label: string; monaco: string; starter: string }> = {
  python: { label: "Python", monaco: "python", starter: "# Try the exercise here\n" },
  javascript: { label: "JavaScript", monaco: "javascript", starter: "// Try the exercise here\n" },
  go: {
    label: "Go", monaco: "go",
    starter: 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("hello")\n}\n',
  },
  java: {
    label: "Java", monaco: "java",
    starter: "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"hello\");\n    }\n}\n",
  },
  cpp: {
    label: "C++", monaco: "cpp",
    starter: "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    cout << \"hello\" << endl;\n    return 0;\n}\n",
  },
};

type ChatMsg = { role: "user" | "coach"; text: string };
const HISTORY_SENT = 20;

export default function TutorPage() {
  const { t } = useI18n();
  const { slug } = useParams<{ slug: string }>();
  const [topic, setTopic] = useState<Topic | null>(null);
  const [chat, setChat] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [lang, setLang] = useState("python");
  const [code, setCode] = useState(LANGUAGES.python.starter);
  const [execution, setExecution] = useState<Execution | null>(null);
  const [running, setRunning] = useState(false);
  const [snippet, setSnippet] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const startedRef = useRef(false);

  const speaker = useSpeaker(setError);
  const voice = useVoiceInput(
    useCallback((text: string) => setInput((v) => (v ? `${v} ${text}` : text)), []),
    setError
  );

  const storageKey = `aic_tutor_${slug}`;

  // Live voice lesson (WebRTC to OpenAI Realtime, tutor persona, no tools).
  // Transcripts land in the lesson chat, so text and voice share one history.
  const [callState, setCallState] = useState<"idle" | "connecting" | "live">("idle");
  const callRef = useRef<RealtimeConnection | null>(null);

  const persist = useCallback(
    (msgs: ChatMsg[]) => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(msgs));
      } catch {
        /* keep in-memory history */
      }
    },
    [storageKey]
  );

  const ask = useCallback(
    async (message: string, existing: ChatMsg[]) => {
      setBusy(true);
      setError(null);
      const withUser: ChatMsg[] = [...existing, { role: "user", text: message }];
      setChat(withUser);
      persist(withUser);
      setInput("");
      try {
        const history = existing.slice(-HISTORY_SENT).map((m) => ({
          role: m.role === "coach" ? ("assistant" as const) : ("user" as const),
          content: m.text,
        }));
        const resp = await api.coachChat(message, "lesson", slug, history);
        const withReply: ChatMsg[] = [...withUser, { role: "coach", text: resp.reply }];
        setChat(withReply);
        persist(withReply);
        if (resp.code_snippet) setSnippet(resp.code_snippet);
        if (speaker.enabled) speaker.speak(resp.reply);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Tutor unavailable");
      } finally {
        setBusy(false);
      }
    },
    [persist, slug, speaker.enabled, speaker.speak]
  );

  const appendVoiceLine = useCallback(
    (role: "user" | "coach", text: string) => {
      setChat((c) => {
        const next: ChatMsg[] = [...c, { role, text }];
        persist(next);
        return next;
      });
    },
    [persist]
  );

  const toggleCall = useCallback(async () => {
    if (callRef.current) {
      callRef.current.stop();
      callRef.current = null;
      return;
    }
    setError(null);
    try {
      callRef.current = await startRealtimeCall({ topicSlug: slug }, {
        onUserTranscript: (text) => appendVoiceLine("user", text),
        onAssistantTranscript: (text) => appendVoiceLine("coach", text),
        onStateChange: (s) => {
          setCallState(s === "closed" ? "idle" : s);
          if (s === "closed") callRef.current = null;
        },
        onError: setError,
      });
    } catch (e) {
      setCallState("idle");
      setError(e instanceof Error ? e.message : "Voice call failed");
    }
  }, [slug, appendVoiceLine]);

  useEffect(() => () => callRef.current?.stop(), []);

  useEffect(() => {
    api.listTopics()
      .then((all) => setTopic(all.find((tp) => tp.slug === slug) ?? null))
      .catch(() => undefined);
  }, [slug]);

  // Restore the lesson, or auto-start a fresh one.
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    let saved: ChatMsg[] = [];
    try {
      saved = JSON.parse(localStorage.getItem(storageKey) ?? "[]") as ChatMsg[];
    } catch {
      saved = [];
    }
    if (saved.length > 0) setChat(saved);
    else void ask("Start the lesson from the beginning.", []);
  }, [storageKey, ask]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, busy]);

  function switchLang(next: string) {
    const wasStarter = code === (LANGUAGES[lang]?.starter ?? "");
    setLang(next);
    if (wasStarter || !code.trim()) setCode(LANGUAGES[next].starter);
    setExecution(null);
  }

  async function run() {
    setRunning(true);
    setError(null);
    try {
      setExecution(await api.runScratch(code, lang));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Execution failed");
    } finally {
      setRunning(false);
    }
  }

  function shareWithTutor() {
    const output = execution
      ? `\n\nOutput (exit ${execution.exit_code}):\n${execution.stdout || execution.stderr}`.slice(0, 1500)
      : "";
    void ask(`Here is my ${LANGUAGES[lang].label} attempt:\n\`\`\`${lang}\n${code}\n\`\`\`${output}`, chat);
  }

  function restartLesson() {
    if (!window.confirm(t("Restart this lesson? The current conversation will be cleared."))) return;
    callRef.current?.stop();
    callRef.current = null;
    persist([]);
    setChat([]);
    void ask("Start the lesson from the beginning.", []);
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <div className="flex items-center gap-3">
          <Link href="/learn" className="text-sm text-slate-500 hover:text-slate-700">← {t("Learn")}</Link>
          <span className="font-semibold text-brand-700">{t("Tutor")}{topic ? ` — ${topic.name}` : ""}</span>
          {topic && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">D{topic.difficulty}</span>}
        </div>
        <div className="flex items-center gap-2">
          <button
            className={`rounded-full border px-3 py-1 text-xs ${
              callState === "live"
                ? "animate-pulse border-red-600 bg-red-50 font-semibold text-red-700"
                : "border-slate-300 text-slate-500"
            }`}
            onClick={toggleCall}
            disabled={callState === "connecting"}
            title={t("Talk to the tutor in a live voice call — everything is transcribed into the lesson")}
          >
            {callState === "live" ? `📞 ${t("Hang up")}` : callState === "connecting" ? t("Connecting…") : `📞 ${t("Voice call")}`}
          </button>
          <button
            className={`rounded-full border px-3 py-1 text-xs ${speaker.enabled ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-500"}`}
            onClick={() => speaker.setEnabled(!speaker.enabled)}
            title={t("Read the tutor's replies aloud")}
          >
            {speaker.enabled ? "🔊" : "🔇"} {t("Auto-read")}
          </button>
          <SpeedSelect rate={speaker.rate} onChange={speaker.setRate} />
          <button className="btn-secondary !py-1 text-xs" onClick={restartLesson}>{t("Restart lesson")}</button>
          <Link href={`/quiz/${slug}`} className="btn-primary !py-1 text-xs">{t("Chapter quiz →")}</Link>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: lesson chat */}
        <div className="flex w-1/2 flex-col border-r border-slate-200 bg-white">
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {chat.map((m, i) => (
              <div key={i} className={`max-w-[90%] whitespace-pre-wrap rounded-xl px-3 py-2 text-sm ${
                m.role === "coach" ? "bg-slate-100" : "ml-auto bg-brand-50"}`}>
                {m.text}
              </div>
            ))}
            {busy && <p className="text-xs text-slate-400">{t("Tutor is thinking…")}</p>}
            <div ref={bottomRef} />
          </div>
          {error && <p className="mx-3 mb-1 rounded bg-red-50 px-2 py-1 text-xs text-red-700">{error}</p>}
          <div className="border-t border-slate-200 p-3">
            <textarea
              className="input h-16 resize-none"
              placeholder={t("Answer the tutor… (Enter to send, Shift+Enter for newline)")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim() && !busy) void ask(input, chat);
                }
              }}
            />
            <div className="mt-2 flex gap-2">
              <button className="btn-primary" disabled={busy || !input.trim()} onClick={() => void ask(input, chat)}>
                {t("Send")}
              </button>
              <button
                className={voice.recording ? "rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white" : "btn-secondary"}
                disabled={busy || voice.transcribing}
                onClick={voice.toggle}
                title={voice.recording ? t("Stop recording") : t("Voice input")}
              >
                {voice.recording ? `⏹ ${t("Stop recording")}` : voice.transcribing ? t("Transcribing…") : "🎙"}
              </button>
              <button
                className="btn-secondary"
                disabled={busy}
                title={t("Ask for a hint on the current exercise")}
                onClick={() => void ask("I'm stuck — give me a hint for the current exercise, with a short code skeleton (not the full answer).", chat)}
              >
                💡 {t("Hint")}
              </button>
            </div>
          </div>
        </div>

        {/* Right: multi-language scratchpad */}
        <div className="flex w-1/2 flex-col">
          <div className="flex items-center justify-between border-b border-slate-200 bg-white px-3 py-2">
            <span className="text-sm font-medium text-slate-600">{t("Practice editor")}</span>
            <select className="input !w-40 !py-1 text-sm" value={lang} onChange={(e) => switchLang(e.target.value)}>
              {Object.entries(LANGUAGES).map(([id, l]) => <option key={id} value={id}>{l.label}</option>)}
            </select>
          </div>
          {snippet && (
            <div className="border-b border-amber-200 bg-amber-50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-amber-700">💡 {t("Hint")}</span>
                <div className="flex gap-2">
                  <button
                    className="rounded bg-amber-600 px-2 py-0.5 text-xs font-medium text-white hover:bg-amber-700"
                    onClick={() => {
                      const starter = LANGUAGES[lang]?.starter ?? "";
                      setCode((c) => (c === starter || !c.trim() ? snippet : `${c}\n\n${snippet}`));
                    }}
                  >
                    {t("Insert into editor")}
                  </button>
                  <button className="text-xs text-amber-600 hover:text-amber-800" onClick={() => setSnippet(null)}>
                    ✕ {t("Dismiss")}
                  </button>
                </div>
              </div>
              <pre className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap font-mono text-xs text-amber-900">{snippet}</pre>
            </div>
          )}
          <div className="flex-1">
            <MonacoEditor
              language={LANGUAGES[lang].monaco}
              value={code}
              onChange={(v) => setCode(v ?? "")}
              options={{ minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false }}
            />
          </div>
          <div className="border-t border-slate-200 bg-white p-3">
            <div className="flex gap-2">
              <button className="btn-secondary" disabled={running} onClick={run}>
                {running ? t("Running…") : t("Run Code")}
              </button>
              <button className="btn-primary" disabled={busy || running} onClick={shareWithTutor}>
                {t("Share with tutor")}
              </button>
            </div>
            {execution && (
              <div className="mt-2 max-h-36 overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100">
                <p className="text-slate-400">exit {execution.exit_code} · {execution.duration_ms}ms</p>
                {execution.stdout && <pre className="mt-1 whitespace-pre-wrap">{execution.stdout}</pre>}
                {execution.stderr && <pre className="mt-1 whitespace-pre-wrap text-red-300">{execution.stderr}</pre>}
                {execution.timed_out && <p className="text-amber-400">Execution timed out.</p>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
