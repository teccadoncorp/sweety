# Sweety

A Docker-first marketing control plane for AI agents. You sit as the board. Agents work campaigns through heartbeats, tasks, artifacts, approvals, search, image/video, and social connectors.

**How to use the product:** [USAGE.md](USAGE.md) — sign in, brands, God Mode, org, studio, command, CRM, connectors, and approvals.

OpenRouter is the live runtime (chat, web search plugin, image models). Claude, Codex, LangChain, and LangGraph are adapter stubs.

## Run

Default compose serves a production Next.js build (fast). Bind-mount `npm run dev` is only for local UI work.

```bash
cp .env.example .env
# set OPENROUTER_API_KEY
docker compose up --build
```

Hot-reload frontend locally:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

On Amazon Linux with an older Docker Buildx:

```bash
COMPOSE_BAKE=false docker compose up -d --build
```

The browser only talks to the frontend. Next.js proxies `/api`, `/media`, `/docs`, and `/health` to the backend (`API_INTERNAL_URL`, `http://api:8000` in Docker). Rebuild `web` after frontend changes.

- Public app: http://34.255.116.239 (login: `/login`)
- Local app: http://localhost:3000
- API docs (via frontend): http://34.255.116.239/docs
- Demo login: `board@sweety.local` / `sweety`
- CRM: brand nav → **CRM** (signal lattice + pipeline)
- Swarm radar: **Command**
- Configure skills / wake the swarm: **Studio**
- Campaign **Run team** wakes every assigned agent in parallel
- Full org is 14 agents; **Expand org** backfills missing roles

Add or reset a board login (Postgres must be up):

```bash
# PowerShell
.\scripts\add-admin.ps1 you@company.com secret

# or Compose
docker compose --profile tools run --rm create-admin --email you@company.com --password secret
```

Restart compose after changing `.env`.

## Production

Caddy (or host Nginx) only talks to the frontend. Next.js forwards `/api` and `/media` to the backend. Set `SWEETY_PUBLIC_URL` and `SWEETY_API_PUBLIC_URL` to the public frontend origin:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Set `JWT_SECRET` and `OPENROUTER_API_KEY` in `.env` first. Default login is still `board@sweety.local` / `sweety` unless you change `SEED_EMAIL` / `SEED_PASSWORD`. Point `SWEETY_PUBLIC_URL` at the public host.

## Model map

| Job | Env | Default |
| --- | --- | --- |
| Chat / agents | `SWEETY_CHAT_MODEL` / `OPENROUTER_DEFAULT_MODEL` | `openai/gpt-4o-mini` |
| Web search | OpenRouter `web` plugin, optional Tavily/Brave | `SWEETY_SEARCH_MODEL` |
| Images | `SWEETY_IMAGE_MODEL` | `google/gemini-2.5-flash-image` |
| Video | HeyGen | `HEYGEN_API_KEY` + avatar/voice IDs |

## Social login

Preferred: create a developer app and set client id/secret in `.env`, then **Login with** that network in Settings.

Redirect URI for every OAuth app:

`http://localhost:3000/api/v1/connectors/callback/{reddit|twitter|linkedin|facebook|instagram}`

| Network | Login | Fallback |
| --- | --- | --- |
| Reddit | OAuth (identity, submit, read) | paste access token + subreddit |
| X / Twitter | OAuth 2.0 + PKCE | paste user access token |
| LinkedIn | OAuth (`w_member_social`) | paste token + person URN |
| Facebook Pages | Facebook Login, then pick a Page | paste page token + page id |
| Instagram | Same Meta app; professional account linked to a Page | paste token + `ig_user_id`. Image URL must be public HTTPS |

Live posts queue a board approval (`REQUIRE_PUBLISH_APPROVAL=true`). Approving publishes with the stored tokens.

## MCP

Settings → MCP servers. Add an HTTP/SSE endpoint or a stdio command. Agents get `list_mcp_tools` and `call_mcp_tool`.

## Add a skill

Drop `backend/skills/<slug>/` with `manifest.json` and `SKILL.md`, then assign the slug on an agent.
