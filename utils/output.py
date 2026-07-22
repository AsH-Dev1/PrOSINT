from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

console = Console()


def print_banner():
    banner = """
╔══════════════════════════════════════════╗
║  ██████╗ ██████╗   ██████╗ ███████╗██╗███╗   ██╗████████╗ ║
║  ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝ ║
║  ██████╔╝██████╔╝██║   ██║███████╗██║██╔██╗ ██║   ██║    ║
║  ██╔═══╝ ██╔══██╗██║   ██║╚════██║██║██║╚██╗██║   ██║    ║
║  ██║     ██║  ██║╚██████╔╝███████║██║██║ ╚████║   ██║    ║
║  ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝    ║
╚══════════════════════════════════════════╝
     OSINT Multi-Source Tool v1.0
"""
    rprint(f"[bold cyan]{banner}[/bold cyan]")


def print_table(title, rows, columns=None, style="cyan"):
    if columns is None and rows:
        columns = list(rows[0].keys()) if isinstance(rows[0], dict) else ["Key", "Value"]

    table = Table(title=f"[bold {style}]{title}[/bold {style}]", title_justify="left")
    for col in columns:
        table.add_column(str(col), style=f"dim {style}")

    for row in rows:
        if isinstance(row, dict):
            table.add_row(*[str(v) for v in row.values()])
        else:
            table.add_row(*[str(v) for v in row])

    console.print(table)


def print_success(msg):
    rprint(f"[bold green][+][/bold green] {msg}")


def print_error(msg):
    rprint(f"[bold red][-][/bold red] {msg}")


def print_info(msg):
    rprint(f"[bold blue][*][/bold blue] {msg}")


def print_warning(msg):
    rprint(f"[bold yellow][!][/bold yellow] {msg}")


def print_section(title):
    rprint(f"\n[bold underline]{title}[/bold underline]")


def print_panel(content, title="", style="cyan"):
    console.print(Panel(content, title=title, border_style=style))


def print_json(data):
    import json
    rprint(json.dumps(data, indent=2, ensure_ascii=False))


def print_results(results, module_name):
    print_section(f"Results: {module_name}")

    if isinstance(results, list):
        if not results:
            print_warning("No results found.")
            return
        if isinstance(results[0], dict):
            print_table(f"{module_name} Results", results)
        else:
            for r in results:
                rprint(f"  [dim]-[/dim] {r}")
    elif isinstance(results, dict):
        rows = [{"Key": k, "Value": str(v)[:200]} for k, v in results.items()]
        print_table(f"{module_name} Results", rows)
    else:
        rprint(str(results))


def create_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    )
