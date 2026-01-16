"""Script to create a test PDF for testing extraction pipeline."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_test_pdf(output_path: str):
    """
    Create a test PDF with text, table, and basic content.

    Args:
        output_path: Path where PDF will be saved
    """
    # Create PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']

    # Add title
    title = Paragraph("Test Document for AI Content Detection", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Add introductory text (human-written style)
    intro_text = """
    This is a test document created to validate the PDF extraction pipeline.
    It contains various types of content including text paragraphs, tables,
    and structured data to ensure all extraction mechanisms are working correctly.
    The document is intentionally simple to make testing straightforward.
    """
    elements.append(Paragraph(intro_text, normal_style))
    elements.append(Spacer(1, 12))

    # Add more text content (AI-generated style)
    ai_text = """
    Artificial intelligence has revolutionized numerous industries in recent years.
    Machine learning algorithms have demonstrated remarkable capabilities in pattern
    recognition, natural language processing, and computer vision. Deep learning models,
    particularly neural networks, have achieved unprecedented accuracy in complex tasks.
    The integration of AI technologies continues to transform how businesses operate and
    how individuals interact with technology. Furthermore, the advancement of generative
    models has opened new possibilities for creative applications and automated content
    generation. These developments represent a paradigm shift in computational capabilities
    and human-computer interaction methodologies.
    """
    elements.append(Paragraph("Section 1: Technology Overview", styles['Heading2']))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(ai_text, normal_style))
    elements.append(Spacer(1, 12))

    # Add a table
    elements.append(Paragraph("Section 2: Data Analysis", styles['Heading2']))
    elements.append(Spacer(1, 6))

    table_data = [
        ['Category', 'Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024'],
        ['Revenue', '$125K', '$142K', '$158K', '$175K'],
        ['Expenses', '$85K', '$92K', '$98K', '$105K'],
        ['Profit', '$40K', '$50K', '$60K', '$70K'],
        ['Growth', '12%', '25%', '20%', '17%'],
    ]

    table = Table(table_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Add conclusion text
    conclusion = """
    In conclusion, this test document successfully demonstrates various content types
    that our extraction system needs to handle. The combination of narrative text,
    structured data in tables, and formatted sections provides a comprehensive test
    case for validating the PDF processing pipeline. We can verify that text extraction,
    table detection, and content classification are all functioning as expected.
    """
    elements.append(Paragraph("Section 3: Conclusion", styles['Heading2']))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(conclusion, normal_style))

    # Build PDF
    doc.build(elements)
    print(f"Test PDF created: {output_path}")


if __name__ == "__main__":
    # Create test directory if it doesn't exist
    test_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_pdfs"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create test PDF
    output_file = test_dir / "test_document.pdf"
    create_test_pdf(str(output_file))
