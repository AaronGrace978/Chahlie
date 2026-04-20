"""
Chahlie's experimental Textual TUI.

Alternative entrypoint - same agent backend, but the UI is a proper terminal
app with a scrollable conversation log, live cost meter, and a dedicated
input box.

Launch with:  python -m chahlie --tui

Requires textual (`pip install textual`); not installed by default so the
classic rich-based CLI remains the zero-extra-dep happy path.
"""

from __future__ import annotations

from typing import Optional

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Footer, Header, Input, Log, Static
    from textual.reactive import reactive
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from . import ui  # reused for error printing only
from .agent import ChahlieAgent
from .tools import set_approval_hook


class _StatusBar(Static):
    """Top strip showing project, backend, and cost."""

    status_text = reactive("")

    def render(self):
        return self.status_text


if TEXTUAL_AVAILABLE:

    class ChahlieApp(App):
        """Textual-based Chahlie UI."""

        CSS = """
        Screen { background: #0C2340; }
        #status { dock: top; height: 1; background: #1E5631; color: white; padding: 0 1; }
        #log    { border: solid #BD3039; padding: 0 1; }
        #input  { dock: bottom; height: 3; border: solid #2ECC71; }
        """

        BINDINGS = [
            ("ctrl+c", "quit", "Quit"),
            ("ctrl+l", "clear", "Clear conversation"),
            ("ctrl+m", "memory", "Memory summary"),
        ]

        def __init__(self):
            super().__init__()
            self.agent: Optional[ChahlieAgent] = None

        def compose(self) -> ComposeResult:
            yield _StatusBar(id="status")
            yield Log(id="log", highlight=True)
            yield Input(placeholder="Type a message, or /help", id="input")
            yield Footer()

        def on_mount(self) -> None:
            set_approval_hook(self._approval_prompter)
            self.agent = ChahlieAgent()
            self._refresh_status()
            log = self.query_one("#log", Log)
            log.write_line("Chahlie TUI ready. Ctrl+C to quit, Ctrl+L to clear, Ctrl+M for memory.")
            primer = self.agent.get_primer_summary()
            if primer.get("primed"):
                log.write_line(
                    f"Project: {primer.get('name')} "
                    f"({primer.get('language','?')} / {primer.get('framework','?')})"
                )

        def _refresh_status(self) -> None:
            if not self.agent:
                return
            c = self.agent.get_cost_summary()
            status = self.query_one("#status", _StatusBar)
            status.status_text = (
                f"Chahlie v2.2 | backend={c['backend']} | model={c['model']} | "
                f"{c['formatted']}"
            )

        def _approval_prompter(self, command: str, reason: str) -> bool:
            """In TUI we can't easily block for a modal; default to DENY and log."""
            log = self.query_one("#log", Log)
            log.write_line(f"[APPROVAL DENIED] {reason}: {command}")
            log.write_line("Re-run with CHAHLIE_REQUIRE_APPROVAL=false or use the classic CLI for interactive approval.")
            return False

        async def on_input_submitted(self, event: Input.Submitted) -> None:
            msg = event.value.strip()
            if not msg:
                return
            log = self.query_one("#log", Log)
            input_widget = self.query_one("#input", Input)
            input_widget.value = ""

            if msg == "/quit" or msg == "/exit":
                self.exit()
                return
            if msg == "/clear":
                self.action_clear()
                return

            log.write_line(f"you> {msg}")
            streaming = False
            buffer = ""
            for evt in self.agent.process(msg):
                if evt.type == "text":
                    if evt.data and evt.data.get("streaming"):
                        buffer += evt.content
                        streaming = True
                    else:
                        log.write_line(f"chahlie> {evt.content}")
                elif evt.type == "tool_use":
                    if streaming and buffer:
                        log.write_line(f"chahlie> {buffer}")
                        buffer = ""
                        streaming = False
                    log.write_line(f"  [tool] {evt.data.get('tool')}")
                elif evt.type == "tool_result":
                    ok = "OK" if evt.data.get("success") else "FAIL"
                    log.write_line(f"  [{ok}] {str(evt.content)[:200]}")
                elif evt.type == "reflection":
                    log.write_line(f"  [learn] {evt.content}")
                elif evt.type == "error":
                    log.write_line(f"  [error] {evt.content}")
                elif evt.type == "cost":
                    log.write_line(f"  [cost] {evt.content}")
            if streaming and buffer:
                log.write_line(f"chahlie> {buffer}")
            self._refresh_status()

        def action_clear(self) -> None:
            if self.agent:
                self.agent.reset()
            log = self.query_one("#log", Log)
            log.clear()
            log.write_line("Conversation cleared.")
            self._refresh_status()

        def action_memory(self) -> None:
            if not self.agent or not self.agent.memory:
                return
            summary = self.agent.get_memory_summary()["summary"]
            log = self.query_one("#log", Log)
            log.write_line(
                f"[memory] sessions={summary['total_sessions']} "
                f"learnings={summary['total_learnings']} "
                f"reflections={summary['total_reflections']}"
            )


def run_tui() -> None:
    if not TEXTUAL_AVAILABLE:
        ui.print_error(
            "The TUI requires the 'textual' package. Install with:\n"
            "    pip install textual"
        )
        return
    ChahlieApp().run()
