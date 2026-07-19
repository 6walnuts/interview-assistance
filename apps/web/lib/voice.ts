"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUTO_READ_KEY = "aic_voice_auto_read";
const RATE_KEY = "aic_voice_rate";

export const PLAYBACK_RATES = [0.75, 1, 1.25, 1.5, 2] as const;

/**
 * Text sent to TTS, with code stripped: fenced blocks (including an unclosed
 * trailing fence) are dropped entirely — listening to code read aloud is
 * noise — and inline backticks keep their text without the ticks.
 */
export function stripCodeForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/```[\s\S]*$/, " ")
    .replace(/`([^`\n]+)`/g, "$1")
    .replace(/\s{3,}/g, " ")
    .trim();
}

async function authFetch(path: string, init: RequestInit): Promise<Response> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return resp;
}

export async function transcribeAudio(blob: Blob): Promise<string> {
  const resp = await authFetch("/api/voice/transcribe", {
    method: "POST",
    body: blob,
    headers: { "Content-Type": blob.type || "audio/webm" },
  });
  return ((await resp.json()) as { text: string }).text;
}

/** Click-to-record microphone input; the recording is transcribed server-side. */
export function useVoiceInput(
  onTranscript: (text: string) => void,
  onError: (msg: string) => void
) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  // Latest callbacks, so the handlers bound at record time never go stale.
  const callbacksRef = useRef({ onTranscript, onError });
  callbacksRef.current = { onTranscript, onError };

  const toggle = useCallback(async () => {
    if (recorderRef.current) {
      recorderRef.current.stop();
      return;
    }
    if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      callbacksRef.current.onError("This browser does not support voice recording.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      const chunks: Blob[] = [];
      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        recorderRef.current = null;
        setRecording(false);
        const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        if (blob.size === 0) return;
        setTranscribing(true);
        try {
          const text = await transcribeAudio(blob);
          if (text.trim()) callbacksRef.current.onTranscript(text.trim());
        } catch (e) {
          callbacksRef.current.onError(e instanceof Error ? e.message : "Transcription failed");
        } finally {
          setTranscribing(false);
        }
      };
      rec.start();
      recorderRef.current = rec;
      setRecording(true);
    } catch (e) {
      callbacksRef.current.onError(e instanceof Error ? e.message : "Microphone unavailable");
    }
  }, []);

  useEffect(
    () => () => {
      recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
      recorderRef.current = null;
    },
    []
  );

  return { recording, transcribing, toggle };
}

/** Text-to-speech playback with persisted auto-read and speed preferences. */
export function useSpeaker(onError?: (msg: string) => void) {
  const [enabled, setEnabledState] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [rate, setRateState] = useState(1);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);
  const rateRef = useRef(1);
  // Monotonic sequence: each speak() invalidates all earlier ones, so a slow
  // TTS fetch that resolves late can never play on top of newer audio.
  const seqRef = useRef(0);
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  useEffect(() => {
    setEnabledState(localStorage.getItem(AUTO_READ_KEY) === "1");
    const saved = Number.parseFloat(localStorage.getItem(RATE_KEY) ?? "1");
    if (PLAYBACK_RATES.includes(saved as (typeof PLAYBACK_RATES)[number])) {
      setRateState(saved);
      rateRef.current = saved;
    }
  }, []);

  const setRate = useCallback((r: number) => {
    setRateState(r);
    rateRef.current = r;
    localStorage.setItem(RATE_KEY, String(r));
    // Apply immediately to whatever is currently playing.
    if (audioRef.current) audioRef.current.playbackRate = r;
  }, []);

  const stopPlayback = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
    setSpeaking(false);
  }, []);

  const stop = useCallback(() => {
    seqRef.current += 1; // also cancels any speak() still fetching
    stopPlayback();
  }, [stopPlayback]);

  const setEnabled = useCallback(
    (v: boolean) => {
      setEnabledState(v);
      localStorage.setItem(AUTO_READ_KEY, v ? "1" : "0");
      if (!v) stop();
    },
    [stop]
  );

  const speak = useCallback(
    async (text: string, opts?: { voice?: string; waitUntilDone?: boolean }) => {
      stopPlayback();
      const seq = ++seqRef.current; // newer speech always wins
      const speakable = stripCodeForSpeech(text);
      if (!speakable) return;
      try {
        const resp = await authFetch("/api/voice/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: speakable,
            ...(opts?.voice ? { voice: opts.voice } : {}),
          }),
        });
        const blob = await resp.blob();
        if (seq !== seqRef.current) return; // superseded while fetching
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.playbackRate = rateRef.current;
        urlRef.current = url;
        audioRef.current = audio;
        const finished = new Promise<void>((resolve) => {
          audio.onended = audio.onerror = () => {
            if (audioRef.current === audio) stopPlayback();
            resolve();
          };
          // pause also fires when a newer speak()/stop() interrupts playback
          audio.onpause = () => resolve();
        });
        setSpeaking(true);
        await audio.play();
        if (opts?.waitUntilDone) await finished;
      } catch (e) {
        if (seq === seqRef.current) {
          stopPlayback();
          onErrorRef.current?.(e instanceof Error ? e.message : "Speech playback failed");
        }
      }
    },
    [stopPlayback]
  );

  useEffect(() => stop, [stop]);

  return { enabled, setEnabled, speak, speaking, stop, rate, setRate };
}
