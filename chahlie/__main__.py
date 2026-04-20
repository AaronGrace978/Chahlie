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
    OLLAMA_CLOUD_HOST, OLLAMA_CLOUD_API_KEY, OLLAMA_LOCAL_HOST, OLLAMA_MODEL
)
from . import ui


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
    
    agent = ChahlieAgent()
    
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
                else:
                    ui.console.print(f"[dim]Unknown command: {command}. Type /help for commands.[/dim]\n")
                    continue
            
            # Process with agent
            ui.console.print()
            
            for event in agent.process(user_input):
                if event.type == "thinking":
                    ui.print_thinking(event.content)
                elif event.type == "text":
                    ui.print_agent_message(event.content)
                elif event.type == "tool_use":
                    ui.print_tool_use(
                        event.data["tool"],
                        event.data["input"]
                    )
                elif event.type == "tool_result":
                    ui.print_tool_result(
                        event.data["tool"],
                        event.data["success"],
                        event.data["output"],
                        event.data.get("error")
                    )
                elif event.type == "reflection":
                    # NEW - Show reflection events
                    ui.console.print(f"[dim cyan]💡 {event.content}[/dim cyan]\n")
                elif event.type == "error":
                    ui.print_error(event.content)
        
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
def main(version: bool, about: bool, backend: str, model: str, no_memory: bool):
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
    
    # Override backend/model if specified
    if backend:
        os.environ["CHAHLIE_BACKEND"] = backend
    if model:
        os.environ["OLLAMA_MODEL"] = model
    
    # Reload config
    from importlib import reload
    from . import config
    reload(config)
    
    run_interactive()


if __name__ == "__main__":
    main()
