import { proxyToBackend } from "@/lib/backend";

export const dynamic = "force-dynamic";

export function GET(req: Request) {
  return proxyToBackend(req, "/openapi.json");
}
