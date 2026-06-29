import { useCallback, useEffect, useRef, useState } from "react";
import {
  AgentEvent,
  ChatMessage,
  Status,
  fetchApprovalPending,
  fetchStatus,
  getBackendUrl,
  resetChat,
  respondApproval,
  saveApiKey,
  streamChat,
} from "./api";
import { BostonBanner } from "./components/BostonBanner";
import {
  BeerMugIcon,
  ChahlieLogoMark,
  GreenMonsterIcon,
  MassAveSignIcon,
  ThinkingCapIcon,
} from "./components/BostonIcons";
import "./theme.css";
import "./App.css";

function uid() {
  return Math.random().toString(36).slice(2);
}

function MessageIcon({ role, text }: { role: ChatMessage["role"]; text: string }) {
  if (role === "error") return <MassAveSignIcon size={18} />;
  if (role === "tool") {
    return text.startsWith("✓") ? (
      <GreenMonsterIcon size={18} />
    ) : (
      <MassAveSignIcon size={18} />
    );
  }
  if (role === "system") {
    const lower = text.toLowerCase();
    if (lower.includes("thinking") || lower.includes("retryin") || lower.includes("💭")) {
      return <ThinkingCapIcon size={18} />;
    }
    if (lower.includes("cost") || lower.includes("💰")) {
      return <GreenMonsterIcon size={18} />;
    }
  }
  return null;
}

function eventToMessages(evt: AgentEvent): ChatMessage[] {
  switch (evt.type) {
    case "text":
      if (evt.data?.streaming === true) return [];
      return [{ id: uid(), role: "agent", text: evt.content }];
    case "thinking":
      return [{ id: uid(), role: "system", text: evt.content }];
    case "reflection":
    case "cost":
      return [{ id: uid(), role: "system", text: evt.content }];
    case "tool_use":
      return [{ id: uid(), role: "tool", text: String(evt.data?.tool ?? "tool") }];
    case "tool_result":
      return [
        {
          id: uid(),
          role: "system",
          text: `${evt.data?.success ? "✓" : "✗"} ${evt.data?.tool}: ${evt.content.slice(0, 120)}`,
        },
      ];
    case "error":
      return [{ id: uid(), role: "error", text: evt.content }];
    default:
      return [];
  }
}

function renderMessageBody(text: string) {
  const parts = text.split(/(`[^`]+`)/g);
  return parts.map((part, i) =>
    part.startsWith("`") && part.endsWith("`") ? (
      <code key={i} className="inline-code">
        {part.slice(1, -1)}
      </code>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export default function App() {
  const [base, setBase] = useState<string | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [keyError, setKeyError] = useState<string | null>(null);
  const [approval, setApproval] = useState<{
    command: string;
    reason: string;
  } | null>(null);
  const [liveAgent, setLiveAgent] = useState("");
  const logRef = useRef<HTMLDivElement>(null);

  const refreshStatus = useCallback(async (url: string) => {
    const s = await fetchStatus(url);
    setStatus(s);
    return s;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const url = await getBackendUrl();
        setBase(url);
        const s = await refreshStatus(url);
        setMessages([{ id: uid(), role: "system", text: s.greeting }]);
      } catch (e) {
        setError(
          e instanceof Error
            ? e.message
            : "Could not connect to Chahlie backend. Install Python deps:\n  pip install -r requirements-tauri.txt",
        );
      }
    })();
  }, [refreshStatus]);

  useEffect(() => {
    if (!base || !busy) return;
    const timer = setInterval(async () => {
      const pending = await fetchApprovalPending(base);
      if (pending) setApproval(pending);
    }, 500);
    return () => clearInterval(timer);
  }, [base, busy]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [messages, liveAgent]);

  const send = async () => {
    if (!base || !input.trim() || busy) return;
    const msg = input.trim();
    setInput("");
    setBusy(true);
    setLiveAgent("");
    setMessages((m) => [...m, { id: uid(), role: "user", text: msg }]);

    try {
      let streamBuf = "";
      await streamChat(base, msg, (evt) => {
        if (evt.type === "text" && evt.data?.streaming === true) {
          streamBuf += evt.content;
          setLiveAgent(streamBuf);
          return;
        }
        const added = eventToMessages(evt);
        if (added.length) setMessages((m) => [...m, ...added]);
      });
      if (streamBuf) {
        setMessages((m) => [...m, { id: uid(), role: "agent", text: streamBuf }]);
      }
      setLiveAgent("");
      await refreshStatus(base);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: uid(),
          role: "error",
          text: e instanceof Error ? e.message : "Request failed",
        },
      ]);
    } finally {
      setBusy(false);
      setApproval(null);
    }
  };

  const onSaveKey = async () => {
    if (!base) return;
    setKeyError(null);
    try {
      await saveApiKey(base, apiKey.trim());
      setApiKey("");
      await refreshStatus(base);
    } catch (e) {
      setKeyError(e instanceof Error ? e.message : "Key rejected");
    }
  };

  const onClear = async () => {
    if (!base) return;
    await resetChat(base);
    setMessages([{ id: uid(), role: "system", text: "Conversation cleared." }]);
    await refreshStatus(base);
  };

  const onApproval = async (approved: boolean) => {
    if (!base) return;
    await respondApproval(base, approved);
    setApproval(null);
  };

  if (error) {
    return (
      <div className="app fenway-bg error-screen">
        <BostonBanner compact />
        <div className="error-card">
          <MassAveSignIcon size={32} />
          <h2>Something went wrong</h2>
          <pre>{error}</pre>
        </div>
      </div>
    );
  }

  if (!status || !base) {
    return (
      <div className="app fenway-bg loading-screen">
        <BeerMugIcon size={40} />
        <p>Chahlie's grabbin' a beer while the backend starts…</p>
      </div>
    );
  }

  if (status.needs_api_key) {
    return (
      <div className="app fenway-bg setup">
        <BostonBanner status={status} />
        <div className="setup-card">
          <ChahlieLogoMark size={56} />
          <h2>Welcome to Chahlie</h2>
          <p className="setup-tagline">You're wicked smart — paste your key to start.</p>
          <a
            className="setup-link"
            href="https://ollama.com/settings/keys"
            target="_blank"
            rel="noreferrer"
          >
            ollama.com/settings/keys
          </a>
          <input
            type="password"
            placeholder="Paste Ollama API key…"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSaveKey()}
          />
          {keyError && (
            <p className="notice warning">
              <MassAveSignIcon size={16} /> {keyError}
            </p>
          )}
          <button type="button" className="btn-primary" onClick={onSaveKey} disabled={apiKey.trim().length < 8}>
            <GreenMonsterIcon size={18} /> Start Chahlie
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app fenway-bg">
      <BostonBanner status={status} />

      <main className="chat" ref={logRef}>
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.role}`}>
            <div className="bubble-head">
              <MessageIcon role={m.role} text={m.text} />
              {m.role === "user" && <strong>You</strong>}
              {m.role === "agent" && <strong>Chahlie</strong>}
              {m.role === "error" && <strong>Heads up</strong>}
              {m.role === "tool" && <strong>Tool</strong>}
            </div>
            <div className="bubble-body">{renderMessageBody(m.text)}</div>
          </div>
        ))}
        {liveAgent && (
          <div className="bubble agent streaming">
            <div className="bubble-head">
              <ThinkingCapIcon size={18} />
              <strong>Chahlie</strong>
            </div>
            <div className="bubble-body">{renderMessageBody(liveAgent)}</div>
          </div>
        )}
        {busy && !liveAgent && (
          <div className="bubble system thinking-row">
            <ThinkingCapIcon size={20} />
            <span>Chahlie's got his thinking cap on…</span>
          </div>
        )}
      </main>

      <footer className="composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={busy ? "Thinking…" : "Ask Chahlie anything…"}
          disabled={busy}
        />
        <button type="button" className="btn-primary" onClick={send} disabled={busy || !input.trim()}>
          Send
        </button>
        <button type="button" className="btn-secondary" onClick={onClear} disabled={busy}>
          Clear
        </button>
      </footer>

      {approval && (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-head">
              <MassAveSignIcon size={28} />
              <h2>Approval needed</h2>
            </div>
            <p className="reason">{approval.reason}</p>
            <pre className="code-block">{approval.command}</pre>
            <div className="modal-actions">
              <button type="button" className="btn-primary" onClick={() => onApproval(true)}>
                <GreenMonsterIcon size={16} /> Approve
              </button>
              <button type="button" className="btn-danger" onClick={() => onApproval(false)}>
                Deny
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
