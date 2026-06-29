export type AgentEvent = {
  type: string;
  content: string;
  data?: Record<string, unknown>;
};

export type Status = {
  version: string;
  codename: string;
  backend: string;
  model: string;
  cost: string;
  needs_api_key: boolean;
  greeting: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "agent" | "system" | "error" | "tool";
  text: string;
};

export async function getBackendUrl(): Promise<string> {
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<string>("backend_url");
}

export async function fetchStatus(base: string): Promise<Status> {
  const res = await fetch(`${base}/api/status`);
  if (!res.ok) throw new Error("Backend unavailable");
  return res.json();
}

export async function saveApiKey(base: string, api_key: string): Promise<void> {
  const res = await fetch(`${base}/api/key`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Invalid API key");
  }
}

export async function resetChat(base: string): Promise<void> {
  await fetch(`${base}/api/reset`, { method: "POST" });
}

export async function streamChat(
  base: string,
  message: string,
  onEvent: (evt: AgentEvent) => void,
): Promise<void> {
  const res = await fetch(`${base}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok || !res.body) {
    throw new Error("Chat request failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      for (const line of part.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (!payload) continue;
        const evt = JSON.parse(payload) as AgentEvent;
        if (evt.type === "stream_end") return;
        onEvent(evt);
      }
    }
  }
}

export async function fetchApprovalPending(
  base: string,
): Promise<{ command: string; reason: string } | null> {
  const res = await fetch(`${base}/api/approval/pending`);
  const data = await res.json();
  return data.pending ?? null;
}

export async function respondApproval(
  base: string,
  approved: boolean,
): Promise<void> {
  await fetch(`${base}/api/approval/respond`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved }),
  });
}
