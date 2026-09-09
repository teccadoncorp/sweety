import { proxyToBackend } from "@/lib/backend";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

type Ctx = { params: Promise<{ path: string[] }> };

async function handle(req: Request, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxyToBackend(req, `/api/${path.join("/")}`);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
export const HEAD = handle;
