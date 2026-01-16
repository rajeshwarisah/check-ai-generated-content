"""Test script for integrated PDF extraction + AI detection pipeline."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.content_analyzer import ContentAnalyzer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def test_integrated_pipeline(pdf_path: str, page_range: str = None):
    """
    Test the complete integrated pipeline.

    Args:
        pdf_path: Path to PDF file
        page_range: Optional page range (e.g., "1-5")
    """
    console.print("\n[bold cyan]Testing Integrated Pipeline: PDF → Extraction → AI Detection[/bold cyan]\n")

    try:
        # Initialize analyzer
        console.print("Initializing content analyzer...")
        analyzer = ContentAnalyzer()
        console.print("✓ Content analyzer initialized\n")

        # Analyze PDF
        console.print(f"[bold]Analyzing PDF:[/bold] {pdf_path}")
        if page_range:
            console.print(f"[bold]Page Range:[/bold] {page_range}")
        console.print()

        results = analyzer.analyze_pdf(pdf_path, page_range, show_progress=True)

        # Display summary
        console.print("\n" + "=" * 80)
        console.print("[bold green]Analysis Complete![/bold green]")
        console.print("=" * 80 + "\n")

        summary = results["summary"]

        # Summary table
        summary_table = Table(title="Analysis Summary", show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", justify="right", style="yellow")

        summary_table.add_row("Total Pages", str(summary["total_pages"]))
        summary_table.add_row("Pages Analyzed", str(summary["total_analyzed"]))
        summary_table.add_row("Pages Failed", str(summary["total_failed"]))
        summary_table.add_row("", "")
        summary_table.add_row(
            "Pages with AI Content",
            f"[red]{summary['ai_detected_pages']}[/red]"
        )
        summary_table.add_row(
            "AI Content Percentage",
            f"[red]{summary['ai_percentage']:.1f}%[/red]"
        )

        console.print(summary_table)
        console.print()

        # Elements summary
        elem_summary = summary["elements"]
        elements_table = Table(title="Elements Analyzed", show_header=True, header_style="bold cyan")
        elements_table.add_column("Element Type", style="cyan")
        elements_table.add_column("Total", justify="right")
        elements_table.add_column("AI Detected", justify="right", style="red")

        elements_table.add_row(
            "Text Blocks",
            str(elem_summary["text_elements"]),
            str(elem_summary["ai_detected_text"])
        )
        elements_table.add_row(
            "Tables",
            str(elem_summary["table_elements"]),
            str(elem_summary["ai_detected_tables"])
        )
        elements_table.add_row(
            "Images",
            str(elem_summary["image_elements"]),
            "[dim]Phase 3[/dim]"
        )

        console.print(elements_table)
        console.print()

        # Detailed page results
        console.print("[bold]Per-Page Analysis:[/bold]\n")

        for page in results["pages"]:
            page_num = page["page_number"]

            if page["status"] == "failed":
                console.print(f"[red]Page {page_num}: FAILED[/red]")
                console.print(f"  Error: {page.get('error_message', 'Unknown error')}\n")
                continue

            if page["status"] == "no_analysis":
                console.print(f"[yellow]Page {page_num}: NO ANALYSIS[/yellow]")
                console.print(f"  Reason: {page.get('reason', 'Unknown')}\n")
                continue

            # Page header
            contains_ai = page.get("contains_ai", False)
            ai_prob = page.get("ai_probability", 0)
            confidence = page.get("confidence", 0)

            if contains_ai:
                status_color = "red"
                status_text = "AI CONTENT DETECTED"
            else:
                status_color = "green"
                status_text = "HUMAN CONTENT"

            console.print(
                f"[bold]Page {page_num}:[/bold] "
                f"[{status_color}]{status_text}[/{status_color}] "
                f"(AI: {ai_prob:.1%}, Confidence: {confidence:.1%})"
            )

            console.print(
                f"  Primary Type: {page['primary_type']}, "
                f"Mixed: {page['is_mixed_content']}, "
                f"Elements: {page['elements_analyzed']}"
            )

            # Element details
            for i, element in enumerate(page.get("elements", []), 1):
                elem_type = element["element_type"]
                elem_status = element["status"]

                if elem_status == "skipped":
                    console.print(
                        f"    [{i}] {elem_type}: [dim]Skipped - {element['reason']}[/dim]"
                    )
                elif elem_status == "not_implemented":
                    console.print(
                        f"    [{i}] {elem_type}: [dim]{element['reason']}[/dim]"
                    )
                elif elem_status == "error":
                    console.print(
                        f"    [{i}] {elem_type}: [red]Error - {element['error']}[/red]"
                    )
                elif elem_status == "analyzed":
                    elem_ai_prob = element["ai_probability"]
                    elem_conf = element["confidence"]

                    if elem_ai_prob >= 0.8:
                        elem_color = "red"
                        elem_verdict = "AI"
                    elif elem_ai_prob >= 0.5:
                        elem_color = "yellow"
                        elem_verdict = "Uncertain"
                    else:
                        elem_color = "green"
                        elem_verdict = "Human"

                    console.print(
                        f"    [{i}] {elem_type}: [{elem_color}]{elem_verdict}[/{elem_color}] "
                        f"(AI: {elem_ai_prob:.1%}, Conf: {elem_conf:.1%})"
                    )

                    if elem_type == "text" and element.get("suspected_model"):
                        model = element["suspected_model"]
                        if model not in ["unknown", "human", None]:
                            console.print(f"        Model: {model}")

                    if "word_count" in element:
                        console.print(f"        Words: {element['word_count']}")

            console.print()

        # Show failed pages if any
        if summary["failed_pages"]:
            console.print(f"[red]Failed Pages: {summary['failed_pages']}[/red]\n")

        console.print("=" * 80)
        console.print("[bold green]✓ Pipeline test complete![/bold green]")
        console.print("=" * 80 + "\n")

        return True

    except Exception as e:
        console.print(f"\n[red]Error during pipeline test: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    if len(sys.argv) < 2:
        # Use default test PDF
        test_pdf = (
            Path(__file__).parent.parent
            / "tests"
            / "fixtures"
            / "sample_pdfs"
            / "test_document.pdf"
        )
        pdf_path = str(test_pdf)

        if not test_pdf.exists():
            console.print("[red]Error: Test PDF not found. Please provide a PDF path.[/red]")
            console.print("Usage: python test_integrated_pipeline.py <pdf_path> [page_range]")
            return 1
    else:
        pdf_path = sys.argv[1]

    page_range = sys.argv[2] if len(sys.argv) > 2 else None

    success = test_integrated_pipeline(pdf_path, page_range)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
