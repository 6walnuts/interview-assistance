"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Topic } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { useSpeaker } from "@/lib/voice";
import SpeedSelect from "@/components/SpeedSelect";
import ResumeUpload from "@/components/ResumeUpload";

type Speaker = "asker" | "answerer" | "user";
type Turn = { speaker: Speaker; text: string };

const MAX_TURNS = 24;
const END_MARKER = "[END_OF_DIALOGUE]";
// Distinct TTS voices so the dialogue sounds like two people.
const VOICES: Record<Speaker, string> = { asker: "echo", answerer: "coral", user: "alloy" };
const HISTORY_SENT = 16;

export default function DuoPage() {
  return (
    <Suspense>
      <DuoSession />
    </Suspense>
  );
}

function DuoSession() {
  const { t } = useI18n();
  const { slug } = useParams<{ slug: string }>();
  const search = useSearchParams();
  // Optional anchor: run the dialogue around one specific bank question.
  const questionId = search.get("question_id");
  const questionTitle = search.get("title");
  // Special variant: /duo/bq = resume-grounded behavioral sparring match.
  const isBQ = slug === "bq";
  const [topic, setTopic] = useState<Topic | null>(null);
  const [hasResume, setHasResume] = useState<boolean | null>(null);
  // Target JD: gap-analysis fuel for the BQ interviewer.
  const [jd, setJd] = useState("");
  const [showJd, setShowJd] = useState(false);
  const [jdSaved, setJdSaved] = useState(false);
  const [saved, setSaved] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  // Cumulative design whiteboard maintained by the answerer (topic mode).
  const [board, setBoard] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const finishedRef = useRef(false);
  const [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const turnsRef = useRef<Turn[]>([]);
  turnsRef.current = turns;
  const playingRef = useRef(false);
  const busyRef = useRef(false);

  const speaker = useSpeaker(setError);
  const voiceOnRef = useRef(speaker.enabled);
  voiceOnRef.current = speaker.enabled;
  const speakRef = useRef(speaker.speak);
  speakRef.current = speaker.speak;

  useEffect(() => {
    if (isBQ) {
      api.getProfile()
        .then(({ profile }) => {
          setHasResume(Boolean(profile.resume_text?.trim()));
          setJd(profile.target_jd ?? "");
        })
        .catch(() => setHasResume(null));
      return;
    }
    api.listTopics()
      .then((all) => setTopic(all.find((tp) => tp.slug === slug) ?? null))
      .catch(() => undefined);
  }, [slug, isBQ]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, busy]);

  useEffect(() => () => {
    playingRef.current = false;
  }, []);

  // History from the generating persona's point of view: its own past turns
  // are "assistant", everything from the other side (incl. the student) "user".
  const historyFor = useCallback((persona: "asker" | "answerer", all: Turn[]) => {
    return all.slice(0, -1).slice(-HISTORY_SENT).map((turn) => ({
      role: ((persona === "asker") === (turn.speaker === "asker")
        ? "assistant" : "user") as "assistant" | "user",
      content: turn.text,
    }));
  }, []);

  const generateTurn = useCallback(async (): Promise<boolean> => {
    if (busyRef.current || finishedRef.current) return false;
    const all = turnsRef.current;
    if (all.length >= MAX_TURNS) {
      finishedRef.current = true;
      setFinished(true);
      playingRef.current = false;
      setPlaying(false);
      return false;
    }
    const last = all[all.length - 1];
    const persona: "asker" | "answerer" =
      !last || last.speaker === "answerer" ? "asker" : "answerer";
    const message = last
      ? last.text
      : isBQ
        ? "[Begin: ask your first behavioral question grounded in the resume.]"
        : "[Begin the dialogue: ask your first, most fundamental question.]";
    busyRef.current = true;
    setBusy(true);
    setError(null);
    const base: Turn[] = [...all, { speaker: persona, text: "" }];
    setTurns(base);
    try {
      let streamed = "";
      const mode = isBQ
        ? (persona === "asker" ? "bq_asker" : "bq_answerer")
        : (persona === "asker" ? "duo_asker" : "duo_answerer");
      const resp = await api.streamCoachChat(
        message, mode, isBQ ? undefined : slug,
        historyFor(persona, [...all, { speaker: persona, text: "" }]),
        (delta) => {
          streamed += delta;
          const partial = streamed;
          setTurns([...all, { speaker: persona, text: partial }]);
        },
        questionId
      );
      if (persona === "answerer" && resp.code_snippet) setBoard(resp.code_snippet);
      // Termination: explicit end marker from the asker, or (safety net) the
      // two sides starting to echo each other's farewell lines verbatim.
      const ended = resp.reply.includes(END_MARKER);
      const text = resp.reply.replace(END_MARKER, "").trim();
      // Only the other side echoing the previous line verbatim counts as a
      // farewell loop (same-speaker repetition is legitimate in short mocks).
      const looping = all.length >= 1 && text === all[all.length - 1].text;
      setTurns([...all, { speaker: persona, text }]);
      if (ended || looping) {
        finishedRef.current = true;
        setFinished(true);
        playingRef.current = false;
        setPlaying(false);
      }
      if (voiceOnRef.current && text) {
        await speakRef.current(text, { voice: VOICES[persona], waitUntilDone: true });
      }
      return !(ended || looping);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Dialogue failed");
      setTurns(all); // drop the empty bubble
      return false;
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }, [slug, isBQ, questionId, historyFor]);

  const playLoop = useCallback(async () => {
    while (playingRef.current && turnsRef.current.length < MAX_TURNS) {
      const ok = await generateTurn();
      if (!ok) break;
      await new Promise((r) => setTimeout(r, voiceOnRef.current ? 300 : 1400));
    }
    playingRef.current = false;
    setPlaying(false);
  }, [generateTurn]);

  function togglePlay() {
    if (playingRef.current) {
      playingRef.current = false;
      setPlaying(false);
      return;
    }
    playingRef.current = true;
    setPlaying(true);
    void playLoop();
  }

  async function saveJd() {
    try {
      await api.updateProfile({ target_jd: jd });
      setJdSaved(true);
      setTimeout(() => setJdSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save JD");
    }
  }

  function dialogueTitle(): string {
    const date = new Date().toISOString().slice(0, 10);
    return isBQ ? `Resume BQ Battle — ${date}` : `AI Q&A — ${topic?.name ?? slug} — ${date}`;
  }

  function toMarkdown(): string {
    const lines = [`# ${dialogueTitle()}`, ""];
    for (const turn of turnsRef.current) {
      lines.push(`**${roleLabel[turn.speaker].replace(/^[^\s]+\s/, "")}**:`, "", turn.text, "");
    }
    if (board) {
      lines.push("## Whiteboard", "", "```", board, "```", "");
    }
    return lines.join("\n");
  }

  function exportMarkdown() {
    const blob = new Blob([toMarkdown()], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${isBQ ? "bq-battle" : `duo-${slug}`}-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function favorite() {
    try {
      const all = JSON.parse(localStorage.getItem("aic_saved_duos") ?? "[]") as unknown[];
      all.unshift({
        id: `${Date.now()}`,
        title: dialogueTitle(),
        kind: isBQ ? "bq" : slug,
        savedAt: new Date().toISOString(),
        turns: turnsRef.current,
      });
      localStorage.setItem("aic_saved_duos", JSON.stringify(all.slice(0, 50)));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    }
  }

  function restart() {
    playingRef.current = false;
    setPlaying(false);
    speaker.stop();
    finishedRef.current = false;
    setFinished(false);
    setBoard(null);
    setTurns([]);
  }

  async function askMine() {
    if (!input.trim() || busyRef.current) return;
    playingRef.current = false;
    setPlaying(false);
    const all = turnsRef.current;
    const q = input.trim();
    setInput("");
    const withMine: Turn[] = [...all, { speaker: "user", text: q }];
    setTurns(withMine);
    turnsRef.current = withMine;
    await generateTurn(); // last turn is the user question -> answerer replies
  }

  const roleLabel: Record<Speaker, string> = isBQ
    ? { asker: `👔 ${t("Interviewer AI")}`, answerer: `🧑‍💼 ${t("Candidate AI")}`, user: `🙋 ${t("You")}` }
    : { asker: `🤔 ${t("Asker")}`, answerer: `💡 ${t("Answerer")}`, user: `🙋 ${t("You")}` };
  const roleStyle: Record<Speaker, string> = {
    asker: "bg-slate-100",
    answerer: "ml-auto bg-brand-50",
    user: "ml-auto bg-green-50",
  };

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <div className="flex items-center gap-3">
          <Link href="/learn" className="text-sm text-slate-500 hover:text-slate-700">← {t("Learn")}</Link>
          <span className="font-semibold text-brand-700">
            {isBQ ? `⚔️ ${t("Resume BQ Battle")}` : `🎭 ${t("AI × AI Q&A")}${topic ? ` — ${topic.name}` : ""}`}
          </span>
          {questionTitle && (
            <span className="max-w-xs truncate rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700"
              title={questionTitle}>
              📌 {questionTitle}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {turns.length > 0 && (
            <>
              <button className="btn-secondary !py-1 text-xs" onClick={favorite}
                title={t("Save this dialogue to your favorites")}>
                {saved ? `✅ ${t("Saved")}` : `⭐ ${t("Favorite")}`}
              </button>
              <button className="btn-secondary !py-1 text-xs" onClick={exportMarkdown}
                title={t("Download this dialogue as Markdown")}>
                ⬇️ {t("Export")}
              </button>
            </>
          )}
          <Link href="/saved" className="btn-secondary !py-1 text-xs">🗂 {t("Favorites")}</Link>
          {isBQ && (
            <>
              <button
                className={`rounded-full border px-3 py-1 text-xs ${jd.trim() ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-500"}`}
                onClick={() => setShowJd((v) => !v)}
                title={t("Paste the target job description — the interviewer attacks the resume-JD gaps")}
              >
                🎯 JD
              </button>
              <ResumeUpload
                onExtract={() => setHasResume(true)}
                onError={setError}
              />
            </>
          )}
          <button
            className={`rounded-full border px-3 py-1 text-xs ${speaker.enabled ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-500"}`}
            onClick={() => speaker.setEnabled(!speaker.enabled)}
            title={t("Read the dialogue aloud with two voices")}
          >
            {speaker.enabled ? "🔊" : "🔇"} {t("Auto-read")}
          </button>
          <SpeedSelect rate={speaker.rate} onChange={speaker.setRate} />
          <button className="btn-secondary !py-1 text-xs" onClick={restart} disabled={busy && !playing}>
            🔄 {t("Restart")}
          </button>
          {finished && (
            <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
              ✅ {t("Dialogue finished")}
            </span>
          )}
          <button className="btn-primary !py-1 text-xs" onClick={togglePlay}
            disabled={finished || turns.length >= MAX_TURNS}>
            {playing ? `⏸ ${t("Pause")}` : `▶ ${t("Play")}`}
          </button>
        </div>
      </header>

      <div className={`mx-auto flex w-full flex-1 flex-col overflow-hidden px-4 ${board ? "max-w-6xl flex-row gap-4" : "max-w-3xl"}`}>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="flex-1 space-y-3 overflow-y-auto py-4">
          {isBQ && showJd && (
            <div className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
              <p className="text-xs font-semibold text-slate-500">
                🎯 {t("Target job description (the interviewer will attack the resume-JD gaps)")}
              </p>
              <textarea
                className="input mt-2 h-24 resize-none text-sm"
                placeholder={t("Paste the JD here…")}
                value={jd}
                onChange={(e) => setJd(e.target.value)}
              />
              <button className="btn-primary mt-2 !py-1 text-xs" onClick={() => void saveJd()}>
                {jdSaved ? `✅ ${t("Saved")}` : t("Save JD")}
              </button>
            </div>
          )}
          {isBQ && hasResume === false && (
            <div className="mt-4 flex items-center justify-between gap-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              <span>
                {t("No resume on file — the interviewer will ask generic behavioral questions.")}{" "}
                <Link href="/interviews/new" className="font-medium underline">{t("Paste your resume")}</Link>
              </span>
              <ResumeUpload onExtract={() => setHasResume(true)} onError={setError} />
            </div>
          )}
          {turns.length === 0 && (
            <p className="mt-10 text-center text-sm text-slate-500">
              {isBQ
                ? t("An interviewer AI grills a candidate AI on YOUR resume — behavioral questions, pushbacks, and model STAR answers. Press Play and study the moves.")
                : t("Two AIs quiz each other from basics to depth — press Play, then sit back and learn. You can jump in with your own question anytime.")}
            </p>
          )}
          {turns.map((turn, i) => (
            <div key={i} className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${roleStyle[turn.speaker]}`}>
              <p className="mb-1 text-[10px] font-semibold uppercase text-slate-400">{roleLabel[turn.speaker]}</p>
              <span className="whitespace-pre-wrap">{turn.text}</span>
            </div>
          ))}
          {busy && <p className="text-xs text-slate-400">…</p>}
          <div ref={bottomRef} />
        </div>
        {error && <p className="mb-1 rounded bg-red-50 px-2 py-1 text-xs text-red-700">{error}</p>}
        <div className="flex gap-2 border-t border-slate-200 py-3">
          <input
            className="input"
            placeholder={t("Ask your own question… (the answering AI replies)")}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void askMine()}
          />
          <button className="btn-primary" disabled={busy || !input.trim()} onClick={() => void askMine()}>
            {t("Send")}
          </button>
          <button className="btn-secondary shrink-0"
            disabled={busy || playing || finished || turns.length >= MAX_TURNS}
            onClick={() => void generateTurn()}>
            ⏭ {t("Next turn")}
          </button>
        </div>
      </div>

      {board && (
        <div className="my-4 flex w-2/5 min-w-[280px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
          <p className="border-b border-slate-100 px-3 py-2 text-xs font-semibold text-slate-500">
            🧊 {t("Whiteboard (evolves with the dialogue)")}
          </p>
          <pre className="flex-1 overflow-auto p-3 font-mono text-xs leading-relaxed text-slate-800">{board}</pre>
        </div>
      )}
      </div>
    </div>
  );
}
