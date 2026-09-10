import { NextRequest } from "next/server";

const ALLOWED = [
  "openrouter.ai",
  "oaidalleapiprodscus.blob.core.windows.net",
  "googleusercontent.com",
  "googleapis.com",
  "cloudflarestorage.com",
  "r2.dev",
  "openai.com",
];

function allowed(target: URL, requestHost: string) {
  if (target.pathname.startsWith("/media/")) return true;
  if (target.hostname === requestHost || target.hostname === "127.0.0.1" || target.hostname === "localhost") {
    return true;
  }
  return ALLOWED.some((host) => target.hostname === host || target.hostname.endsWith(`.${host}`));
}

export async function GET(req: NextRequest) {
  const raw = req.nextUrl.searchParams.get("url");
  if (!raw) return new Response("missing url", { status: 400 });
  let target: URL;
  try {
    target = new URL(raw, req.nextUrl.origin);
  } catch {
    return new Response("bad url", { status: 400 });
  }
  if (!allowed(target, req.nextUrl.hostname)) {
    return new Response("blocked", { status: 403 });
  }
  const upstream = await fetch(target.toString());
  if (!upstream.ok || !upstream.body) {
    return new Response("upstream failed", { status: 502 });
  }
  const name = target.pathname.split("/").pop() || "sweety-visual.png";
  const headers = new Headers();
  headers.set("content-type", upstream.headers.get("content-type") || "application/octet-stream");
  headers.set("content-disposition", `attachment; filename="${name.replace(/"/g, "")}"`);
  return new Response(upstream.body, { status: 200, headers });
}
