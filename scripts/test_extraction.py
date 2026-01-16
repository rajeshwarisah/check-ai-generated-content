"""Test script for PDF extraction pipeline."""

import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.page_processor import PageProcessor
from src.utils.config import get_config
from src.utils.logger import get_logger


def test_extraction(pdf_path: str):
    """
    Test PDF extraction pipeline.

    Args:
        pdf_path: Path to PDF file
    """
    print("=" * 80)
    print("Testing PDF Extraction Pipeline")
    print("=" * 80)

    try:
        # Initialize processor
        print("\n1. Initializing page processor...")
        processor = PageProcessor()
        print("   ✓ Page processor initialized")

        # Get PDF info
        print(f"\n2. Getting PDF info: {pdf_path}")
        info = processor.get_pdf_info(pdf_path)
        print(f"   ✓ Page count: {info['page_count']}")
        print(f"   ✓ File size: {info['file_size']:,} bytes")

        # Process PDF
        print("\n3. Processing PDF (all pages)...")
        results = processor.process_pdf(pdf_path, show_progress=True)

        summary = results["summary"]
        print(f"\n4. Processing Summary:")
        print(f"   - Total pages: {summary['total_pages']}")
        print(f"   - Processed pages: {summary['processed_pages']}")
        print(f"   - Successful pages: {summary['successful_pages']}")
        print(f"   - Failed pages: {len(summary['failed_pages'])}")

        if summary['failed_pages']:
            print(f"   - Failed page numbers: {summary['failed_pages']}")

        # Analyze each page
        print("\n5. Page Analysis:")
        for result in results["results"]:
            if result["status"] == "success":
                page_num = result["page_number"]
                classification = result["classification"]
                extraction = result["extraction"]

                print(f"\n   Page {page_num}:")
                print(f"      - Primary type: {classification['primary_type']}")
                print(f"      - Mixed content: {classification['is_mixed_content']}")

                content_types = classification['content_types']
                print(f"      - Has tables: {content_types['has_tables']}")
                print(f"      - Has images: {content_types['has_images']}")
                print(f"      - Has text: {content_types['has_text']}")

                print(f"      - Text blocks extracted: {len(extraction['text_blocks'])}")
                print(f"      - Images extracted: {len(extraction['images'])}")
                print(f"      - Tables extracted: {len(extraction['tables'])}")

                # Show classified elements
                elements = classification['elements']
                print(f"      - Classified elements: {len(elements)}")
                for elem in elements:
                    print(f"        • {elem['type']} (priority: {elem['priority']})")

                # Show sample text
                if extraction['text_blocks']:
                    all_text = " ".join(block['text'] for block in extraction['text_blocks'])
                    word_count = len(all_text.split())
                    print(f"      - Total words: {word_count}")
                    if word_count > 0:
                        sample = " ".join(all_text.split()[:20])
                        print(f"      - Sample text: {sample}...")

                # Show table info
                for i, table in enumerate(extraction['tables']):
                    print(f"      - Table {i+1}: {table['rows']} rows × {table['cols']} columns")

            else:
                print(f"\n   Page {result['page_number']}: FAILED")
                print(f"      - Error: {result.get('error_message', 'Unknown error')}")

        print("\n" + "=" * 80)
        print("✓ Extraction test completed successfully!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n✗ Error during extraction test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Determine PDF path
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Use default test PDF
        test_pdf = (
            Path(__file__).parent.parent
            / "tests"
            / "fixtures"
            / "sample_pdfs"
            / "test_document.pdf"
        )
        pdf_path = str(test_pdf)

    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    # Run test
    success = test_extraction(pdf_path)
    sys.exit(0 if success else 1)
