# Sweety user guide

Sweety is a marketing control plane. You sit as the board. A CMO agent and a marketing org plan campaigns, draft work, generate visuals, queue social posts, and keep a CRM — you approve what goes live.

Open the app at **http://localhost:3000** after the stack is running (see [README](README.md) for install).

---

## 1. Sign in

1. Open the app. You land on the login screen.
2. Use the demo board account, or create your own:
   - **Email:** `board@sweety.local`
   - **Password:** `sweety`
3. Click **Enter God Mode**.

Need a new login? Use **Need an account?** and register. An operator can also add a board user with `scripts/add-admin.ps1` (see the README).

**Sign out** is always in the top-right.

---

## 2. Create a brand

After login you see **Brands** — your portfolio.

1. Fill **New brand**:
   - **Brand name** (required)
   - **Mission** (what the org should optimize for)
   - Optional **Website**, **App URL**, **Logo URL**
2. Click **Seed marketing org**.

Sweety creates the brand and stands up a marketing team (CMO plus specialists). Click a brand card to open **God Mode**.

Each card shows spend vs monthly budget. Clicking a brand always starts in God Mode; use the top nav to move around.

---

## 3. The map (top nav)

Once a brand is open, the header is:

| Link | What it is |
| --- | --- |
| **Brands** | Back to the portfolio |
| **God Mode** | Chat with the CMO — briefs, plans, images |
| **Command** | Live radar: who is running, open work, hot CRM |
| **CRM** | Contacts, deals, pipeline |
| **Org** | Team, campaigns, approvals |
| **Studio** | Skills, models, heartbeat interval per agent |
| **Connectors** | Social login, HeyGen, MCP, brand profile |
| **Settings** | Keys, adapters, skill catalog |

You are the board. Agents work on a heartbeat. Nothing expensive or public should go live without an approval.

---

## 4. First-run path (recommended)

Do this in order the first time:

1. **Connectors** — add website / logo if you have them; connect socials you actually want to post to.
2. **God Mode** — brief the campaign in plain language.
3. **Org** — check that a campaign appeared, then **Approve** anything waiting.
4. **Studio** — **Apply recommended skills**, then **Wake all agents** (or use **Run team** on the campaign).
5. **Command** — watch live runs and last summaries.
6. Open the campaign board for tasks and artifacts.
7. **CRM** — load demo signals or capture real leads; wake the CRM steward.

---

## 5. God Mode (brief the CMO)

God Mode is a chat with the Chief Marketing Officer for that brand.

**What to type**

Describe the outcome, channel, and timing. Examples:

- “Launch a 2-week Spring Edit campaign across email and Instagram.”
- “I need a product-hunt style launch for our iOS app next month.”
- “Research competitors and draft a positioning brief before we spend.”

Empty-state chips send those starters for you. **Enter** sends; **Shift+Enter** is a new line.

**What the CMO can do from chat**

- Turn the brief into a plan (markdown).
- Save website / app / mission onto the brand if you mention them.
- Wake one role or the whole swarm.
- Generate stills. After you ask for an image, tap a platform chip (**Instagram 4:5**, **IG story 9:16**, **X 16:9**, **LinkedIn**, **Facebook**, **Reddit**, **Pinterest**, **TikTok**) so the frame matches that network.

Plans and images stay in this conversation. Campaign work itself lives under **Org**.

---

## 6. Connectors (social, video, brand profile)

**Connectors** is the desk for this brand’s profile and outbound tools.

### Brand assets

- Website, app URL, and logo URL — or **upload a logo** (png, jpg, webp, gif, svg).
- Click **Save profile**. God Mode uses these when planning.

### Social & media

For each network you can:

- **Login with …** if a developer app is configured in `.env` (Reddit, X, LinkedIn, Facebook, Instagram).
- Or open **Paste token / API key instead** and save credentials from that platform’s console.

Facebook Login can also attach Instagram (professional account linked to a Page). After Facebook, pick a Page if asked. Instagram image URLs must be public HTTPS.

**HeyGen** is video. Set `HEYGEN_API_KEY` (and avatar/voice IDs) in `.env`, or paste them on the connector card.

Live posts are queued for board approval when `REQUIRE_PUBLISH_APPROVAL=true` (the default). Approving on **Org** publishes with the stored tokens.

### MCP servers

Add an HTTP/SSE URL or a stdio command. On heartbeat, agents can list and call those tools.

---

## 7. Org (team, campaigns, approvals)

**Org** is the home screen for the brand.

### Agents

Cards show role, model, spend vs budget, and status.

- **Wake agent** — run one heartbeat now.
- **Wake all agents** — queue the whole swarm.
- **Expand org** — fill missing roles (full org is 14 people). Click an agent title to open their briefing and heartbeat log.

Roles: CMO, Brand Strategist, Copywriter, SEO Lead, Social Lead, Growth Analyst, Paid Media Lead, Community Lead, PR Lead, Email Lead, CRM Steward, Art Director, Video Lead, Lifecycle Lead.

### Campaigns

Create one with a **name** and **goal**, or let God Mode / the CMO spawn work from a brief.

Open a campaign to see:

- **Brief** (if written)
- **Board** — tasks in backlog → ready → checked out → review → done / blocked
- **Artifacts** — copy, briefs, calendars, research the agents saved
- **Run team** — wake every agent assigned to this campaign in parallel
- **Approve** / **Pause** the campaign itself

Click a task for description, assignee, artifacts, and recent runs. You can mark it ready / review / done / blocked, or **Release** it.

### Approvals (the board queue)

The right column lists items waiting on you (campaign scale, social publish, and similar).

- **Approve** — proceed (including live publish when that is what was queued).
- **Reject** — stop it.

If the list is empty, nothing is waiting.

---

## 8. Agent studio

**Studio** is how you tune the org without writing code.

- **Expand to full org** — same as Org: backfill roles.
- **Apply recommended skills** — load the default skill pack per role. Cyan chips = on; violet outline = recommended for that role.
- Toggle skills, set **model** and **heartbeat minutes**, then **Save** on that agent.
- **Model for all** + **Broadcast model** — same OpenRouter model id on every agent.
- **Wake all agents** — after skills are set.

Heartbeats run on that interval while the worker is up. **Wake** / **Pulse** / **Run team** run a cycle immediately.

---

## 9. Command radar

**Command** refreshes every few seconds.

Tiles: **Live runs**, **Open tasks**, **Approvals**, **Hot CRM**.

Each agent card shows inbox size, skill count, last wake time, last summary, and a cyan pulse when a run is live. **Pulse** wakes that agent. Use this screen while the swarm is working.

---

## 10. CRM (signal lattice)

**CRM** is the pipeline for this brand. Agents (especially the CRM steward) write here too.

1. **Load demo signals** if you want sample contacts and deals.
2. Or **Capture** a contact (name, email, company) with **Drop into lattice**.
3. Filter the constellation by **cool / warm / hot / star**, or search.
4. Select a contact to set temperature, **next action**, and log a note (**Write to trace**).
5. **Open deal** with a name and value; move cards across **signal → qualify → propose → commit → won / lost**.
6. **Wake CRM steward** so the agent scores, logs, and moves deals.

---

## 11. Settings

**Settings** is org-wide, not per-brand:

- Whether **OpenRouter** is configured (chat, image, search models). Keys stay on the server; restart compose after changing `.env`.
- Adapter health (OpenRouter live; Claude / Codex / LangChain / LangGraph are stubs unless you wire them).
- Skill catalog (name, slug, description).
- A brand picker if you want connectors from this page — prefer the brand **Connectors** tab.

If social OAuth just finished, Settings may show **Connected …**. For Facebook / Instagram, pick a Page if prompted.

---

## 12. How work actually moves

Keep this mental model:

1. You brief in **God Mode** (or create a campaign on **Org**).
2. Agents pick up **ready** tasks on heartbeat (automatic interval or Wake / Run team / Pulse).
3. They save **artifacts** (copy, images, calendars, research).
4. Risky or public actions raise an **approval**.
5. You **Approve** or **Reject** on Org.
6. Spend shows on the brand and on each agent vs their monthly budget.

If nothing is happening: check OpenRouter in Settings, wake the CMO or **Run team**, and confirm agents are **active** (not paused or terminated).

---

## 13. Agent page (one person)

From Org or Command, open an agent:

- **Wake now** — one heartbeat.
- **Pause** / **Resume** — stop or continue scheduled work.
- **Terminate** — take them out of the active org.
- Read the system briefing, assigned skills, and the heartbeat log (tokens, cost, optional trace).

---

## 14. What “good” looks like in a session

| You want… | Do this |
| --- | --- |
| A launch plan | God Mode brief → Org campaign → Approve |
| Copy and stills | Brief + platform chips in God Mode; Copywriter / Art Director in Studio |
| Posts on a network | Connect that network → Social Lead with `social-publish` → Approve the queue |
| Research before spend | Ask in God Mode; SEO / Strategist with `research-web` |
| Pipeline hygiene | CRM capture or demo → Wake CRM steward |
| The whole org working | Studio presets → Command **Wake all** or campaign **Run team** |

You stay the board: brief, connect channels, watch Command, and approve what ships.
