"""
Chahlie - The Boston Coding Agent
Entry point for running as a module: python -m chahlie
NOW WITH MEMORY AND SELF-IMPROVEMENT!
"""

import sys
import click

from rich.console import Console
from rich.panel import Panel
from rich import box

from .agent import ChahlieAgent, AgentEvent
from .config import (
    BACKEND, ANTHROPIC_API_KEY,
    OLLAMA_CLOUD_HOST, OLLAMA_CLOUD_API_KEY, OLLAMA_LOCAL_HOST, OLLAMA_MODEL,
)
from .tools import set_approval_hook
from . import ui


def _approval_prompter(command: str, reason: str) -> bool:
    """Interactive approval for dangerous commands."""
    ui.console.print()
    ui.console.print(Panel(
        f"[bold yellow]APPROVAL NEEDED[/bold yellow]\n\n"
        f"Chahlie wants to run a command flagged as: [red]{reason}[/red]\n\n"
        f"[white]$ {command}[/white]\n\n"
        f"[dim]Only approve if you're sure. Ctrl+C to abort entirely.[/dim]",
        title="[yellow]SAFETY[/yellow]",
        border_style="yellow",
        box=box.ROUNDED,
    ))
    try:
        answer = input("Approve? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


console = Console()


def check_backend():
    """Check if the configured backend is available"""
    if BACKEND == "anthropic":
        if not ANTHROPIC_API_KEY:
            ui.print_error(
                "Anthropic backend selected but no API key found!\n\n"
                "Either set your Anthropic API key:\n"
                "  ANTHROPIC_API_KEY=your-key-here\n\n"
                "Or switch to Ollama Cloud (recommended):\n"
                "  CHAHLIE_BACKEND=ollama-cloud"
            )
            return False
    elif BACKEND == "ollama-cloud":
        if not OLLAMA_CLOUD_API_KEY:
            ui.print_error(
                "Ollama Cloud selected but no API key found!\n\n"
                "Get your API key from:\n"
                "  https://ollama.com/settings/keys\n\n"
                "Then set it in your .env file:\n"
                "  OLLAMA_API_KEY=your-key-here"
            )
            return False
    else:  # ollama-local
        import requests
        try:
            response = requests.get(f"{OLLAMA_LOCAL_HOST}/api/tags", timeout=5)
            response.raise_for_status()
        except:
            ui.print_error(
                f"Can't connect to Ollama at {OLLAMA_LOCAL_HOST}\n\n"
                "Make sure Ollama is running:\n"
                "  ollama serve\n\n"
                "And pull a model:\n"
                f"  ollama pull {OLLAMA_MODEL}\n\n"
                "Or switch to Ollama Cloud:\n"
                "  CHAHLIE_BACKEND=ollama-cloud"
            )
            return False
    return True


def run_interactive():
    """Run Chahlie in interactive mode"""
    # Check backend
    if not check_backend():
        sys.exit(1)
    
    # Initialize
    ui.clear_screen()
    ui.print_banner()
    
    # Show which backend we're using
    if BACKEND == "ollama-cloud":
        ui.console.print(f"[dim]☁️ Using Ollama Cloud: {OLLAMA_MODEL}[/dim]\n")
    elif BACKEND == "ollama-local":
        ui.console.print(f"[dim]🦙 Using Local Ollama: {OLLAMA_MODEL}[/dim]\n")
    else:
        ui.console.print(f"[dim]🤖 Using Anthropic Claude[/dim]\n")
    
    # Show memory status
    ui.console.print("[dim green]🧠 Memory System: ENABLED[/dim green]")
    ui.console.print("[dim]Chahlie will learn from every interaction![/dim]\n")
    
    ui.print_greeting()

    set_approval_hook(_approval_prompter)
    agent = ChahlieAgent()

    # Show primer summary (one-liner) if we detected something useful
    primer = agent.get_primer_summary()
    if primer.get("primed"):
        bits = []
        if primer.get("language"):
            bits.append(primer["language"])
        if primer.get("framework"):
            bits.append(primer["framework"])
        if primer.get("branch"):
            bits.append(f"@ {primer['branch']}")
        if bits:
            ui.console.print(f"[dim cyan]Project: {primer['name']} ({' / '.join(bits)})[/dim cyan]\n")

    if agent.plugin_warnings:
        for w in agent.plugin_warnings:
            ui.console.print(f"[dim yellow]plugin: {w}[/dim yellow]")
    
    # Main loop
    while True:
        try:
            user_input = ui.print_user_prompt()
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                command = user_input.lower().strip()
                
                if command == "/exit" or command == "/quit":
                    # Show memory summary before exit
                    if agent.memory:
                        summary = agent.get_memory_summary()
                        if summary["enabled"]:
                            ui.console.print("\n[cyan]📊 Session Summary:[/cyan]")
                            ui.console.print(f"  Sessions: {summary['summary']['total_sessions']}")
                            ui.console.print(f"  Learnings: {summary['summary']['total_learnings']}")
                            ui.console.print(f"  Reflections: {summary['summary']['total_reflections']}")
                    
                    ui.print_goodbye()
                    break
                elif command == "/help":
                    ui.print_help()
                    continue
                elif command == "/clear":
                    agent.reset()
                    ui.clear_screen()
                    ui.print_banner()
                    ui.console.print("[dim]Conversation cleared.[/dim]\n")
                    continue
                elif command == "/fact":
                    ui.print_fact()
                    continue
                elif command == "/about":
                    ui.print_about()
                    continue
                elif command == "/cursorboston" or command == "/cb":
                    ui.print_cursor_boston()
                    continue
                elif command == "/providers":
                    ui.print_providers()
                    continue
                elif command == "/model":
                    if BACKEND == "ollama-cloud":
                        ui.console.print(f"[cyan]Model:[/cyan] {OLLAMA_MODEL} (Ollama Cloud)\n")
                    elif BACKEND == "ollama-local":
                        ui.console.print(f"[cyan]Model:[/cyan] {OLLAMA_MODEL} (Local Ollama)\n")
                    else:
                        ui.console.print(f"[cyan]Model:[/cyan] Claude (Anthropic)\n")
                    continue
                elif command == "/memory" or command == "/mem":
                    # NEW COMMAND - Show memory status
                    summary = agent.get_memory_summary()
                    if summary["enabled"]:
                        top_learnings = summary['summary']['top_learnings'][:5]
                        learnings_text = "\n".join(f"• {l['pattern'][:60]}..." for l in top_learnings) if top_learnings else "No learnings yet, kehd!"
                        
                        console.print(Panel(
                            f"""[bold cyan]🧠 CHAHLIE MEMORY STATUS[/bold cyan]

[white]Sessions:[/white] {summary['summary']['total_sessions']}
[white]Learnings:[/white] {summary['summary']['total_learnings']}
[white]Reflections:[/white] {summary['summary']['total_reflections']}
[white]Has Context:[/white] {summary['summary']['has_context']}

[bold yellow]Recent Learnings:[/bold yellow]
{learnings_text}

[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]
[dim]Chahlie is learning from every interaction![/dim]
                            """,
                            title="[green]MEMORY[/green]",
                            border_style="green",
                            box=box.ROUNDED
                        ))
                    else:
                        ui.console.print("[yellow]Memory is disabled[/yellow]\n")
                    continue
                elif command == "/profile":
                    # NEW COMMAND - Show user profile
                    profile_summary = agent.get_memory_summary()
                    if profile_summary["enabled"]:
                        profile = profile_summary["user_profile"]
                        
                        coding_style = "\n".join(f"• {v}" for v in profile['coding_style'].values()) if profile['coding_style'] else "Still learning..."
                        communication = "\n".join(f"• {v}" for v in profile['communication_style'].values()) if profile['communication_style'] else "Still learning..."
                        workflow = "\n".join(f"• {v}" for v in profile['workflow'].values()) if profile['workflow'] else "Still learning..."
                        
                        console.print(Panel(
                            f"""[bold cyan]📋 YOUR CODING PROFILE[/bold cyan]

[bold yellow]Coding Style:[/bold yellow]
{coding_style}

[bold yellow]Communication:[/bold yellow]
{communication}

[bold yellow]Workflow:[/bold yellow]
{workflow}

[white]Confidence:[/white] {profile['confidence']:.0%}

[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]
[dim]The more we work together, the better I know ya![/dim]
                            """,
                            title="[green]PROFILE[/green]",
                            border_style="green",
                            box=box.ROUNDED
                        ))
                    else:
                        ui.console.print("[yellow]Memory is disabled[/yellow]\n")
                    continue
                elif command == "/reflect":
                    # NEW COMMAND - Show self-reflection
                    if agent.reflection_engine:
                        plan = agent.reflection_engine.generate_improvement_plan()
                        
                        focus_areas = "\n".join(f"• {area['area'][:50]} ({area['priority']} priority)" for area in plan['focus_areas']) if plan['focus_areas'] else "Looking good, kehd!"
                        strengths = "\n".join(f"• {area['area'][:50]}" for area in plan['continue_doing']) if plan['continue_doing'] else "Building the list..."
                        
                        console.print(Panel(
                            f"""[bold cyan]🤔 CHAHLIE'S SELF-REFLECTION[/bold cyan]

[bold yellow]Focus Areas (what I'm working on):[/bold yellow]
{focus_areas}

[bold green]Keep Doing (my strengths):[/bold green]
{strengths}

[white]Reflections Analyzed:[/white] {plan['total_reflections_analyzed']}

[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]
[dim]Always improvin', always learnin'![/dim]
                            """,
                            title="[green]REFLECTION[/green]",
                            border_style="green",
                            box=box.ROUNDED
                        ))
                    else:
                        ui.console.print("[yellow]Memory is disabled[/yellow]\n")
                    continue
                elif command == "/learnings":
                    # NEW COMMAND - Show all learnings
                    if agent.memory:
                        learnings = agent.memory.get_learnings()
                        if learnings:
                            ui.console.print(f"[bold cyan]📚 ALL LEARNINGS ({len(learnings)} total)[/bold cyan]\n")
                            for i, learning in enumerate(learnings[-10:], 1):  # Last 10
                                ui.console.print(f"[dim]{i}.[/dim] [{learning.category}] {learning.pattern}")
                                ui.console.print(f"   [dim]Confidence: {learning.confidence:.0%} | Seen: {learning.times_seen}x[/dim]\n")
                        else:
                            ui.console.print("[yellow]No learnings yet, kehd. Let's get to work![/yellow]\n")
                    continue
                elif command == "/cost":
                    c = agent.get_cost_summary()
                    ui.console.print(Panel(
                        f"[bold cyan]TOKEN / COST METER[/bold cyan]\n\n"
                        f"Backend: [white]{c['backend']}[/white]\n"
                        f"Model:   [white]{c['model']}[/white]\n"
                        f"Input:   [white]{c['input_tokens']:,} tokens[/white]\n"
                        f"Output:  [white]{c['output_tokens']:,} tokens[/white]\n"
                        f"Est:     [green]${c['cost_usd']:.4f}[/green] this session\n",
                        title="[green]COST[/green]", border_style="green", box=box.ROUNDED,
                    ))
                    continue
                elif command == "/primer" or command == "/project":
                    p = agent.get_primer_summary()
                    if not p.get("primed"):
                        ui.console.print("[yellow]No project context detected.[/yellow]\n")
                        continue
                    layout = "\n".join(f"  {row}" for row in (p.get("layout") or [])[:15])
                    ui.console.print(Panel(
                        f"[bold cyan]PROJECT PRIMER[/bold cyan]\n\n"
                        f"Name: [white]{p.get('name')}[/white]\n"
                        f"Path: [dim]{p.get('path')}[/dim]\n"
                        f"Language:  [white]{p.get('language') or '(unknown)'}[/white]\n"
                        f"Framework: [white]{p.get('framework') or '(none detected)'}[/white]\n"
                        f"Branch:    [white]{p.get('branch') or '(no git)'}[/white]\n\n"
                        f"[bold]Top-level:[/bold]\n{layout}",
                        title="[green]PROJECT[/green]", border_style="green", box=box.ROUNDED,
                    ))
                    continue
                elif command == "/plugins":
                    if not agent.plugin_definitions and not agent.plugin_warnings:
                        ui.console.print("[dim]No plugins loaded. Drop .py files in ~/.chahlie/plugins/[/dim]\n")
                        continue
                    names = ", ".join(d.get("name", "?") for d in agent.plugin_definitions) or "(none)"
                    warns = "\n".join(f"  • {w}" for w in agent.plugin_warnings) or "  (none)"
                    ui.console.print(Panel(
                        f"[bold cyan]PLUGINS[/bold cyan]\n\n"
                        f"Loaded tools: [white]{names}[/white]\n\n"
                        f"[bold yellow]Warnings:[/bold yellow]\n{warns}",
                        title="[green]PLUGINS[/green]", border_style="green", box=box.ROUNDED,
                    ))
                    continue
                else:
                    ui.console.print(f"[dim]Unknown command: {command}. Type /help for commands.[/dim]\n")
                    continue
            
            # Process with agent
            ui.console.print()

            streaming_started = False

            def _end_stream_if_needed():
                nonlocal streaming_started
                if streaming_started:
                    ui.console.print()  # newline after the live-streamed text
                    streaming_started = False

            for event in agent.process(user_input):
                if event.type == "thinking":
                    _end_stream_if_needed()
                    ui.print_thinking(event.content)
                elif event.type == "text":
                    if event.data and event.data.get("streaming"):
                        if not streaming_started:
                            ui.console.print("[bold green]Chahlie:[/bold green] ", end="")
                            streaming_started = True
                        ui.console.print(event.content, end="", highlight=False)
                    else:
                        _end_stream_if_needed()
                        ui.print_agent_message(event.content)
                elif event.type == "tool_use":
                    _end_stream_if_needed()
                    ui.print_tool_use(event.data["tool"], event.data["input"])
                elif event.type == "tool_result":
                    _end_stream_if_needed()
                    ui.print_tool_result(
                        event.data["tool"], event.data["success"],
                        event.data["output"], event.data.get("error"),
                    )
                elif event.type == "reflection":
                    _end_stream_if_needed()
                    ui.console.print(f"[dim cyan]💡 {event.content}[/dim cyan]\n")
                elif event.type == "cost":
                    _end_stream_if_needed()
                    ui.console.print(f"[dim]💰 {event.content}[/dim]\n")
                elif event.type == "error":
                    _end_stream_if_needed()
                    ui.print_error(event.content)
            _end_stream_if_needed()
        
        except KeyboardInterrupt:
            ui.console.print("\n")
            ui.print_goodbye()
            break
        except Exception as e:
            ui.print_error(f"Unexpected error: {str(e)}")


@click.command()
@click.option("--version", "-v", is_flag=True, help="Show version and exit")
@click.option("--about", "-a", is_flag=True, help="Show about information")
@click.option("--backend", "-b", type=click.Choice(["ollama-cloud", "ollama-local", "anthropic"]), help="Backend to use")
@click.option("--model", "-m", help="Model to use (for Ollama)")
@click.option("--no-memory", is_flag=True, help="Disable memory system")
@click.option("--no-stream", is_flag=True, help="Disable token streaming")
@click.option("--no-approval", is_flag=True, help="Disable approval prompts for dangerous commands (NOT recommended)")
@click.option("--llm-reflection", is_flag=True, help="Enable LLM-based reflection on failures")
@click.option("--semantic-memory", is_flag=True, help="Enable semantic (embedding) memory retrieval")
@click.option("--tui", is_flag=True, help="Launch the experimental Textual TUI instead of the classic CLI")
def main(version, about, backend, model, no_memory, no_stream, no_approval, llm_reflection, semantic_memory, tui):
    """
    Chahlie - The Boston Coding Agent
    
    An agentic AI coding assistant with authentic Boston personality.
    Official product of Cursor Boston.
    
    NOW WITH MEMORY AND SELF-IMPROVEMENT!
    """
    import os
    
    if version:
        from . import __version__, __codename__
        click.echo(f"Chahlie v{__version__} \"{__codename__}\"")
        click.echo("Official Product of Cursor Boston")
        click.echo("🧠 Memory System: ENABLED")
        return
    
    if about:
        ui.print_about()
        return
    
    # Override backend/model/flags if specified
    if backend:
        os.environ["CHAHLIE_BACKEND"] = backend
    if model:
        os.environ["OLLAMA_MODEL"] = model
    if no_stream:
        os.environ["CHAHLIE_STREAMING"] = "false"
    if no_approval:
        os.environ["CHAHLIE_REQUIRE_APPROVAL"] = "false"
    if llm_reflection:
        os.environ["CHAHLIE_LLM_REFLECTION"] = "true"
    if semantic_memory:
        os.environ["CHAHLIE_SEMANTIC_MEMORY"] = "true"

    # Reload config
    from importlib import reload
    from . import config
    reload(config)

    if tui:
        try:
            from .tui import run_tui  # lazy import - Textual is optional
        except ImportError:
            ui.print_error(
                "Textual isn't installed. Run:  pip install textual\n"
                "Then try again with --tui."
            )
            sys.exit(1)
        run_tui()
        return

    run_interactive()


if __name__ == "__main__":
    main()
