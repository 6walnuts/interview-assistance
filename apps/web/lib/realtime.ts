"use client";

import { getToken } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface RealtimeHandlers {
  /** Final transcript of something the user said. */
  onUserTranscript: (text: string) => void;
  /** Final transcript of something the AI said. */
  onAssistantTranscript: (text: string) => void;
  /**
   * The model called a tool (interview calls: advance_stage /
   * record_observation). Execute it against the backend and return the result
   * object to feed back. Omit for calls without tools (tutor lessons).
   */
  onToolCall?: (name: string, args: Record<string, unknown>) => Promise<Record<string, unknown>>;
  onStateChange: (state: "connecting" | "live" | "closed") => void;
  onError: (msg: string) => void;
}

export interface RealtimeConnection {
  stop: () => void;
}

/** What to talk to: a mock interview session, or a tutor lesson on a topic. */
export type RealtimeTarget = { interviewId: string } | { topicSlug: string };

/**
 * Live voice call: mints an ephemeral secret from our backend, then connects
 * the browser straight to OpenAI's Realtime API over WebRTC. Transcript events
 * stream back over the data channel.
 */
export async function startRealtimeCall(
  target: RealtimeTarget,
  handlers: RealtimeHandlers
): Promise<RealtimeConnection> {
  handlers.onStateChange("connecting");

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const tokenResp = await fetch(`${API_URL}/api/voice/realtime-session`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      interview_id: "interviewId" in target ? target.interviewId : null,
      topic_slug: "topicSlug" in target ? target.topicSlug : null,
    }),
  });
  if (!tokenResp.ok) {
    let detail = tokenResp.statusText;
    try {
      const body = await tokenResp.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep statusText */
    }
    handlers.onStateChange("closed");
    throw new Error(detail);
  }
  const { client_secret, model } = (await tokenResp.json()) as {
    client_secret: string;
    model: string;
  };

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const pc = new RTCPeerConnection();
  const audioEl = new Audio();
  audioEl.autoplay = true;

  let stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    pc.close();
    stream.getTracks().forEach((t) => t.stop());
    audioEl.pause();
    audioEl.srcObject = null;
    handlers.onStateChange("closed");
  };

  try {
    stream.getTracks().forEach((t) => pc.addTrack(t, stream));
    pc.ontrack = (e) => {
      audioEl.srcObject = e.streams[0];
    };
    pc.onconnectionstatechange = () => {
      if (["failed", "disconnected", "closed"].includes(pc.connectionState) && !stopped) {
        handlers.onError("Voice call connection lost.");
        stop();
      }
    };

    const dc = pc.createDataChannel("oai-events");
    dc.onopen = () => handlers.onStateChange("live");

    // Relay a model tool call to the backend, then feed the result back over
    // the data channel and ask the model to continue speaking.
    const runToolCall = async (name: string, argsRaw: string, callId: string) => {
      let result: Record<string, unknown>;
      try {
        if (!handlers.onToolCall) throw new Error(`no tool handler for '${name}'`);
        const args = argsRaw ? (JSON.parse(argsRaw) as Record<string, unknown>) : {};
        result = await handlers.onToolCall(name, args);
      } catch (err) {
        result = { ok: false, error: err instanceof Error ? err.message : "tool call failed" };
      }
      if (dc.readyState !== "open") return;
      dc.send(JSON.stringify({
        type: "conversation.item.create",
        item: { type: "function_call_output", call_id: callId, output: JSON.stringify(result) },
      }));
      dc.send(JSON.stringify({ type: "response.create" }));
    };

    dc.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data as string);
        // Event names cover both the GA and beta Realtime APIs.
        if (
          ev.type === "conversation.item.input_audio_transcription.completed" &&
          typeof ev.transcript === "string" &&
          ev.transcript.trim()
        ) {
          handlers.onUserTranscript(ev.transcript.trim());
        } else if (
          (ev.type === "response.output_audio_transcript.done" ||
            ev.type === "response.audio_transcript.done") &&
          typeof ev.transcript === "string" &&
          ev.transcript.trim()
        ) {
          handlers.onAssistantTranscript(ev.transcript.trim());
        } else if (
          ev.type === "response.output_item.done" &&
          ev.item?.type === "function_call" &&
          typeof ev.item.name === "string" &&
          typeof ev.item.call_id === "string"
        ) {
          void runToolCall(ev.item.name, ev.item.arguments ?? "", ev.item.call_id);
        } else if (ev.type === "error") {
          handlers.onError(ev.error?.message ?? "Realtime API error");
        }
      } catch {
        /* ignore non-JSON frames */
      }
    };

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    const sdpResp = await fetch(
      `https://api.openai.com/v1/realtime/calls?model=${encodeURIComponent(model)}`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${client_secret}`, "Content-Type": "application/sdp" },
        body: offer.sdp,
      }
    );
    if (!sdpResp.ok) {
      throw new Error(`Realtime connection failed (${sdpResp.status}): ${await sdpResp.text()}`);
    }
    await pc.setRemoteDescription({ type: "answer", sdp: await sdpResp.text() });
  } catch (e) {
    stop();
    throw e instanceof Error ? e : new Error("Failed to start voice call");
  }

  return { stop };
}
