import os
import sys
import asyncio
import uuid
import click
import time
import logging
from dotenv import load_dotenv, set_key
from rich.align import Align
from rich.console import Console, Group
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Suppress debug logs from other libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

console = Console()

HELP_TEXT = """
[bold cyan]SPECTRA CLI[/bold cyan]

[bold]Description:[/bold]
A multi-agent AI pipeline that audits any local codebase or GitHub repository, 
detects bugs & vulnerabilities across the full stack, and generates professional 
Markdown and PDF audit reports.

[bold]How to Setup & Run:[/bold]
1. Navigate to the project directory you want to audit.
2. Run [green]spectra[/green] in your terminal.
3. The CLI will automatically create a [cyan].spectra[/cyan] folder and a template [cyan].env[/cyan] file.
4. The CLI will pause and instruct you to open the [cyan].env[/cyan] file to add your API Key and Model.
5. After saving the file, run [green]spectra[/green] again to start the audit.

[bold]Commands:[/bold]
  [green]spectra[/green]                  Run interactive audit in the current directory.
  [green]spectra -d <path>[/green]      Run audit on a specific directory.
  [green]spectra -help[/green]          Show this help message and exit.

[bold]Generated Reports:[/bold]
Reports will be saved locally, and the exact links to the [cyan].md[/cyan] and [cyan].pdf[/cyan] files 
will be provided at the end of the run.
"""

CONFIG_DIR_NAME = ".spectra"

def show_intro():
    console.clear()
    
    letters = ["S", "P", "E", "C", "T", "R", "A"]
    # Aesthetic modern gradient (Cyan to Deep Blue/Purple)
    colors = ["#00f2fe", "#00dcf9", "#00c6f4", "#00b0ef", "#009aea", "#0084e5", "#006ee0"]
    
    logo = Text()
    logo.justify = "center"
    
    # Clean Reveal Animation
    for i in range(len(letters)):
        sys.stdout.write("\033[H\033[J")
        sys.stdout.flush()
        logo.append(f" {letters[i]} ", style=f"bold {colors[i]}")
        
        panel = Panel(
            logo,
            border_style=colors[i],
            padding=(1, 4),
            expand=False
        )
        console.print(Align.center(panel))
        time.sleep(0.08)

    sys.stdout.write("\033[H\033[J")
    sys.stdout.flush()
    subtitle = Text("MULTI-AGENT CODEBASE AUDIT SYSTEM", style="dim #A0AEC0", justify="center")
    group = Group(logo, Text(""), subtitle)
    panel = Panel(
        group,
        border_style="#009aea",
        padding=(1, 6),
        expand=False
    )
    console.print(Align.center(panel))
    console.print("\n")

def setup_config(target_dir):
    config_dir = os.path.join(target_dir, CONFIG_DIR_NAME)
    env_file = os.path.join(config_dir, ".env")

    needs_user_edit = False

    if not os.path.exists(config_dir):
        with console.status("[bold green]Creating configuration directory...[/bold green]"):
            time.sleep(0.5)
            os.makedirs(config_dir, exist_ok=True)
            
        # Create template .env
        with open(env_file, 'w') as f:
            f.write("# OpenAI API Key Configuration\n")
            f.write("OPENAI_API_KEY=\n\n")
            f.write("# Select the OpenAI Model to use:\n")
            f.write("# - gpt-4o-mini (Fast & Cost-effective, Recommended)\n")
            f.write("# - gpt-4o      (High Performance & Accuracy)\n")
            f.write("# - gpt-5.4-mini (Latest / Future-proof)\n")
            f.write("OPENAI_MODEL=gpt-4o-mini\n")
            
        console.print(f"[green]OK[/green]  Created workspace at [bold]{config_dir}[/bold]")
        needs_user_edit = True
    else:
        console.print(f"[green]OK[/green]  Workspace found at [bold]{config_dir}[/bold]")
        # Load existing env vars
        load_dotenv(env_file)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.strip() == "":
            needs_user_edit = True

    if needs_user_edit:
        console.print()
        console.print("[bold yellow]Setup required[/bold yellow]")
        console.print("Add your OpenAI key before running the audit.")

        console.print()
        console.print(f"  [cyan]config[/cyan]  {env_file}")
        console.print("  [cyan]key[/cyan]     OPENAI_API_KEY=sk-your-openai-api-key")
        console.print("  [cyan]model[/cyan]   OPENAI_MODEL=gpt-4o-mini")
        console.print()
        console.print("[dim]Next: edit the config file, then run[/dim] [bold cyan]spectra[/bold cyan] [dim]again.[/dim]")
        sys.exit(0)

    # Force update current process env so the backend picks it up directly
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    os.environ["OPENAI_MODEL"] = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    os.environ["JOB_STORAGE_PATH"] = os.path.join(config_dir, "reports")

async def run_audit(target_dir: str):
    # Setup config in target directory
    setup_config(target_dir)

    # Now load the backend graph
    console.print("[bold blue]Initializing audit pipeline...[/bold blue]\n")
    from backend.graph.audit_graph import audit_graph, jobs_store
    
    job_id = str(uuid.uuid4())
    
    # Initialize job in store
    jobs_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress_percent": 0,
        "current_step": "Job created, queued for processing...",
        "agents_done": [],
        "agents_running": [],
        "agents_queued": [],
        "finding_counts": {"EXTREME": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "total_findings": 0,
        "error": None,
        "report_md_ready": False,
        "report_pdf_ready": False,
    }

    initial_state = {
        "job_id": job_id,
        "repo_url": "", 
        "repo_path": target_dir,
        "branch": "",
        "github_token": None,
        "include_patterns": [],
        "exclude_patterns": [
            "node_modules", ".git", "dist", "__pycache__", "venv", ".venv",
            ".spectra", ".env", ".env.*", "*.env",
        ],
        "max_files_per_agent": int(os.environ.get("MAX_FILES_PER_AGENT", 20)),
        "max_chunks_per_file": int(os.environ.get("MAX_CHUNKS_PER_FILE", 2)),
        "rate_limit_rpm": int(os.environ.get("OPENAI_RATE_LIMIT_RPM", 20)),
        "file_map": {},
        "agent_findings": {},
        "aggregated_findings": [],
        "report_md": "",
        "report_md_path": "",
        "report_pdf_path": "",
        "status": "queued",
        "current_step": "Starting audit...",
        "agents_done": [],
        "error": None,
    }

    task = asyncio.create_task(audit_graph.ainvoke(initial_state))

    with Progress(
        SpinnerColumn("dots12", style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, style="blue", complete_style="cyan"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        job_task = progress.add_task("[cyan]Starting...", total=100)
        
        while not task.done():
            status = jobs_store.get(job_id, {})
            pct = status.get("progress_percent", 0)
            step = status.get("current_step", "")
            state_val = status.get("status", "running")
            
            progress.update(job_task, completed=pct, description=f"[cyan]{state_val.capitalize()}:[/cyan] {step}")
            await asyncio.sleep(0.5)

        try:
            result = task.result()
            status = jobs_store.get(job_id, {})
            pct = status.get("progress_percent", 100)
            step = status.get("current_step", "Done")
            progress.update(job_task, completed=pct, description=f"[green]Done:[/green] {step}")
            
            if result.get("error"):
                console.print(f"\n[red]Error during audit:[/red] {result['error']}")
                sys.exit(1)
            
            console.print("\n[bold green]Audit Complete![/bold green]")
            counts = status.get("finding_counts", {})
            total = status.get("total_findings", 0)
            
            # Professional Summary Table
            summary_table = Table(title="[bold]Audit Summary[/bold]", show_header=False, box=None, padding=(0, 2))
            summary_table.add_column("Level", justify="right")
            summary_table.add_column("Count", justify="left")
            
            summary_table.add_row("[red]EXTREME[/red]", str(counts.get('EXTREME', 0)))
            summary_table.add_row("[dark_orange]HIGH[/dark_orange]", str(counts.get('HIGH', 0)))
            summary_table.add_row("[yellow]MEDIUM[/yellow]", str(counts.get('MEDIUM', 0)))
            summary_table.add_row("[blue]LOW[/blue]", str(counts.get('LOW', 0)))
            summary_table.add_row("", "")
            summary_table.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]")
            
            console.print(Panel(
                Align.center(summary_table),
                border_style="green",
                padding=(1, 2),
                expand=False
            ))
            
            md_path = result.get("report_md_path")
            pdf_path = result.get("report_pdf_path")

            # Report Links formatted cleanly
            if md_path and os.path.exists(md_path):
                console.print(f"\n[bold cyan]Markdown Report:[/bold cyan]\n   [link=file://{os.path.abspath(md_path)}]{os.path.abspath(md_path)}[/link]")
            if pdf_path and os.path.exists(pdf_path):
                console.print(f"\n[bold red]PDF Report:[/bold red]\n   [link=file://{os.path.abspath(pdf_path)}]{os.path.abspath(pdf_path)}[/link]")
            console.print("\n")
                
        except Exception as e:
            console.print(f"\n[red]Audit failed with exception:[/red] {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

@click.command(add_help_option=False)
@click.option('--dir', '-d', type=click.Path(exists=True, file_okay=False, dir_okay=True), default=".", help='Target directory to audit.')
@click.option('--help', '-help', '-h', is_flag=True, help='Show this message and exit.')
def main(dir, help):
    if help:
        console.print(HELP_TEXT)
        sys.exit(0)

    # Show intro animation
    show_intro()
    
    target_dir = os.path.abspath(dir)
    console.print(f"[magenta]Target Directory:[/magenta] [bold]{target_dir}[/bold]")

    # Run the async loop
    asyncio.run(run_audit(target_dir))

if __name__ == '__main__':
    main()
