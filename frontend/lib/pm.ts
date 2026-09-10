export const PM_TOKEN_KEY = "sweety_pm_token";
export const PM_WORKSPACE_KEY = "sweety_pm_workspace";

export function getPmToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(PM_TOKEN_KEY);
}

export function setPmToken(token: string) {
  localStorage.setItem(PM_TOKEN_KEY, token);
}

export function clearPmToken() {
  localStorage.removeItem(PM_TOKEN_KEY);
}

export function getPmWorkspaceId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(PM_WORKSPACE_KEY);
}

export function setPmWorkspaceId(id: string) {
  localStorage.setItem(PM_WORKSPACE_KEY, id);
}

export async function pmApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getPmToken();
  const headers: Record<string, string> = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };
  const res = await fetch(`/api/v1/pm${path}`, {
    ...options,
    headers,
    signal: options.signal ?? (typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(25_000) : undefined),
  });
  if (res.status === 401 && typeof window !== "undefined") {
    clearPmToken();
    if (!path.startsWith("/auth/")) window.location.href = "/pm/login";
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type PmWorkspace = {
  id: string;
  name: string;
  slug: string;
  role: string;
  can_create_features: boolean;
  created_at: string;
  members: PmMember[];
};

export type PmMember = {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
};

export type PmMe = {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
  workspaces: {
    id: string;
    name: string;
    slug: string;
    role: string;
    can_create_features: boolean;
  }[];
};

export type PmProject = {
  id: string;
  workspace_id: string;
  name: string;
  key: string;
  description: string;
  sweety_brand_id: string | null;
  created_at: string;
  feature_count: number;
  issue_count: number;
};

export type PmFeature = {
  id: string;
  project_id: string;
  key: string;
  number: number;
  title: string;
  description: string;
  status: string;
  source: string;
  created_by_user_id: string | null;
  issue_count: number;
  created_at: string;
  updated_at: string;
};

export type PmIssue = {
  id: string;
  project_id: string;
  feature_id: string | null;
  key: string;
  number: number;
  title: string;
  description: string;
  kind: string;
  status: string;
  priority: number;
  assignee_id: string | null;
  reporter_id: string | null;
  assignee_name: string;
  reporter_name: string;
  feature_title: string;
  feature_key: string;
  due_date: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type PmComment = {
  id: string;
  issue_id: string;
  user_id: string;
  author_name: string;
  body: string;
  created_at: string;
};

export type PmBoard = {
  project: PmProject;
  features: PmFeature[];
  columns: Record<string, PmIssue[]>;
  members: PmMember[];
  role: string;
  can_create_features: boolean;
};

export type PmChatMessage = {
  id: string;
  role: string;
  content: string;
  trace?: unknown[];
  created_at: string | null;
};

export const ISSUE_COLUMNS = ["backlog", "todo", "in_progress", "review", "done"] as const;
export const ISSUE_KINDS = ["story", "task", "bug"] as const;
export const FEATURE_STATUSES = ["backlog", "planned", "in_progress", "done"] as const;
export const PRIORITY_LABELS = ["Urgent", "High", "Medium", "Low", "None"];

export function priorityLabel(n: number) {
  return PRIORITY_LABELS[n] || "Medium";
}
