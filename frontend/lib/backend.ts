const HOP_BY_HOP = [
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
];

export function backendOrigin(): string {
  return (process.env.API_INTERNAL_URL || process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    "",
  );
}

function copyHeaders(source: Headers, extra?: Record<string, string>): Headers {
  const headers = new Headers();
  source.forEach((value, key) => {
    if (!HOP_BY_HOP.includes(key.toLowerCase())) headers.set(key, value);
  });
  headers.delete("accept-encoding");
  if (extra) {
    for (const [key, value] of Object.entries(extra)) headers.set(key, value);
  }
  return headers;
}

function publicLocation(req: Request, location: string): string {
  try {
    const backend = new URL(backendOrigin());
    const loc = new URL(location, backend);
    const sameBackend =
      loc.origin === backend.origin ||
      ((loc.hostname === "localhost" || loc.hostname === "127.0.0.1") && loc.port === "8000");
    if (!sameBackend) return location;
    const incoming = new URL(req.url);
    loc.protocol = incoming.protocol;
    loc.host = incoming.host;
    return loc.toString();
  } catch {
    return location;
  }
}

export async function proxyToBackend(req: Request, backendPath: string): Promise<Response> {
  const incoming = new URL(req.url);
  const target = `${backendOrigin()}${backendPath.startsWith("/") ? backendPath : `/${backendPath}`}${incoming.search}`;
  const headers = copyHeaders(req.headers, {
    "x-forwarded-host": incoming.host,
    "x-forwarded-proto": incoming.protocol.replace(":", ""),
  });

  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: "manual",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  const upstream = await fetch(target, init);
  const out = copyHeaders(upstream.headers);
  const location = upstream.headers.get("location");
  if (location) out.set("location", publicLocation(req, location));

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: out,
  });
}
