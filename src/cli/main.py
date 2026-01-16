"""Command-line interface for AI content detection."""

import click
from pathlib import Path
from typing import Dict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.content_analyzer import ContentAnalyzer
from src.report.html_generator import HTMLReportGenerator
from src.utils.config import get_config
from src.utils.logger import get_logger
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="AI Content Detector")
def cli():
    """
    AI Content Detection System

    Detect AI-generated content in PDF documents including text, images, and tables.
    """
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "--pages",
    "-p",
    help="Page range to analyze (e.g., '1-10' or '5')",
    default=None,
)
@click.option(
    "--output",
    "-o",
    help="Output path for HTML report",
    default=None,
    type=click.Path(),
)
@click.option(
    "--no-progress",
    is_flag=True,
    help="Disable progress bars",
)
@click.option(
    "--config",
    "-c",
    help="Path to custom configuration file",
    default=None,
    type=click.Path(exists=True),
)
def analyze(pdf_path, pages, output, no_progress, config):
    """
    Analyze a PDF for AI-generated content.

    \b
    Examples:
      detect analyze document.pdf
      detect analyze document.pdf --pages 1-10
      detect analyze document.pdf --output report.html
    """
    try:
        console.print("\n[bold cyan]AI Content Detection System[/bold cyan]\n")

        # Initialize analyzer
        console.print("Initializing analyzer...")
        analyzer = ContentAnalyzer(config)
        console.print("✓ Analyzer initialized\n")

        # Analyze PDF
        console.print(f"[bold]Analyzing:[/bold] {pdf_path}")
        if pages:
            console.print(f"[bold]Pages:[/bold] {pages}")
        console.print()

        results = analyzer.analyze_pdf(
            pdf_path,
            page_range=pages,
            show_progress=not no_progress,
        )

        # Display summary
        _display_summary(results)

        # Generate HTML report
        if output is None:
            # Auto-generate output path
            pdf_name = Path(pdf_path).stem
            output_dir = Path("outputs/reports")
            output_dir.mkdir(parents=True, exist_ok=True)
            output = output_dir / f"{pdf_name}_report.html"

        console.print(f"\n[bold]Generating HTML report...[/bold]")
        generator = HTMLReportGenerator()
        report_path = generator.generate(results, str(output))
        console.print(f"✓ Report saved: [green]{report_path}[/green]\n")

        # Final message
        summary = results["summary"]
        if summary["ai_detected_pages"] > 0:
            console.print(
                f"[yellow]⚠ Warning: {summary['ai_detected_pages']} page(s) "
                f"contain AI-generated content![/yellow]"
            )
        else:
            console.print("[green]✓ No AI-generated content detected.[/green]")

        console.print()

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
def info(pdf_path):
    """
    Get basic information about a PDF.

    \b
    Example:
      detect info document.pdf
    """
    try:
        from src.core.page_processor import PageProcessor

        processor = PageProcessor()
        info_dict = processor.get_pdf_info(pdf_path)

        console.print(f"\n[bold]PDF Information:[/bold]\n")
        console.print(f"  Path: {info_dict['path']}")
        console.print(f"  Pages: {info_dict['page_count']}")
        console.print(f"  Size: {info_dict['file_size']:,} bytes\n")

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
        sys.exit(1)


@cli.command()
def config_show():
    """Show current configuration."""
    try:
        config = get_config()
        config_dict = config.to_dict()

        console.print("\n[bold]Current Configuration:[/bold]\n")

        # Text detection
        text_config = config_dict.get("text_detection", {})
        console.print("[cyan]Text Detection:[/cyan]")
        console.print(f"  Min words: {text_config.get('min_words', 50)}")

        detectors = text_config.get("detectors", {})
        console.print("  Detectors:")
        for name, det_config in detectors.items():
            enabled = det_config.get("enabled", False)
            weight = det_config.get("weight", 0)
            status = "✓" if enabled else "✗"
            console.print(f"    {status} {name}: weight={weight}")

        # Thresholds
        thresholds = config_dict.get("thresholds", {})
        console.print("\n[cyan]Thresholds:[/cyan]")
        console.print(f"  AI detection: {thresholds.get('ai_detection', 0.80):.0%}")
        console.print(f"  Confidence: {thresholds.get('confidence', 0.70):.0%}")

        # Output
        console.print("\n[cyan]Output:[/cyan]")
        console.print(f"  Reports: {config.get_output_dir('reports_dir')}")
        console.print(f"  Logs: {config.get_output_dir('logs_dir')}\n")

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
        sys.exit(1)


def _display_summary(results: Dict):
    """Display analysis summary."""
    summary = results["summary"]

    console.print("\n" + "=" * 70)
    console.print("[bold green]Analysis Complete![/bold green]")
    console.print("=" * 70 + "\n")

    # Summary table
    table = Table(title="Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="yellow")

    table.add_row("Total Pages", str(summary["total_pages"]))
    table.add_row("Pages Analyzed", str(summary["total_analyzed"]))
    table.add_row("Pages Failed", str(summary["total_failed"]))
    table.add_row("", "")

    ai_pages = summary["ai_detected_pages"]
    ai_pct = summary["ai_percentage"]

    if ai_pages > 0:
        table.add_row("AI Content Detected", f"[red]{ai_pages} ({ai_pct:.1f}%)[/red]")
    else:
        table.add_row("AI Content Detected", f"[green]None[/green]")

    console.print(table)
    console.print()

    # Elements summary
    elements = summary["elements"]
    elem_table = Table(title="Elements", show_header=True, header_style="bold cyan")
    elem_table.add_column("Type", style="cyan")
    elem_table.add_column("Analyzed", justify="right")
    elem_table.add_column("AI Detected", justify="right")

    elem_table.add_row(
        "Text",
        str(elements["text_elements"]),
        f"[red]{elements['ai_detected_text']}[/red]" if elements['ai_detected_text'] > 0 else "0"
    )
    elem_table.add_row(
        "Tables",
        str(elements["table_elements"]),
        f"[red]{elements['ai_detected_tables']}[/red]" if elements['ai_detected_tables'] > 0 else "0"
    )
    elem_table.add_row(
        "Images",
        str(elements["image_elements"]),
        "-"
    )

    console.print(elem_table)


if __name__ == "__main__":
    cli()
