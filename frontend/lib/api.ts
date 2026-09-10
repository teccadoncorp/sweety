function apiBase(): string {
  return "";
}

export function publicAsset(url?: string | null): string {
  if (!url) return "";
  try {
    const parsed = new URL(url, typeof window === "undefined" ? "http://localhost" : window.location.origin);
    if (parsed.pathname.startsWith("/media/")) return parsed.pathname + parsed.search;
  } catch {
    return url;
  }
  return url;
}

export const TOKEN_KEY = "sweety_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };
  const res = await fetch(`${apiBase()}/api/v1${path}`, {
    ...options,
    headers,
    signal: options.signal ?? (typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(25_000) : undefined),
  });
  if (res.status === 401 && typeof window !== "undefined") {
    clearToken();
    if (!path.startsWith("/auth/")) window.location.href = "/login";
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type Brand = {
  id: string;
  name: string;
  mission: string;
  voice_notes: string;
  audience?: string;
  guidelines?: string;
  agents_paused?: boolean;
  logo_url?: string;
  website_url?: string;
  app_url?: string;
  monthly_budget_usd: string;
  spent_usd: string;
  created_at: string;
  campaigns_count?: number;
  launch_campaign?: string;
};

export type ChatMessage = {
  id: string;
  role: string;
  content: string;
  trace?: unknown[];
  images?: string[];
  created_at: string | null;
};

export type Agent = {
  id: string;
  brand_id: string;
  role: string;
  title: string;
  reports_to_id: string | null;
  adapter: string;
  model: string;
  system_prompt: string;
  skill_slugs: string[];
  monthly_budget_usd: string;
  status: string;
  heartbeat_interval_minutes: number;
  last_heartbeat_at: string | null;
  spent_usd: string;
};

export type Campaign = {
  id: string;
  brand_id: string;
  name: string;
  goal: string;
  brief: string;
  status: string;
  budget_cap_usd: string;
  spent_usd: string;
};

export type Task = {
  id: string;
  brand_id: string;
  campaign_id: string;
  parent_id: string | null;
  assignee_agent_id: string | null;
  title: string;
  description: string;
  priority: number;
  status: string;
  checked_out_by: string | null;
  created_at: string;
};

export type Artifact = {
  id: string;
  title: string;
  kind: string;
  content: string;
  task_id: string | null;
  created_by_agent_id: string | null;
  created_at: string;
};

export type Run = {
  id: string;
  agent_id: string;
  trigger: string;
  adapter: string;
  status: string;
  result_summary: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: string;
  trace: unknown[];
  created_at: string;
};

export type Approval = {
  id: string;
  kind: string;
  status: string;
  subject_type: string;
  subject_id: string | null;
  payload: {
    summary?: string;
    text?: string;
    title?: string;
    platform?: string;
    channel?: string;
    kind?: string;
    content_item_id?: string;
    publish_result?: { ok?: boolean; error?: string };
    scheduled_for?: string;
  };
  created_at: string;
  decided_at?: string | null;
};

export type ContentItem = {
  id: string;
  campaign_id: string | null;
  task_id: string | null;
  kind: string;
  channel: string;
  title: string;
  body: string;
  status: string;
  scheduled_for: string | null;
  published_at: string | null;
  extra: Record<string, unknown>;
  created_at: string;
};

export type CalendarSnapshot = {
  items: ContentItem[];
  counts: Record<string, number>;
};

export type BrandNotification = {
  id: string;
  kind: string;
  title: string;
  body: string;
  href: string;
  read_at: string | null;
  created_at: string;
};

export type AdapterHealth = { name: string; status: string; detail: string };
export type Skill = {
  slug: string;
  name: string;
  version: string;
  allowed_roles: string[];
  description: string;
};

export type CrmBoard = {
  contacts: number;
  accounts: number;
  open_deals: number;
  pipeline_usd: string;
  weighted_pipeline_usd: string;
  won_usd: string;
  avg_deal_usd: string;
  hot_leads: number;
  overdue: number;
  stages: Record<string, number>;
  avg_signal: number;
};

export type CrmAccount = {
  id: string;
  name: string;
  domain: string;
  industry: string;
  size: string;
  website: string;
  signal_score: number;
  tags: string[];
  notes: string;
};

export type CrmContact = {
  id: string;
  account_id: string | null;
  name: string;
  email: string;
  phone: string;
  title: string;
  company: string;
  channel: string;
  status: string;
  temperature: string;
  signal_score: number;
  tags: string[];
  source: string;
  next_action: string;
  notes: string;
  last_touch_at: string | null;
  created_at: string;
  account_name?: string;
};

export type CrmDeal = {
  id: string;
  account_id: string | null;
  contact_id: string | null;
  owner_agent_id?: string | null;
  name: string;
  stage: string;
  value_usd: string;
  probability: number;
  close_date: string;
  notes: string;
  lost_reason?: string;
  sort_order?: number;
  contact_name?: string;
  account_name?: string;
  created_at: string;
};

export type CrmActivity = {
  id: string;
  contact_id: string | null;
  deal_id: string | null;
  kind: string;
  title: string;
  body: string;
  due_at?: string | null;
  created_at: string;
};

export type SwarmQueued = { queued: number; agent_ids: string[]; reason: string };

export type CommandAgent = {
  id: string;
  role: string;
  title: string;
  status: string;
  model: string;
  last_heartbeat_at: string | null;
  inbox: number;
  live: boolean;
  last_run_status: string;
  last_summary: string;
  skill_count: number;
  spent_usd: string;
};

export type CommandSnapshot = {
  live_runs: number;
  ready_tasks: number;
  pending_approvals: number;
  crm_hot: number;
  agents_paused?: boolean;
  agents: CommandAgent[];
};
