"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Execution, InterviewDetail, Message } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { useSpeaker, useVoiceInput } from "@/lib/voice";
import { startRealtimeCall, type RealtimeConnection } from "@/lib/realtime";
import SpeedSelect from "@/components/SpeedSelect";

const MonacoEditor = dynamic(
  async () => {
    const { loader, default: Editor } = await import("@monaco-editor/react");
    // Self-hosted Monaco assets (copied to public/ by scripts/copy-monaco.mjs)
    // instead of the default CDN, so the editor works offline / behind proxies.
    // The origin must be absolute: language workers (e.g. tsWorker for JS)
    // fetch from inside a Worker where a bare "/monaco/vs" path cannot resolve.
    loader.config({ paths: { vs: `${window.location.origin}/monaco/vs` } });
    return Editor;
  },
  { ssr: false }
);

const STAGES = [
  "introduction", "question_presentation", "clarification", "approach", "deep_dive",
  "coding", "testing", "complexity", "optimization", "follow_up", "candidate_questions", "finish",
];

// Per-language editor setup. `harness: true` languages run the question's test
// cases automatically; the others run as a complete program (CoderPad style).
const LANGUAGE_SETUP: Record<string, { monaco: string; starter: string; harness: boolean }> = {
  python: { monaco: "python", harness: true, starter: "# Write your solution here\n" },
  javascript: {
    monaco: "javascript", harness: true,
    starter: "// Write your solution here (keep the function name from the problem)\n",
  },
  go: {
    monaco: "go", harness: false,
    starter: `package main

import "fmt"

// Tests are not auto-run for Go — call your solution from main and print results.
func main() {
\tfmt.Println("hello")
}
`,
  },
  java: {
    monaco: "java", harness: false,
    starter: `// Class must be named Main. Tests are not auto-run for Java —
// call your solution from main and print results.
public class Main {
    public static void main(String[] args) {
        System.out.println("hello");
    }
}
`,
  },
  cpp: {
    monaco: "cpp", harness: false,
    starter: `#include <bits/stdc++.h>
using namespace std;

// Tests are not auto-run for C++ — call your solution from main and print results.
int main() {
    cout << "hello" << endl;
    return 0;
}
`,
  },
};

export default function InterviewRoomPage() {
  const { t } = useI18n();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<InterviewDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [stage, setStage] = useState("introduction");
  const [input, setInput] = useState("");
  const [code, setCode] = useState("# Write your solution here\n");
  // Editor language: starts from the session config, switchable mid-interview.
  const [editorLang, setEditorLang] = useState<string | null>(null);
  const [design, setDesign] = useState("");
  const [execution, setExecution] = useState<Execution | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [running, setRunning] = useState(false);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const speaker = useSpeaker(setError);
  const voice = useVoiceInput(
    useCallback((text: string) => setInput((v) => (v ? `${v} ${text}` : text)), []),
    setError
  );

  // Live voice call (WebRTC to OpenAI Realtime). Transcript lines land in the
  // chat and are persisted server-side so the Scoring Agent grades them too.
  const [callState, setCallState] = useState<"idle" | "connecting" | "live">("idle");
  const callRef = useRef<RealtimeConnection | null>(null);
  const stageRef = useRef(stage);
  stageRef.current = stage;

  const addVoiceLine = useCallback(
    (role: "candidate" | "interviewer", text: string) => {
      setMessages((m) => [...m, {
        id: `voice-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        role, content: text, stage: stageRef.current, created_at: new Date().toISOString(),
      }]);
      api.addVoiceTranscript(id, role, text).catch(() => undefined);
    },
    [id]
  );

  const toggleCall = useCallback(async () => {
    if (callRef.current) {
      callRef.current.stop();
      callRef.current = null;
      return;
    }
    setError(null);
    try {
      callRef.current = await startRealtimeCall({ interviewId: id }, {
        onUserTranscript: (text) => addVoiceLine("candidate", text),
        onAssistantTranscript: (text) => addVoiceLine("interviewer", text),
        onToolCall: async (name, args) => {
          // The voice interviewer drives the stage machine through here.
          const resp = await api.runVoiceTool(id, name, args);
          setStage(resp.current_stage);
          return resp.result;
        },
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
  }, [id, addVoiceLine]);

  useEffect(() => () => callRef.current?.stop(), []);

  // Draft autosave: restore unsent code/design for this session, then persist
  // every edit so a page refresh never loses work.
  const draftsLoaded = useRef(false);
  useEffect(() => {
    const savedCode = localStorage.getItem(`aic_code_${id}`);
    if (savedCode) setCode(savedCode);
    const savedDesign = localStorage.getItem(`aic_design_${id}`);
    if (savedDesign) setDesign(savedDesign);
    draftsLoaded.current = true;
  }, [id]);
  useEffect(() => {
    if (draftsLoaded.current) localStorage.setItem(`aic_code_${id}`, code);
  }, [code, id]);
  useEffect(() => {
    if (draftsLoaded.current) localStorage.setItem(`aic_design_${id}`, design);
  }, [design, id]);

  useEffect(() => {
    api.getInterview(id)
      .then((d) => {
        setDetail(d);
        setMessages(d.messages);
        setStage(d.session.current_stage);
        const setup = LANGUAGE_SETUP[d.session.language] ?? LANGUAGE_SETUP.python;
        setCode((current) =>
          current === LANGUAGE_SETUP.python.starter || current === "# Write your solution here\n"
            ? setup.starter
            : current
        );
        const started = new Date(d.session.started_at).getTime();
        const total = d.session.duration_minutes * 60_000;
        setRemaining(Math.max(0, started + total - Date.now()));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [id]);

  useEffect(() => {
    const timer = setInterval(
      () => setRemaining((r) => (r === null ? null : Math.max(0, r - 1000))),
      1000
    );
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (content: string, action: string) => {
      if (!content.trim() || busy) return;
      setBusy(true);
      setError(null);
      const optimistic: Message = {
        id: `local-${Date.now()}`, role: "candidate", content, stage,
        created_at: new Date().toISOString(),
      };
      setMessages((m) => [...m, optimistic]);
      setInput("");
      try {
        const resp = await api.sendMessage(id, content, action);
        setMessages((m) => [...m, resp.message]);
        setStage(resp.current_stage);
        if (resp.hint_content) setHint(resp.hint_content);
        // Hints are always read aloud — the reply to the hint button is the
        // one message the candidate explicitly asked to hear.
        if (speaker.enabled || action === "request_hint") speaker.speak(resp.message.content);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to send");
      } finally {
        setBusy(false);
      }
    },
    [busy, id, stage, speaker.enabled, speaker.speak]
  );

  const activeLang = editorLang ?? detail?.session.language ?? "python";

  function switchEditorLang(next: string) {
    const currentSetup = LANGUAGE_SETUP[activeLang] ?? LANGUAGE_SETUP.python;
    const untouched = code === currentSetup.starter || !code.trim();
    setEditorLang(next);
    if (untouched) setCode((LANGUAGE_SETUP[next] ?? LANGUAGE_SETUP.python).starter);
    setExecution(null);
  }

  async function runCode(label: "run" | "submit") {
    const lang = activeLang;
    setRunning(true);
    setError(null);
    try {
      const resp = await api.runCode(id, code, label, lang);
      setExecution(resp.execution);
      if (label === "submit") {
        const summary = resp.execution.test_results.length
          ? `Test results: ${resp.execution.test_results.filter((t) => t.passed).length}/${resp.execution.test_results.length} passed.`
          : `Program exited with code ${resp.execution.exit_code}. Output:\n${resp.execution.stdout.slice(0, 500)}`;
        await send(
          `I'm submitting my solution. ${summary}\n\n\`\`\`${lang}\n${code}\n\`\`\``,
          "message"
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Execution failed");
    } finally {
      setRunning(false);
    }
  }

  async function endInterview() {
    if (!window.confirm(t("End the interview?"))) return;
    const wantReport = window.confirm(
      t("Generate your scoring report now? Choose Cancel to end without a report — you can generate it later from the report page.")
    );
    setBusy(true);
    callRef.current?.stop();
    callRef.current = null;
    try {
      if (detail?.session.interview_type === "system_design" && design.trim()) {
        await api.sendMessage(id, `Here is my final design summary:\n${design}`, "message");
      }
      await api.endInterview(id, wantReport);
      router.push(wantReport ? `/interviews/${id}/report` : "/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to end interview");
      setBusy(false);
    }
  }

  if (!detail) {
    return <div className="flex min-h-screen items-center justify-center text-slate-500">
      {error ?? t("Loading interview…")}
    </div>;
  }

  const isCoding = detail.session.interview_type === "coding";
  const minutes = remaining === null ? "--" : Math.floor(remaining / 60_000);
  const seconds = remaining === null ? "--" : String(Math.floor((remaining % 60_000) / 1000)).padStart(2, "0");

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-brand-700">AI Interview Coach</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{detail.session.role} · {detail.session.level}</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            className={`rounded-full border px-3 py-1 text-xs ${
              callState === "live"
                ? "animate-pulse border-red-600 bg-red-50 font-semibold text-red-700"
                : "border-slate-300 text-slate-500"
            }`}
            onClick={toggleCall}
            disabled={callState === "connecting"}
            title={t("Talk to the interviewer in a live voice call — everything is transcribed into the chat")}
          >
            {callState === "live" ? `📞 ${t("Hang up")}` : callState === "connecting" ? t("Connecting…") : `📞 ${t("Voice call")}`}
          </button>
          <button
            className={`rounded-full border px-3 py-1 text-xs ${speaker.enabled ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-500"}`}
            onClick={() => speaker.setEnabled(!speaker.enabled)}
            title={t("Read the interviewer's replies aloud")}
          >
            {speaker.enabled ? "🔊" : "🔇"} {t("Auto-read")}
          </button>
          <SpeedSelect rate={speaker.rate} onChange={speaker.setRate} />
          <span className={`text-sm font-mono ${remaining !== null && remaining < 5 * 60_000 ? "text-red-600" : "text-slate-600"}`}>
            ⏱ {minutes}:{seconds}
          </span>
          <button className="btn-secondary !py-1 text-red-600" onClick={endInterview} disabled={busy}>
            {t("End Interview")}
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: chat + stage */}
        <div className="flex w-1/2 flex-col border-r border-slate-200 bg-white">
          <div className="flex flex-wrap gap-1 border-b border-slate-100 px-3 py-2">
            {STAGES.map((s) => (
              <span key={s} className={`rounded px-1.5 py-0.5 text-[10px] ${s === stage ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-400"}`}>
                {s}
              </span>
            ))}
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((m) => (
              <div key={m.id} className={`max-w-[85%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap ${
                m.role === "interviewer" ? "bg-slate-100" : "ml-auto bg-brand-50"}`}>
                <p className="mb-1 text-[10px] font-semibold uppercase text-slate-400">
                  {m.role === "interviewer" ? t("Interviewer") : t("You")}
                </p>
                {m.content}
              </div>
            ))}
            {busy && <p className="text-xs text-slate-400">{t("Interviewer is typing…")}</p>}
            <div ref={bottomRef} />
          </div>
          {error && <p className="mx-3 mb-1 rounded bg-red-50 px-2 py-1 text-xs text-red-700">{error}</p>}
          <div className="border-t border-slate-200 p-3">
            <textarea
              className="input h-20 resize-none"
              placeholder={t("Talk to your interviewer… (Enter to send, Shift+Enter for newline)")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input, "message");
                }
              }}
            />
            <div className="mt-2 flex gap-2">
              <button className="btn-primary" disabled={busy || !input.trim()} onClick={() => send(input, "message")}>{t("Send")}</button>
              <button
                className={voice.recording ? "rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white" : "btn-secondary"}
                disabled={busy || voice.transcribing}
                onClick={voice.toggle}
                title={voice.recording ? t("Stop recording") : t("Voice input")}
              >
                {voice.recording ? `⏹ ${t("Stop recording")}` : voice.transcribing ? t("Transcribing…") : "🎙"}
              </button>
              <button className="btn-secondary" disabled={busy || !input.trim()} onClick={() => send(input, "ask_clarification")}>{t("Ask Clarification")}</button>
              <button className="btn-secondary" disabled={busy} onClick={() => send(t("Could I get a hint?"), "request_hint")}>{t("Request Hint")}</button>
            </div>
          </div>
        </div>

        {/* Right: question + editor/whiteboard */}
        <div className="flex w-1/2 flex-col">
          <div className="max-h-48 overflow-y-auto border-b border-slate-200 bg-white p-4">
            <h2 className="font-semibold">{detail.question?.title}</h2>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{detail.question?.prompt}</p>
            {detail.question && detail.question.constraints.length > 0 && (
              <ul className="mt-2 list-inside list-disc text-xs text-slate-500">
                {detail.question.constraints.map((c, i) => <li key={i}>{String(c)}</li>)}
              </ul>
            )}
          </div>

          {hint && (
            <div className="border-b border-amber-200 bg-amber-50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-amber-700">💡 {t("Hint")}</span>
                <button className="text-xs text-amber-600 hover:text-amber-800" onClick={() => setHint(null)}>
                  ✕ {t("Dismiss")}
                </button>
              </div>
              <pre className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap font-mono text-xs text-amber-900">{hint}</pre>
            </div>
          )}

          {isCoding ? (
            <>
              <div className="flex-1">
                <MonacoEditor
                  language={(LANGUAGE_SETUP[activeLang] ?? LANGUAGE_SETUP.python).monaco}
                  value={code}
                  onChange={(v) => setCode(v ?? "")}
                  options={{ minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false }}
                />
              </div>
              <div className="border-t border-slate-200 bg-white p-3">
                <div className="flex items-center gap-2">
                  <button className="btn-secondary" disabled={running} onClick={() => runCode("run")}>
                    {running ? t("Running…") : t("Run Code")}
                  </button>
                  <button className="btn-primary" disabled={running} onClick={() => runCode("submit")}>{t("Submit")}</button>
                  <select
                    className="input ml-auto !w-36 !py-1 text-sm"
                    value={activeLang}
                    onChange={(e) => switchEditorLang(e.target.value)}
                    title={t("Switch the editor language")}
                  >
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="go">Go</option>
                    <option value="java">Java</option>
                    <option value="cpp">C++</option>
                  </select>
                </div>
                {execution && (
                  <div className="mt-2 max-h-36 overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100">
                    {execution.test_results.length === 0 && execution.exit_code === 0 && !execution.timed_out && (
                      <p className="text-slate-400">exit 0 · {execution.duration_ms}ms</p>
                    )}
                    {execution.test_results.map((t) => (
                      <p key={t.name} className={t.passed ? "text-green-400" : "text-red-400"}>
                        {t.passed ? "✓" : "✗"} {t.name}{t.detail ? ` — ${t.detail}` : ""}
                      </p>
                    ))}
                    {execution.stdout && <pre className="mt-1 whitespace-pre-wrap">{execution.stdout}</pre>}
                    {execution.stderr && <pre className="mt-1 whitespace-pre-wrap text-red-300">{execution.stderr}</pre>}
                    {execution.timed_out && <p className="text-amber-400">Execution timed out.</p>}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-1 flex-col bg-white p-3">
              <label className="label">{t("Design whiteboard (plain text / markdown)")}</label>
              <textarea
                className="input flex-1 resize-none font-mono text-sm"
                placeholder={"Components:\n- API Gateway\n- ...\n\nData model:\n...\n\nFailure handling:\n..."}
                value={design}
                onChange={(e) => setDesign(e.target.value)}
              />
              <button className="btn-secondary mt-2 self-start" disabled={busy || !design.trim()}
                onClick={() => send(`Here is my current design:\n${design}`, "message")}>
                {t("Share design with interviewer")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
