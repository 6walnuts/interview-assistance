// Copies Monaco's static assets into public/ so the editor is self-hosted
// (no CDN dependency — works offline and behind restrictive proxies).
// Runs automatically via the predev/prebuild npm scripts.
import { cpSync, existsSync, rmSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const src = join(root, "node_modules", "monaco-editor", "min", "vs");
const dest = join(root, "public", "monaco", "vs");

if (!existsSync(src)) {
  console.error("monaco-editor package not found — run npm install first");
  process.exit(1);
}
rmSync(dest, { recursive: true, force: true });
cpSync(src, dest, { recursive: true });
console.log("Copied Monaco assets to public/monaco/vs");
