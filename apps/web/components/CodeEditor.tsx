"use client";

import dynamic from "next/dynamic";

/**
 * Shared Monaco editor: one dynamic chunk for the whole app (tutor +
 * interview room). Self-hosted assets with an absolute origin so language
 * workers can resolve their modules from inside a Worker context.
 */
const CodeEditor = dynamic(
  async () => {
    const { loader, default: Editor } = await import("@monaco-editor/react");
    loader.config({ paths: { vs: `${window.location.origin}/monaco/vs` } });
    return Editor;
  },
  {
    ssr: false,
    loading: () => <div className="p-4 text-sm text-slate-400">Loading editor…</div>,
  }
);

export default CodeEditor;
