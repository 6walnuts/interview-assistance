"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUTO_READ_KEY = "aic_voice_auto_read";

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

/** Text-to-speech playback with a persisted auto-read preference. */
export function useSpeaker(onError?: (msg: string) => void) {
  const [enabled, setEnabledState] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  useEffect(() => {
    setEnabledState(localStorage.getItem(AUTO_READ_KEY) === "1");
  }, []);

  const stop = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
    setSpeaking(false);
  }, []);

  const setEnabled = useCallback(
    (v: boolean) => {
      setEnabledState(v);
      localStorage.setItem(AUTO_READ_KEY, v ? "1" : "0");
      if (!v) stop();
    },
    [stop]
  );

  const speak = useCallback(
    async (text: string) => {
      stop();
      if (!text.trim()) return;
      try {
        const resp = await authFetch("/api/voice/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        const url = URL.createObjectURL(await resp.blob());
        const audio = new Audio(url);
        urlRef.current = url;
        audioRef.current = audio;
        audio.onended = audio.onerror = () => {
          if (audioRef.current === audio) stop();
        };
        setSpeaking(true);
        await audio.play();
      } catch (e) {
        stop();
        onErrorRef.current?.(e instanceof Error ? e.message : "Speech playback failed");
      }
    },
    [stop]
  );

  useEffect(() => stop, [stop]);

  return { enabled, setEnabled, speak, speaking, stop };
}
