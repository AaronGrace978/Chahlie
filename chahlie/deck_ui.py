"""
Chahlie Steam Deck UI — gamepad-friendly, voice-enabled, 1280×800 polish.

Launch with:  python -m chahlie --deck
"""

from __future__ import annotations

import asyncio
from typing import Optional

try:
    from textual import on, work
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.events import Focus
    from textual.screen import ModalScreen
    from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static
    from textual.reactive import reactive
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from .agent import ChahlieAgent
from .config import (
    APP_CODENAME,
    APP_VERSION,
    BACKEND,
    OLLAMA_CLOUD_MODEL,
    OLLAMA_LOCAL_MODEL,
    VOICE_TTS_ENABLED,
)
from .deck_setup import needs_api_key_setup, reload_config, save_api_key, verify_api_key
from .personality import get_greeting
from .tools import set_approval_hook
from .voice import VoiceManager, voice_available


# Fenway palette
NAVY = "#0C2340"
GREEN = "#1E5631"
RED = "#BD3039"
ACCENT = "#2ECC71"
MUTED = "#5D6D7E"


class ApprovalScreen(ModalScreen[bool]):
    """Gamepad-friendly yes/no for dangerous shell commands."""

    CSS = f"""
    ApprovalScreen {{
        align: center middle;
    }}
    #approval-box {{
        width: 90%;
        max-width: 72;
        height: auto;
        max-height: 80%;
        background: {NAVY};
        border: thick {RED};
        padding: 1 2;
    }}
  #approval-cmd {{
        color: #F8F9FA;
        margin: 1 0;
    }}
    #approval-btns {{
        height: 5;
        margin-top: 1;
    }}
    #approve-btn {{
        background: {GREEN};
        color: white;
        min-width: 16;
        margin: 0 1;
    }}
    #deny-btn {{
        background: {RED};
        color: white;
        min-width: 16;
        margin: 0 1;
    }}
    """

    BINDINGS = [
        Binding("y", "approve", "Approve", show=False),
        Binding("n", "deny", "Deny", show=False),
        Binding("a", "approve", "Approve", show=False),
        Binding("b", "deny", "Deny", show=False),
        Binding("escape", "deny", "Deny", show=False),
    ]

    def __init__(self, command: str, reason: str):
        super().__init__()
        self.command = command
        self.reason = reason

    def compose(self) -> ComposeResult:
        with Vertical(id="approval-box"):
            yield Label("[bold yellow]⚠ APPROVAL NEEDED[/bold yellow]")
            yield Label(f"Flagged as: [red]{self.reason}[/red]")
            yield Static(f"$ {self.command}", id="approval-cmd")
            yield Label(
                "[dim]Only approve if you're sure. "
                "A / Y = approve · B / N = deny[/dim]"
            )
            with Horizontal(id="approval-btns"):
                yield Button("✓ Approve  (A)", id="approve-btn", variant="success")
                yield Button("✗ Deny  (B)", id="deny-btn", variant="error")

    @on(Button.Pressed, "#approve-btn")
    def _btn_approve(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#deny-btn")
    def _btn_deny(self) -> None:
        self.dismiss(False)

    def action_approve(self) -> None:
        self.dismiss(True)

    def action_deny(self) -> None:
        self.dismiss(False)


class SetupScreen(ModalScreen[str]):
    """First-run welcome — paste API key, then go."""

    CSS = f"""
    SetupScreen {{
        align: center middle;
    }}
    #setup-box {{
        width: 92%;
        max-width: 78;
        height: auto;
        background: {NAVY};
        border: thick {GREEN};
        padding: 1 2;
    }}
    #setup-title {{
        text-style: bold;
        color: {ACCENT};
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }}
    #setup-url {{
        color: {ACCENT};
    }}
    #setup-error {{
        color: #E74C3C;
    }}
    #api-input {{
        margin: 1 0;
        border: solid {ACCENT};
        background: #0A1A2E;
    }}
    #start-btn {{
        background: {GREEN};
        color: white;
        width: 100%;
        margin-top: 1;
    }}
  #skip-btn {{
        background: {MUTED};
        color: white;
        width: 100%;
        margin-top: 1;
    }}
    """

    BINDINGS = [
        Binding("escape", "skip", "Skip", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-box"):
            yield Label("⚾ Welcome to Chahlie!", id="setup-title")
            yield Label(
                "Paste your free Ollama API key to start chatting.",
                id="setup-help",
            )
            yield Label(
                "Get a free key at ollama.com/settings/keys",
                id="setup-url",
            )
            yield Label("", id="setup-error")
            yield Input(
                placeholder="Paste API key here…",
                password=True,
                id="api-input",
            )
            yield Button("▶  Start Chahlie", id="start-btn", variant="success")
            yield Button("Skip for now (typed chat won't work)", id="skip-btn")

    def on_mount(self) -> None:
        self.query_one("#api-input", Input).focus()

    @on(Button.Pressed, "#start-btn")
    @on(Input.Submitted, "#api-input")
    def _start(self, event=None) -> None:
        key = self.query_one("#api-input", Input).value.strip()
        err = self.query_one("#setup-error", Label)
        if not key or len(key) < 8:
            err.update("Key too short — paste the full key from ollama.com/settings/keys")
            self.app.bell()
            return
        err.update("Checking key…")
        ok, msg = verify_api_key(key)
        if not ok:
            err.update(msg)
            self.app.bell()
            return
        self.dismiss(key)

    @on(Button.Pressed, "#skip-btn")
    def _skip(self) -> None:
        self.dismiss("")

    def action_skip(self) -> None:
        self.dismiss("")


class DeckStatusBar(Static):
    """Top strip: backend, model, cost, voice state."""

    status_text = reactive("Chahlie Deck")

    def render(self) -> str:
        return self.status_text


if TEXTUAL_AVAILABLE:

    class ChahlieDeckApp(App):
        """Steam Deck edition — touch buttons, voice, compact layout."""

        TITLE = "Chahlie"
        SUB_TITLE = "Steam Deck Edition"

        CSS = f"""
        Screen {{
            background: {NAVY};
        }}

        Header {{
            background: {GREEN};
            color: white;
        }}

        Footer {{
            background: {NAVY};
        }}

        #status-bar {{
            dock: top;
            height: 1;
            background: {GREEN};
            color: #ECF0F1;
            padding: 0 1;
        }}

        #hero {{
            height: 3;
            background: {NAVY};
            border-bottom: solid {RED};
            padding: 0 1;
            content-align: center middle;
        }}

        #hero-title {{
            text-style: bold;
            color: {ACCENT};
        }}

        #toolbar {{
            dock: bottom;
            height: 3;
            background: #0A1A2E;
            border-top: solid {GREEN};
            padding: 0 1;
        }}

        #toolbar Button {{
            min-width: 10;
            margin: 0 1 0 0;
            background: {GREEN};
            color: white;
        }}

        #toolbar Button:hover {{
            background: {ACCENT};
            color: {NAVY};
        }}

        #mic-btn.listening {{
            background: {RED};
            color: white;
        }}

        #chat-log {{
            border: solid {RED};
            margin: 0 1;
            padding: 0 1;
            scrollbar-background: {NAVY};
            scrollbar-color: {GREEN};
        }}

        #input-row {{
            dock: bottom;
            height: 3;
            border-top: solid {GREEN};
            padding: 0 1;
            background: #0A1A2E;
        }}

        #input-row:focus-within {{
            background: #0E2A4A;
        }}

        #user-input {{
            width: 1fr;
            border: solid {ACCENT};
            background: {NAVY};
            color: white;
            min-height: 3;
        }}

        #user-input:focus {{
            border: thick {ACCENT};
            background: #0E2A4A;
        }}

        #user-input.-disabled {{
            opacity: 0.65;
            border: solid {MUTED};
        }}

        #input-hint {{
            width: auto;
            color: {MUTED};
            content-align: center middle;
            padding: 0 1;
        }}

        .msg-user {{
            color: #85C1E9;
        }}

        .msg-agent {{
            color: #A9DFBF;
        }}

        .msg-system {{
            color: {MUTED};
        }}

        .msg-tool {{
            color: #F5B041;
        }}

        .msg-error {{
            color: #E74C3C;
        }}
        """

        BINDINGS = [
            Binding("ctrl+c", "quit", "Quit"),
            Binding("f1", "help", "Help"),
            Binding("f2", "clear", "Clear"),
            Binding("f3", "memory", "Memory"),
            Binding("f4", "toggle_mic", "Talk"),
            Binding("f5", "toggle_tts", "TTS"),
            Binding("f6", "stop_speech", "Stop voice"),
            Binding("f7", "focus_input", "Type"),
            Binding("ctrl+l", "clear", "Clear", show=False),
            Binding("ctrl+i", "focus_input", "Type", show=False),
        ]

        def __init__(self):
            super().__init__()
            self.agent: Optional[ChahlieAgent] = None
            self.voice = VoiceManager()
            self._loop: Optional[asyncio.AbstractEventLoop] = None
            self._listening = False
            self._processing = False
            self._tts_on = VOICE_TTS_ENABLED
            self._input_placeholder = "Type or press F4 / 🎤 Talk to speak…"

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            yield DeckStatusBar(id="status-bar")
            yield Label(
                f"⚾ CHAHLIE v{APP_VERSION} \"{APP_CODENAME}\" — Steam Deck",
                id="hero-title",
            )
            yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
            with Horizontal(id="toolbar"):
                yield Button("Help", id="btn-help", variant="primary")
                yield Button("Clear", id="btn-clear")
                yield Button("Memory", id="btn-memory")
                yield Button("🎤 Talk", id="mic-btn")
                yield Button("🔊 TTS", id="tts-btn")
                yield Button("Quit", id="btn-quit", variant="warning")
            with Horizontal(id="input-row"):
                yield Input(
                    placeholder=self._input_placeholder,
                    id="user-input",
                )
                yield Label("F7 = focus", id="input-hint")
            yield Footer()

        def on_mount(self) -> None:
            self._loop = asyncio.get_running_loop()
            self._boot()

        @work
        async def _boot(self) -> None:
            if needs_api_key_setup():
                key = await self.push_screen_wait(SetupScreen())
                if key:
                    save_api_key(key)
                    reload_config()
                    self._log_system("API key saved. You're good to go, kehd!")
                else:
                    self._log_system(
                        "[yellow]No API key yet — type /key to add one[/yellow]"
                    )
            self._start_session()

        @work
        async def _change_api_key(self) -> None:
            key = await self.push_screen_wait(SetupScreen())
            if not key:
                return
            save_api_key(key)
            reload_config()
            self.agent = ChahlieAgent()
            self._refresh_status()
            self._log_system("API key updated.")

        def _start_session(self) -> None:
            set_approval_hook(self._approval_prompter)
            self.agent = ChahlieAgent()
            self._refresh_status()
            self._log_system(get_greeting())
            self._log_system(
                "Type below or tap 🎤 Talk · F1 Help · F2 Clear · F3 Memory · "
                "F4 Talk · F5 TTS · F7 Type · Enter send"
            )
            if voice_available():
                self._log_system(f"Voice: {self.voice.status_line()}")
            else:
                self._log_system("[dim]Voice: type to chat (mic optional)[/dim]")
            if self.agent:
                primer = self.agent.get_primer_summary()
                if primer.get("primed"):
                    self._log_system(
                        f"Project: {primer.get('name')} "
                        f"({primer.get('language', '?')} / {primer.get('framework', '?')})"
                    )
                if self.agent.plugin_warnings:
                    for w in self.agent.plugin_warnings:
                        self._log_system(f"[yellow]plugin: {w}[/yellow]")
            self._focus_input()

        def _input(self) -> Input:
            return self.query_one("#user-input", Input)

        def _focus_input(self) -> None:
            """Keep keyboard focus on the text field unless we're busy."""
            if self._processing or self._listening:
                return
            try:
                self._input().focus()
            except Exception:
                pass

        def _set_processing(self, on: bool) -> None:
            self._processing = on
            inp = self._input()
            inp.disabled = on
            if on:
                inp.placeholder = "Chahlie is thinking… (F7 refocuses when done)"
                bar = self.query_one("#status-bar", DeckStatusBar)
                bar.status_text = "⏳ Working… you can still read the chat"
            else:
                inp.placeholder = self._input_placeholder
                self._refresh_status()
                self._focus_input()

        def on_screen_resume(self) -> None:
            """Refocus after approval modals and other screens dismiss."""
            self._focus_input()

        def _chat(self) -> RichLog:
            return self.query_one("#chat-log", RichLog)

        def _log_user(self, text: str) -> None:
            self._chat().write(f"[bold #85C1E9]You:[/] {text}")

        def _log_agent(self, text: str) -> None:
            self._chat().write(f"[bold #A9DFBF]Chahlie:[/] {text}")

        def _log_system(self, text: str) -> None:
            self._chat().write(f"[dim]{text}[/dim]")

        def _log_tool(self, tool: str, detail: str = "") -> None:
            line = f"[bold #F5B041]⚙ {tool}[/]"
            if detail:
                line += f" [dim]{detail}[/]"
            self._chat().write(line)

        def _log_error(self, text: str) -> None:
            self._chat().write(f"[bold #E74C3C]✗ {text}[/]")

        def _refresh_status(self) -> None:
            if not self.agent:
                return
            c = self.agent.get_cost_summary()
            bar = self.query_one("#status-bar", DeckStatusBar)
            backend_label = c["backend"]
            if BACKEND == "ollama-cloud":
                model = OLLAMA_CLOUD_MODEL
            elif BACKEND == "ollama-local":
                model = OLLAMA_LOCAL_MODEL
            else:
                model = c.get("model", "?")
            tts = "TTS on" if self._tts_on else "TTS off"
            bar.status_text = (
                f"☁ {backend_label} · {model} · {c['formatted']} · "
                f"{self.voice.status_line()} · {tts}"
            )

        def _approval_prompter(self, command: str, reason: str) -> bool:
            """Block the agent thread until the user picks approve/deny."""
            if not self._loop:
                return False
            future = asyncio.run_coroutine_threadsafe(
                self.push_screen_wait(ApprovalScreen(command, reason)),
                self._loop,
            )
            try:
                return bool(future.result(timeout=300))
            except Exception:
                return False
            finally:
                try:
                    self.call_from_thread(self._focus_input)
                except RuntimeError:
                    self._focus_input()

        def _handle_slash(self, msg: str) -> bool:
            """Return True if handled (don't send to agent)."""
            cmd = msg.lower().strip()
            if cmd in ("/quit", "/exit"):
                self.exit()
                return True
            if cmd == "/clear":
                self.action_clear()
                return True
            if cmd == "/help":
                self.action_help()
                return True
            if cmd in ("/memory", "/mem"):
                self.action_memory()
                return True
            if cmd == "/voice":
                self.action_toggle_mic()
                return True
            if cmd == "/tts":
                self.action_toggle_tts()
                return True
            if cmd == "/key":
                self._change_api_key()
                return True
            if cmd.startswith("/"):
                self._log_system(f"Unknown command {cmd}. Try /help /clear /memory.")
                return True
            return False

        def _dispatch_agent_event(self, evt) -> None:
            """Handle one agent event on the UI thread."""
            if evt.type == "text":
                streaming = evt.data and evt.data.get("streaming")
                if streaming:
                    return
                self._log_agent(evt.content)
                if self._tts_on:
                    self.voice.speak(evt.content)
            elif evt.type == "thinking":
                self._log_system(f"💭 {evt.content}")
            elif evt.type == "tool_use":
                self._log_tool(evt.data.get("tool", "?"))
            elif evt.type == "tool_result":
                ok = "✓" if evt.data.get("success") else "✗"
                snippet = str(evt.content)[:160].replace("\n", " ")
                self._log_system(f"{ok} {evt.data.get('tool')}: {snippet}")
            elif evt.type == "reflection":
                self._log_system(f"💡 {evt.content}")
            elif evt.type == "error":
                msg = evt.content or ""
                self._log_error(msg)
                if "401" in msg or "unauthorized" in msg.lower():
                    self._log_system(
                        "[yellow]Bad API key — type /key to enter a new one[/yellow]"
                    )
            elif evt.type == "cost":
                self._log_system(f"💰 {evt.content}")

        def _process_message_worker(self, msg: str) -> None:
            """Run agent turn off the UI thread so typing stays responsive."""
            if not self.agent:
                return
            buffer = ""
            streaming = False
            try:
                for evt in self.agent.process(msg):
                    if evt.type == "text":
                        if evt.data and evt.data.get("streaming"):
                            buffer += evt.content
                            streaming = True
                            continue
                        if streaming and buffer:
                            chunk = buffer
                            buffer = ""
                            streaming = False
                            self.call_from_thread(self._log_agent, chunk)
                            if self._tts_on:
                                self.voice.speak(chunk)
                        self.call_from_thread(self._dispatch_agent_event, evt)
                    else:
                        if streaming and buffer:
                            chunk = buffer
                            buffer = ""
                            streaming = False
                            self.call_from_thread(self._log_agent, chunk)
                            if self._tts_on:
                                self.voice.speak(chunk)
                        self.call_from_thread(self._dispatch_agent_event, evt)
                if streaming and buffer:
                    self.call_from_thread(self._log_agent, buffer)
                    if self._tts_on:
                        self.voice.speak(buffer)
            except Exception as exc:
                self.call_from_thread(self._log_error, str(exc))
            finally:
                self.call_from_thread(self._set_processing, False)

        @work(thread=True)
        def _process_message(self, msg: str) -> None:
            self.call_from_thread(self._set_processing, True)
            self._process_message_worker(msg)

        @on(Input.Submitted, "#user-input")
        def on_input_submitted(self, event: Input.Submitted) -> None:
            msg = event.value.strip()
            if not msg:
                return
            if self._processing:
                self._log_system("Still working on the last message…")
                self._focus_input()
                return
            self._input().value = ""
            if self._handle_slash(msg):
                self._focus_input()
                return
            self._log_user(msg)
            self._process_message(msg)

        @on(Button.Pressed, "#btn-help")
        def _btn_help(self) -> None:
            self.action_help()
            self._focus_input()

        @on(Button.Pressed, "#btn-clear")
        def _btn_clear(self) -> None:
            self.action_clear()
            self._focus_input()

        @on(Button.Pressed, "#btn-memory")
        def _btn_memory(self) -> None:
            self.action_memory()
            self._focus_input()

        @on(Button.Pressed, "#mic-btn")
        def _btn_mic(self) -> None:
            self.action_toggle_mic()

        @on(Button.Pressed, "#tts-btn")
        def _btn_tts(self) -> None:
            self.action_toggle_tts()
            self._focus_input()

        @on(Button.Pressed, "#btn-quit")
        def _btn_quit(self) -> None:
            self.exit()

        def on_focus(self, event: Focus) -> None:
            if getattr(event.control, "id", None) == "user-input":
                self._chat().scroll_end(animate=False)

        def action_focus_input(self) -> None:
            if self._processing:
                self._log_system("Still working… input unlocks when Chahlie finishes.")
                return
            self._focus_input()

        def action_help(self) -> None:
            self._log_system(
                "[bold]Deck commands[/]: /help /clear /memory /voice /tts /key /quit\n"
                "[bold]Keys[/]: F1 Help · F2 Clear · F3 Memory · F4 Talk · F5 TTS · F7 Type\n"
                "[bold]Steam Input[/]: map A→Enter, B→Esc, X→F4, Y→F1, Start→F7 for typing"
            )

        def action_clear(self) -> None:
            if self.agent:
                self.agent.reset()
            self._chat().clear()
            self._log_system("Conversation cleared.")
            self._refresh_status()

        def action_memory(self) -> None:
            if not self.agent or not self.agent.memory:
                self._log_system("Memory disabled.")
                return
            s = self.agent.get_memory_summary()["summary"]
            self._log_system(
                f"Sessions: {s['total_sessions']} · "
                f"Learnings: {s['total_learnings']} · "
                f"Reflections: {s['total_reflections']}"
            )

        def action_toggle_tts(self) -> None:
            self._tts_on = not self._tts_on
            state = "on" if self._tts_on else "off"
            self._log_system(f"Text-to-speech {state}.")
            if not self._tts_on:
                self.voice.stop_speaking()
            self._refresh_status()

        def action_stop_speech(self) -> None:
            self.voice.stop_speaking()
            self._log_system("Stopped speaking.")

        def action_toggle_mic(self) -> None:
            if self._listening:
                return
            if not self.voice.can_listen:
                self._log_error(
                    "Mic not available — just type your message below instead."
                )
                return
            self._start_listen()

        @work(thread=True)
        def _start_listen(self) -> None:
            self._listening = True
            self.call_from_thread(self._set_mic_listening, True)
            try:
                def status(s: str) -> None:
                    self.call_from_thread(self._log_system, f"🎤 {s}…")

                text = self.voice.listen(on_status=status)
                self.call_from_thread(self._on_voice_result, text)
            except Exception as exc:
                self.call_from_thread(self._log_error, str(exc))
            finally:
                self._listening = False
                self.call_from_thread(self._set_mic_listening, False)

        def _set_mic_listening(self, on: bool) -> None:
            btn = self.query_one("#mic-btn", Button)
            btn.add_class("listening") if on else btn.remove_class("listening")
            btn.label = "🎤 Listening…" if on else "🎤 Talk"

        def _on_voice_result(self, text: str) -> None:
            if not text.strip():
                self._focus_input()
                return
            if self._processing:
                self._log_system("Still working on the last message…")
                self._focus_input()
                return
            self._log_user(f"🎤 {text}")
            if self._handle_slash(text):
                self._focus_input()
                return
            self._process_message(text)


def run_deck() -> None:
    if not TEXTUAL_AVAILABLE:
        from . import ui
        ui.print_error(
            "Steam Deck UI needs Textual:\n"
            "    pip install textual"
        )
        return
    ChahlieDeckApp().run()
