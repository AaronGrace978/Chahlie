"""
Chahlie - The Boston Coding Agent
Entry point for running as a module: python -m chahlie
"""

import sys
import click

from .agent import ChahlieAgent, AgentEvent
from .config import BACKEND, ANTHROPIC_API_KEY, OLLAMA_HOST, OLLAMA_MODEL
from . import ui


def check_backend():
    """Check if the configured backend is available"""
    if BACKEND == "anthropic":
        if not ANTHROPIC_API_KEY:
            ui.print_error(
                "Anthropic backend selected but no API key found!\n\n"
                "Either set your Anthropic API key:\n"
                "  ANTHROPIC_API_KEY=your-key-here\n\n"
                "Or switch to Ollama (recommended for local use):\n"
                "  CHAHLIE_BACKEND=ollama"
            )
            return False
    else:
        # Check if Ollama is running
        import requests
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            response.raise_for_status()
        except:
            ui.print_error(
                f"Can't connect to Ollama at {OLLAMA_HOST}\n\n"
                "Make sure Ollama is running:\n"
                "  ollama serve\n\n"
                "And pull a model:\n"
                f"  ollama pull {OLLAMA_MODEL}"
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
    if BACKEND == "ollama":
        ui.console.print(f"[dim]🦙 Using Ollama: {OLLAMA_MODEL}[/dim]\n")
    else:
        ui.console.print(f"[dim]🤖 Using Anthropic Claude[/dim]\n")
    
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
                elif command == "/model":
                    if BACKEND == "ollama":
                        ui.console.print(f"[cyan]Model:[/cyan] {OLLAMA_MODEL} (Ollama)\n")
                    else:
                        ui.console.print(f"[cyan]Model:[/cyan] Claude (Anthropic)\n")
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
@click.option("--backend", "-b", type=click.Choice(["ollama", "anthropic"]), help="Backend to use")
@click.option("--model", "-m", help="Model to use (for Ollama)")
def main(version: bool, about: bool, backend: str, model: str):
    """
    Chahlie - The Boston Coding Agent
    
    An agentic AI coding assistant with authentic Boston personality.
    Official product of Cursor Boston.
    """
    import os
    
    if version:
        from . import __version__, __codename__
        click.echo(f"Chahlie v{__version__} \"{__codename__}\"")
        click.echo("Official Product of Cursor Boston")
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
