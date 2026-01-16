"""Script to download required AI detection models."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from transformers import AutoTokenizer, AutoModelForSequenceClassification, GPT2LMHeadModel, GPT2Tokenizer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def download_text_models(model_dir: Path):
    """
    Download text detection models.

    Args:
        model_dir: Base directory for models
    """
    console.print("\n[bold cyan]Downloading Text Detection Models[/bold cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # RoBERTa detector
        task = progress.add_task("Downloading RoBERTa AI detector...", total=None)

        roberta_dir = model_dir / "text" / "roberta_detector"
        roberta_dir.mkdir(parents=True, exist_ok=True)

        try:
            model_id = "Hello-SimpleAI/chatgpt-detector-roberta"
            console.print(f"  Model: {model_id}")

            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForSequenceClassification.from_pretrained(model_id)

            tokenizer.save_pretrained(str(roberta_dir))
            model.save_pretrained(str(roberta_dir))

            progress.update(task, completed=True)
            console.print(f"  ✓ Saved to: {roberta_dir}\n")
        except Exception as e:
            console.print(f"  ✗ Error: {e}\n", style="red")

        # GPT-2 for perplexity
        task = progress.add_task("Downloading GPT-2 for perplexity analysis...", total=None)

        perplexity_dir = model_dir / "text" / "perplexity_model"
        perplexity_dir.mkdir(parents=True, exist_ok=True)

        try:
            model_id = "gpt2"
            console.print(f"  Model: {model_id}")

            tokenizer = GPT2Tokenizer.from_pretrained(model_id)
            model = GPT2LMHeadModel.from_pretrained(model_id)

            tokenizer.save_pretrained(str(perplexity_dir))
            model.save_pretrained(str(perplexity_dir))

            progress.update(task, completed=True)
            console.print(f"  ✓ Saved to: {perplexity_dir}\n")
        except Exception as e:
            console.print(f"  ✗ Error: {e}\n", style="red")


def download_image_models(model_dir: Path):
    """
    Download image detection models.

    Args:
        model_dir: Base directory for models
    """
    console.print("\n[bold cyan]Image Detection Models[/bold cyan]\n")
    console.print("  ℹ Image models will be implemented in Phase 3")
    console.print("  For now, placeholder directory will be created\n")

    image_dir = model_dir / "image" / "cnn_detector"
    image_dir.mkdir(parents=True, exist_ok=True)

    # Create a placeholder file
    placeholder = image_dir / "README.txt"
    placeholder.write_text(
        "Image detection models will be added in Phase 3.\n"
        "This directory is reserved for future use.\n"
    )

    console.print(f"  ✓ Created placeholder: {image_dir}\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Download AI detection models")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Download text detection models",
    )
    parser.add_argument(
        "--image",
        action="store_true",
        help="Download image detection models (Phase 3)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all models",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default="models",
        help="Base directory for models (default: models/)",
    )

    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    model_dir = project_root / args.model_dir

    console.print("\n[bold]AI Detection Model Downloader[/bold]")
    console.print(f"Model directory: {model_dir}\n")

    # Check what to download
    download_text = args.text or args.all
    download_image = args.image or args.all

    if not (download_text or download_image):
        console.print("[yellow]No models specified. Use --text, --image, or --all[/yellow]")
        parser.print_help()
        return 1

    # Download models
    try:
        if download_text:
            download_text_models(model_dir)

        if download_image:
            download_image_models(model_dir)

        console.print("\n[bold green]✓ Model download complete![/bold green]\n")

        # Print summary
        console.print("[bold]Model Locations:[/bold]")
        if download_text:
            console.print(f"  - RoBERTa: {model_dir}/text/roberta_detector/")
            console.print(f"  - GPT-2: {model_dir}/text/perplexity_model/")
        if download_image:
            console.print(f"  - Image models: {model_dir}/image/ (Phase 3)")

        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Set your OpenAI API key in .env file")
        console.print("  2. Run: python scripts/test_text_detection.py")
        console.print()

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Download cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
