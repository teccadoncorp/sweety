import { proxyToBackend } from "@/lib/backend";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ path: string[] }> };

async function handle(req: Request, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxyToBackend(req, `/media/${path.join("/")}`);
}

export const GET = handle;
export const HEAD = handle;
export const OPTIONS = handle;
