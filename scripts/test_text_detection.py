"""Test script for text detection pipeline."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.detectors.text.ensemble_text import EnsembleTextDetector
from src.detectors.model_identifier import AIModelIdentifier
from src.utils.config import get_config
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_text_detection():
    """Test text detection with sample texts."""

    console.print("\n[bold cyan]Testing Text Detection Pipeline[/bold cyan]\n")

    # Sample texts
    test_samples = [
        {
            "name": "Human-written (casual)",
            "text": """
                Hey! So I was thinking about this the other day... you know how everyone's
                talking about AI? It's crazy how fast things are moving. Like, I remember
                when chatbots were super dumb and now they can write essays and stuff.
                But honestly, I'm not sure if that's a good thing or not. What do you think?
                Anyway, I gotta run to the store real quick. Talk later!
            """,
        },
        {
            "name": "AI-generated (GPT-style)",
            "text": """
                Artificial intelligence has emerged as a transformative technology that is
                fundamentally reshaping various aspects of modern society. The integration of
                AI systems across multiple domains has demonstrated remarkable potential for
                enhancing efficiency and productivity. Furthermore, machine learning algorithms
                have shown exceptional capabilities in pattern recognition and data analysis.
                It is important to note that these technological advancements present both
                opportunities and challenges. Moreover, the ethical implications of AI deployment
                require careful consideration. Consequently, stakeholders must collaborate to
                ensure responsible development and implementation of these powerful systems.
            """,
        },
        {
            "name": "Mixed (edited AI)",
            "text": """
                I've been working with AI for a few years now, and it's pretty amazing what
                these systems can do. Machine learning algorithms have become increasingly
                sophisticated, enabling applications that were previously impossible. However,
                we need to be realistic about the limitations. Not everything can or should be
                automated. There's still a huge role for human judgment, creativity, and ethics
                in how we deploy these technologies. The key is finding the right balance.
            """,
        },
        {
            "name": "Technical (human academic)",
            "text": """
                Recent advancements in transformer architectures have led to significant
                improvements in natural language processing tasks (Vaswani et al., 2017).
                Our experiments demonstrate that fine-tuning on domain-specific corpora yields
                better performance than general pre-training alone. We observe a 12% improvement
                in F1 scores across our test set (n=500, p<0.01). These findings suggest that
                transfer learning remains highly effective for specialized applications.
            """,
        },
    ]

    # Initialize detector
    console.print("Initializing ensemble text detector...")
    try:
        detector = EnsembleTextDetector()

        if not detector.is_available():
            console.print("[red]No detectors available! Please run download_models.py first.[/red]")
            return False

        console.print(f"✓ {len(detector.detectors)} detector(s) loaded\n")
    except Exception as e:
        console.print(f"[red]Failed to initialize detector: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

    # Initialize model identifier
    identifier = AIModelIdentifier()

    # Test each sample
    for i, sample in enumerate(test_samples, 1):
        console.print(f"\n[bold]Test {i}: {sample['name']}[/bold]")
        console.print("─" * 80)

        text = sample["text"].strip()

        # Show text sample
        preview = " ".join(text.split()[:30]) + "..."
        console.print(f"\n[dim]{preview}[/dim]\n")

        # Run detection
        try:
            result = detector.detect(text)

            if result["status"] == "error":
                console.print(f"[red]Error: {result.get('error')}[/red]")
                continue

            # Display results
            ai_prob = result["ai_probability"]
            confidence = result["confidence"]

            # Color code based on AI probability
            if ai_prob >= 0.7:
                prob_color = "red"
                verdict = "AI-GENERATED"
            elif ai_prob >= 0.5:
                prob_color = "yellow"
                verdict = "UNCERTAIN"
            else:
                prob_color = "green"
                verdict = "HUMAN-WRITTEN"

            console.print(
                f"[bold {prob_color}]{verdict}[/bold {prob_color}] "
                f"(AI Probability: {ai_prob:.1%}, Confidence: {confidence:.1%})"
            )

            # Model identification
            model_info = identifier.identify(text, result)
            if model_info["model"] != "unknown":
                model_name = identifier.format_model_name(model_info["model"])
                console.print(
                    f"Suspected Model: {model_name} "
                    f"(confidence: {model_info['confidence']:.1%})"
                )

            # Individual detector results
            console.print("\n[bold]Individual Detector Results:[/bold]")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Method")
            table.add_column("AI Probability", justify="right")
            table.add_column("Confidence", justify="right")
            table.add_column("Status")

            for det_result in result["individual_results"]:
                method = det_result["method"]
                prob = det_result["ai_probability"]
                conf = det_result["confidence"]
                error = det_result["error"]

                if error:
                    status = f"[red]Error: {error}[/red]"
                    table.add_row(method, "-", "-", status)
                else:
                    prob_str = f"{prob:.1%}"
                    conf_str = f"{conf:.1%}"
                    status = "[green]✓[/green]"
                    table.add_row(method, prob_str, conf_str, status)

            console.print(table)

            # Explanation
            explanation = result.get("explanation", "")
            if explanation:
                console.print(f"\n[bold]Explanation:[/bold]")
                console.print(Panel(explanation, border_style="blue"))

        except Exception as e:
            console.print(f"[red]Detection failed: {e}[/red]")
            import traceback
            traceback.print_exc()

    console.print("\n" + "=" * 80)
    console.print("[bold green]✓ Text detection test complete![/bold green]")
    console.print("=" * 80 + "\n")

    return True


def test_custom_text():
    """Test with custom user-provided text."""
    console.print("\n[bold cyan]Custom Text Detection[/bold cyan]\n")
    console.print("Enter or paste your text (press Ctrl+D or Ctrl+Z when done):\n")

    try:
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break

        text = "\n".join(lines).strip()

        if not text:
            console.print("[yellow]No text provided[/yellow]")
            return False

        # Initialize detector
        detector = EnsembleTextDetector()
        identifier = AIModelIdentifier()

        # Run detection
        result = detector.detect(text)

        if result["status"] == "error":
            console.print(f"[red]Error: {result.get('error')}[/red]")
            return False

        # Display results
        console.print("\n[bold]Detection Results:[/bold]\n")
        console.print(f"AI Probability: {result['ai_probability']:.1%}")
        console.print(f"Confidence: {result['confidence']:.1%}")

        model_info = identifier.identify(text, result)
        if model_info["model"] != "unknown":
            model_name = identifier.format_model_name(model_info["model"])
            console.print(f"Suspected Model: {model_name}")

        console.print(f"\n{result['explanation']}")

        return True

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        return False


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--custom":
        return 0 if test_custom_text() else 1
    else:
        return 0 if test_text_detection() else 1


if __name__ == "__main__":
    sys.exit(main())
