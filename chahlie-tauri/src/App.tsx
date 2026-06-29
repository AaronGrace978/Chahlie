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
import "./App.css";

function uid() {
  return Math.random().toString(36).slice(2);
}

function eventToMessages(evt: AgentEvent, streamingId: string | null): {
  messages: ChatMessage[];
  streamingId: string | null;
  streamingText: string;
} {
  const messages: ChatMessage[] = [];
  let nextId = streamingId;
  let streamingText = "";

  switch (evt.type) {
    case "text": {
      const streaming = evt.data?.streaming === true;
      if (streaming) {
        return { messages: [], streamingId: nextId, streamingText: evt.content };
      }
      messages.push({ id: uid(), role: "agent", text: evt.content });
      break;
    }
    case "thinking":
    case "reflection":
    case "cost":
      messages.push({ id: uid(), role: "system", text: evt.content });
      break;
    case "tool_use":
      messages.push({
        id: uid(),
        role: "tool",
        text: String(evt.data?.tool ?? "tool"),
      });
      break;
    case "tool_result":
      messages.push({
        id: uid(),
        role: "system",
        text: `${evt.data?.success ? "✓" : "✗"} ${evt.data?.tool}: ${evt.content.slice(0, 120)}`,
      });
      break;
    case "error":
      messages.push({ id: uid(), role: "error", text: evt.content });
      break;
    default:
      break;
  }

  return { messages, streamingId: null, streamingText };
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
        const { messages: added } = eventToMessages(evt, null);
        if (added.length) {
          setMessages((m) => [...m, ...added]);
        }
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
      <div className="app error-screen">
        <h1>⚾ Chahlie</h1>
        <pre>{error}</pre>
      </div>
    );
  }

  if (!status || !base) {
    return <div className="app loading">Starting Chahlie…</div>;
  }

  if (status.needs_api_key) {
    return (
      <div className="app setup">
        <div className="setup-card">
          <h1>⚾ Welcome to Chahlie</h1>
          <p>Paste your free Ollama Cloud API key to start.</p>
          <a href="https://ollama.com/settings/keys" target="_blank" rel="noreferrer">
            ollama.com/settings/keys
          </a>
          <input
            type="password"
            placeholder="Paste API key…"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSaveKey()}
          />
          {keyError && <p className="key-error">{keyError}</p>}
          <button type="button" onClick={onSaveKey} disabled={apiKey.trim().length < 8}>
            Start Chahlie
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">⚾ CHAHLIE v{status.version} "{status.codename}"</span>
        <span className="meta">
          ☁ {status.backend} · {status.model} · {status.cost}
        </span>
      </header>

      <main className="chat" ref={logRef}>
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.role}`}>
            {m.role === "user" && <strong>You: </strong>}
            {m.role === "agent" && <strong>Chahlie: </strong>}
            {m.role === "error" && <strong>✗ </strong>}
            {m.role === "tool" && <strong>⚙ </strong>}
            {m.text}
          </div>
        ))}
        {liveAgent && (
          <div className="bubble agent">
            <strong>Chahlie: </strong>
            {liveAgent}
          </div>
        )}
      </main>

      <footer className="composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={busy ? "Chahlie is thinking…" : "Type a message…"}
          disabled={busy}
        />
        <button type="button" onClick={send} disabled={busy || !input.trim()}>
          Send
        </button>
        <button type="button" className="ghost" onClick={onClear} disabled={busy}>
          Clear
        </button>
      </footer>

      {approval && (
        <div className="modal-backdrop">
          <div className="modal">
            <h2>⚠ Approval needed</h2>
            <p className="reason">{approval.reason}</p>
            <pre>{approval.command}</pre>
            <div className="modal-actions">
              <button type="button" className="approve" onClick={() => onApproval(true)}>
                Approve
              </button>
              <button type="button" className="deny" onClick={() => onApproval(false)}>
                Deny
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
