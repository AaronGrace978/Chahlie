"""
Chahlie's Terminal UI
Beautiful, clean, Boston-styled interface
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    os.system("")  # Enable ANSI escape sequences

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
from rich import box

from .config import THEME, APP_NAME, APP_VERSION, APP_CODENAME, CREDITS, CURSOR_BOSTON, CURSOR
from .personality import get_greeting, get_boston_fact


console = Console(force_terminal=True)


# ASCII Art Banner with Boston Skyline
BANNER = r"""
[green]
     ██████╗██╗  ██╗ █████╗ ██╗  ██╗██╗     ██╗███████╗
    ██╔════╝██║  ██║██╔══██╗██║  ██║██║     ██║██╔════╝
    ██║     ███████║███████║███████║██║     ██║█████╗  
    ██║     ██╔══██║██╔══██║██╔══██║██║     ██║██╔══╝  
    ╚██████╗██║  ██║██║  ██║██║  ██║███████╗██║███████╗
     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝╚══════╝
[/green]"""

# Boston Skyline - Hancock, Prudential, Zakim Bridge
BOSTON_SKYLINE = r"""
[dim cyan]                          ___
                         |   |  ╱╲                    ╱╲
              ┌──┐       |   | ╱  ╲    ┌──┐         ╱  ╲
    ┌──┐      │▓▓│  ┌──┐ |   |╱    ╲   │▓▓│  ┌──┐  ╱    ╲
    │▓▓│ ┌──┐ │▓▓│  │▓▓│ |___|      ╲  │▓▓│  │▓▓│ ╱      ╲
────┴──┴─┴──┴─┴──┴──┴──┴─────────────╲─┴──┴──┴──┴╱────────────
    ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀ BOSTON ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀[/dim cyan]"""

CURSOR_BOSTON_LOGO = r"""
[bold cyan]
   ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗ 
  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗
  ██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝
  ██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗
  ╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
               B  O  S  T  O  N                      
[/bold cyan]"""


def print_banner():
    """Print the Chahlie banner with Boston skyline"""
    # Print the skyline first
    console.print(BOSTON_SKYLINE)
    
    # Print main Chahlie logo
    console.print(BANNER)
    
    # Tagline and version
    info = Table.grid(padding=0)
    info.add_column(justify="center")
    info.add_row(Text("The Boston Coding Agent", style="bold white"))
    info.add_row(Text(f"v{APP_VERSION} \"{APP_CODENAME}\"", style="dim"))
    info.add_row(Text(""))
    info.add_row(Text(f"Official Product of {CREDITS['organization']}", style="bold cyan"))
    info.add_row(Text(f"{CREDITS['founder_title']}: {CREDITS['founder']} | CMO: {CREDITS['cmo']}", style="dim cyan"))
    info.add_row(Text(""))
    info.add_row(Text("Made with Cursor - cursor.com", style="dim magenta"))
    
    console.print(Align.center(info))
    console.print()


def print_skyline():
    """Print Boston skyline ASCII art"""
    console.print(Text(BOSTON_SKYLINE, style="dim blue"))


def print_greeting():
    """Print a greeting message"""
    greeting = get_greeting()
    console.print(Panel(
        Text(greeting, style="bold white"),
        title="[green]CHAHLIE[/green]",
        border_style="green",
        box=box.ROUNDED
    ))
    console.print()


def print_help():
    """Print help information"""
    help_table = Table(
        title="Chahlie Commands",
        box=box.ROUNDED,
        border_style="green",
        title_style="bold green"
    )
    help_table.add_column("Command", style="cyan")
    help_table.add_column("Description", style="white")
    
    help_table.add_row("/help", "Show this help message")
    help_table.add_row("/clear", "Clear conversation history")
    help_table.add_row("/exit", "Exit Chahlie")
    help_table.add_row("/fact", "Get a random Boston fact")
    help_table.add_row("/about", "About Chahlie")
    help_table.add_row("/model", "Show current model")
    help_table.add_row("/providers", "View available AI providers")
    help_table.add_row("/cursorboston", "Learn about Cursor Boston!")
    help_table.add_row("")
    help_table.add_row("[bold green]🧠 MEMORY COMMANDS[/bold green]", "")
    help_table.add_row("/memory", "Show memory status and recent learnings")
    help_table.add_row("/profile", "View your learned coding profile")
    help_table.add_row("/reflect", "See Chahlie's self-reflection & improvement plan")
    help_table.add_row("/learnings", "View all learned patterns")
    
    console.print(help_table)
    console.print()
    console.print("[dim cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim cyan]")
    console.print("[bold]Chahlie[/bold] is an official product of [bold cyan]Cursor Boston[/bold cyan]")
    console.print("[dim]Boston's home for AI-powered development[/dim]")
    console.print("[dim green]🧠 NOW WITH MEMORY & SELF-IMPROVEMENT![/dim green]")
    console.print()


def print_about():
    """Print about information"""
    about = f"""
[bold green]CHAHLIE[/bold green] - The Boston Coding Agent
[dim]v{APP_VERSION} "{APP_CODENAME}"[/dim]

[bold cyan]== CURSOR BOSTON ==[/bold cyan]
{CURSOR_BOSTON['tagline']}

Chahlie is the official AI coding agent of [bold]Cursor Boston[/bold] - 
the community for Boston developers building with Cursor IDE.

[cyan]What Can Chahlie Do?[/cyan]
• Read, write, and search your codebase
• Run shell commands and manage your project
• Help with any coding task - wicked fast
• Do it all with authentic Boston personality
• [bold green]🧠 NEW: Learn from every interaction![/bold green]
• [bold green]🧠 NEW: Adapt to your coding style![/bold green]
• [bold green]🧠 NEW: Self-reflect and improve![/bold green]

[cyan]Leadership:[/cyan]
• [bold]{CREDITS['founder']}[/bold] - {CREDITS['founder_title']}
• [bold]{CREDITS['cmo']}[/bold] - Chief Media Officer

[bold yellow]━━━━━━━━━━━━ CONNECT ━━━━━━━━━━━━[/bold yellow]

[white]🌐 Cursor Boston:[/white]  [link={CURSOR_BOSTON['website']}]{CURSOR_BOSTON['website']}[/link]
[white]🐦 X/Twitter:[/white]      [link={CURSOR_BOSTON['x_twitter']}]{CURSOR_BOSTON['x_twitter']}[/link]
[white]💻 GitHub:[/white]         [link={CURSOR_BOSTON['github']}]{CURSOR_BOSTON['github']}[/link]

[bold magenta]━━━━━━━━━━ MADE WITH CURSOR ━━━━━━━━━━[/bold magenta]

[bold magenta]Cursor[/bold magenta] - {CURSOR['tagline']}
[white]🌐 Website:[/white]   [link={CURSOR['website']}]{CURSOR['website']}[/link]
[bold green]⬇️  Download:[/bold green]  [link={CURSOR['download']}]{CURSOR['download']}[/link]

[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]
[bold]Join the Cursor Boston community![/bold]
Boston's home for AI-powered development.
[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]

[dim italic]Built with love in Boston - Boston Strong![/dim italic]
"""
    console.print(Panel(
        about,
        title="[green]About Chahlie | Cursor Boston[/green]",
        border_style="green",
        box=box.DOUBLE
    ))


def print_fact():
    """Print a random Boston fact"""
    fact = get_boston_fact()
    console.print(Panel(
        Text(fact, style="italic"),
        title="[blue]Boston Fact[/blue]",
        border_style="blue",
        box=box.ROUNDED
    ))
    console.print()


def print_providers():
    """Print available AI providers"""
    providers = """
[bold cyan]Available AI Providers[/bold cyan]

Chahlie supports multiple AI backends. Configure in your [yellow].env[/yellow] file:

[bold green]1. Ollama Cloud (Recommended)[/bold green]
   Best for: Cloud-hosted models, no GPU required
   [dim]CHAHLIE_BACKEND=ollama-cloud
   OLLAMA_API_KEY=your-key-here
   OLLAMA_MODEL=glm-5.1[/dim]
   
   Top Models:
   • glm-5.1 - SOTA for agentic engineering
   • qwen3.5 - Multimodal powerhouse
   • devstral-small-2 - Multi-file editing expert
   • gemma4 - Frontier performance
   
   Get your API key: [link]https://ollama.com/settings/keys[/link]

[bold green]2. Local Ollama[/bold green]
   Best for: Privacy, offline use, local GPU
   [dim]CHAHLIE_BACKEND=ollama-local
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=qwen3:8b[/dim]
   
   Install: [link]https://ollama.com/download[/link]

[bold green]3. Anthropic Claude[/bold green]
   Best for: Claude fans, enterprise use
   [dim]CHAHLIE_BACKEND=anthropic
   ANTHROPIC_API_KEY=your-key-here[/dim]
   
   Get your API key: [link]https://console.anthropic.com[/link]

[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]
After changing .env, restart Chahlie to use the new provider.
"""
    console.print(Panel(
        providers,
        title="[bold cyan]AI Providers[/bold cyan]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()


def print_cursor_boston():
    """Print Cursor Boston info"""
    console.print(CURSOR_BOSTON_LOGO)
    
    info = f"""
[bold cyan]{CURSOR_BOSTON['tagline']}[/bold cyan]

{CURSOR_BOSTON['description']}

[yellow]Why Cursor Boston?[/yellow]
• Connect with Boston's AI developer community
• Learn tips & tricks for Cursor IDE
• Build awesome projects together
• Network with local tech talent

[bold yellow]━━━━━━━━━━━━ CONNECT WITH US ━━━━━━━━━━━━[/bold yellow]

[bold white]🌐 Website:[/bold white]     [link={CURSOR_BOSTON['website']}]{CURSOR_BOSTON['website']}[/link]
[bold white]🐦 X/Twitter:[/bold white]   [link={CURSOR_BOSTON['x_twitter']}]{CURSOR_BOSTON['x_twitter']}[/link]
[bold white]💻 GitHub:[/white]      [link={CURSOR_BOSTON['github']}]{CURSOR_BOSTON['github']}[/link]

[bold cyan]━━━━━━━━━━━━━━ CURSOR IDE ━━━━━━━━━━━━━━━[/bold cyan]

[bold white]Made with[/bold white] [bold magenta]Cursor[/bold magenta] - {CURSOR['tagline']}

[bold green]⬇️  DOWNLOAD CURSOR:[/bold green]  [link={CURSOR['download']}]{CURSOR['download']}[/link]
[bold white]🌐 Website:[/bold white]          [link={CURSOR['website']}]{CURSOR['website']}[/link]

[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]
  Chahlie is proud to represent Cursor Boston!
  Let's build somethin' wicked good together, kehd!
[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]
"""
    console.print(Panel(
        info,
        title="[bold cyan]CURSOR BOSTON[/bold cyan]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()


def print_thinking(message: str = "Thinking..."):
    """Print a thinking indicator"""
    console.print(f"[dim]> {message}[/dim]")


def print_agent_message(message: str):
    """Print a message from Chahlie"""
    console.print(Panel(
        Markdown(message),
        title="[green]CHAHLIE[/green]",
        border_style="green",
        box=box.ROUNDED
    ))
    console.print()


def print_tool_use(tool_name: str, tool_input: dict):
    """Print tool use information"""
    # Create a clean display of the tool call
    tool_display = Table.grid(padding=(0, 1))
    tool_display.add_column(style="cyan")
    tool_display.add_column(style="white")
    
    for key, value in tool_input.items():
        display_value = str(value)
        if len(display_value) > 60:
            display_value = display_value[:57] + "..."
        tool_display.add_row(f"{key}:", display_value)
    
    icon = get_tool_icon(tool_name)
    console.print(Panel(
        tool_display,
        title=f"[yellow]{icon} {tool_name}[/yellow]",
        border_style="yellow",
        box=box.ROUNDED
    ))


def print_tool_result(tool_name: str, success: bool, output: str, error: str = None):
    """Print tool result"""
    if success:
        display = output if len(output) < 500 else output[:500] + "\n... (truncated)"
        console.print(Panel(
            Text(display, style="green"),
            title=f"[green]+ {tool_name} succeeded[/green]",
            border_style="green",
            box=box.ROUNDED
        ))
    else:
        console.print(Panel(
            Text(error or "Unknown error", style="red"),
            title=f"[red]x {tool_name} failed[/red]",
            border_style="red",
            box=box.ROUNDED
        ))


def print_error(message: str):
    """Print an error message"""
    console.print(Panel(
        Text(message, style="bold red"),
        title="[red]Error[/red]",
        border_style="red",
        box=box.ROUNDED
    ))


def print_user_prompt():
    """Get user input with a styled prompt"""
    console.print()
    return console.input("[bold cyan]You:[/bold cyan] ")


def get_tool_icon(tool_name: str) -> str:
    """Get an icon for a tool"""
    icons = {
        "read_file": "[R]",
        "write_file": "[W]",
        "list_directory": "[D]",
        "search_files": "[S]",
        "search_content": "[?]",
        "run_command": "[>]",
        "create_directory": "[+]",
        "open_browser": "[B]",
        "web_search": "[G]",
    }
    return icons.get(tool_name, "[T]")


def clear_screen():
    """Clear the console"""
    console.clear()


def print_goodbye():
    """Print goodbye message"""
    console.print()
    goodbye_msg = """[bold green]See ya later, kehd! Keep writin' wicked good code![/bold green]

[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]
[cyan]Chahlie[/cyan] is brought to you by [bold]Cursor Boston[/bold]
Boston's home for AI-powered development.
[dim green]🧠 Memory System Active - I'll remember everything we built together![/dim green]
[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]"""
    console.print(Panel(
        goodbye_msg,
        title="[green]CHAHLIE | Cursor Boston[/green]",
        border_style="green",
        box=box.ROUNDED
    ))
    console.print()
