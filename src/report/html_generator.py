"""HTML report generator with visual highlighting."""

from typing import Dict, List
from pathlib import Path
from datetime import datetime
import base64
import io
from PIL import Image, ImageDraw

from ..utils.logger import get_logger
from ..utils.config import get_config


class HTMLReportGenerator:
    """Generate HTML reports with bounding box visualizations."""

    def __init__(self):
        """Initialize report generator."""
        self.logger = get_logger()
        self.config = get_config()

        # Get color coding from config
        reporting_config = self.config.get("reporting", {})
        color_coding = reporting_config.get("color_coding", {})

        self.colors = {
            "human": color_coding.get("human_generated", "#28a745"),
            "uncertain": color_coding.get("inconclusive", "#ffc107"),
            "ai": color_coding.get("ai_generated", "#dc3545"),
            "failed": color_coding.get("failed", "#6c757d"),
        }

    def generate(self, analysis_results: Dict, output_path: str) -> str:
        """
        Generate HTML report from analysis results.

        Args:
            analysis_results: Results from ContentAnalyzer
            output_path: Path to save HTML report

        Returns:
            Path to generated report
        """
        self.logger.info(f"Generating HTML report: {output_path}")

        html = self._build_html(analysis_results)

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        self.logger.info(f"Report generated: {output_file}")
        return str(output_file)

    def _build_html(self, results: Dict) -> str:
        """Build complete HTML document."""
        summary = results["summary"]
        pages = results["pages"]
        pdf_info = results.get("pdf_info", {})

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Content Detection Report</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._build_header(pdf_info, summary)}
        {self._build_summary_section(summary)}
        {self._build_pages_section(pages)}
        {self._build_footer()}
    </div>
</body>
</html>"""

        return html

    def _get_css(self) -> str:
        """Get CSS styles for report."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }

        .header-meta {
            opacity: 0.9;
            font-size: 0.9em;
        }

        .section {
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .summary-card {
            padding: 20px;
            border-radius: 8px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
        }

        .summary-card h3 {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }

        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }

        .summary-card.ai-detected {
            border-left-color: #dc3545;
        }

        .summary-card.ai-detected .value {
            color: #dc3545;
        }

        .page-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }

        .page-header {
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .page-header h3 {
            font-size: 1.2em;
        }

        .verdict {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }

        .verdict.human {
            background: #d4edda;
            color: #155724;
        }

        .verdict.ai {
            background: #f8d7da;
            color: #721c24;
        }

        .verdict.uncertain {
            background: #fff3cd;
            color: #856404;
        }

        .verdict.failed {
            background: #d6d8db;
            color: #383d41;
        }

        .page-content {
            padding: 20px;
        }

        .page-preview {
            text-align: center;
            margin-bottom: 20px;
            position: relative;
        }

        .page-preview img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        .elements-list {
            margin-top: 20px;
        }

        .element-card {
            background: #f8f9fa;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 4px solid #6c757d;
        }

        .element-card.human {
            border-left-color: #28a745;
        }

        .element-card.ai {
            border-left-color: #dc3545;
        }

        .element-card.uncertain {
            border-left-color: #ffc107;
        }

        .element-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }

        .element-type {
            font-weight: bold;
            text-transform: capitalize;
        }

        .element-score {
            font-size: 0.9em;
            color: #666;
        }

        .element-details {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }

        .explanation {
            background: #e9ecef;
            padding: 15px;
            border-radius: 6px;
            margin-top: 10px;
            font-size: 0.9em;
            line-height: 1.5;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }

        .stats-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }

        .stats-table th,
        .stats-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }

        .stats-table th {
            background: #f8f9fa;
            font-weight: 600;
        }

        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 500;
        }

        .badge.human {
            background: #d4edda;
            color: #155724;
        }

        .badge.ai {
            background: #f8d7da;
            color: #721c24;
        }

        @media print {
            body {
                background: white;
            }
            .container {
                max-width: 100%;
            }
            .page-card {
                page-break-inside: avoid;
            }
        }
        """

    def _build_header(self, pdf_info: Dict, summary: Dict) -> str:
        """Build header section."""
        pdf_path = pdf_info.get("path", "Unknown")
        page_range = pdf_info.get("page_range", "All")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""
        <div class="header">
            <h1>🔍 AI Content Detection Report</h1>
            <div class="header-meta">
                <p><strong>Document:</strong> {pdf_path}</p>
                <p><strong>Pages Analyzed:</strong> {page_range}</p>
                <p><strong>Generated:</strong> {timestamp}</p>
            </div>
        </div>
        """

    def _build_summary_section(self, summary: Dict) -> str:
        """Build summary statistics section."""
        ai_detected = summary.get("ai_detected_pages", 0)
        total = summary.get("total_analyzed", 0)
        ai_pct = summary.get("ai_percentage", 0)

        elements = summary.get("elements", {})

        html = """
        <div class="section">
            <h2 class="section-title">📊 Summary</h2>
            <div class="summary-grid">
        """

        # Total pages
        html += f"""
                <div class="summary-card">
                    <h3>Total Pages</h3>
                    <div class="value">{total}</div>
                </div>
        """

        # AI detected pages
        html += f"""
                <div class="summary-card ai-detected">
                    <h3>AI Content Detected</h3>
                    <div class="value">{ai_detected}</div>
                </div>
        """

        # AI percentage
        html += f"""
                <div class="summary-card ai-detected">
                    <h3>AI Percentage</h3>
                    <div class="value">{ai_pct:.1f}%</div>
                </div>
        """

        # Failed pages
        failed = summary.get("total_failed", 0)
        html += f"""
                <div class="summary-card">
                    <h3>Failed Pages</h3>
                    <div class="value">{failed}</div>
                </div>
        """

        html += """
            </div>
        """

        # Elements table
        html += """
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>Element Type</th>
                        <th>Total Analyzed</th>
                        <th>AI Detected</th>
                    </tr>
                </thead>
                <tbody>
        """

        text_total = elements.get("text_elements", 0)
        text_ai = elements.get("ai_detected_text", 0)
        html += f"""
                    <tr>
                        <td>Text Blocks</td>
                        <td>{text_total}</td>
                        <td><span class="badge ai">{text_ai}</span></td>
                    </tr>
        """

        table_total = elements.get("table_elements", 0)
        table_ai = elements.get("ai_detected_tables", 0)
        html += f"""
                    <tr>
                        <td>Tables</td>
                        <td>{table_total}</td>
                        <td><span class="badge ai">{table_ai}</span></td>
                    </tr>
        """

        image_total = elements.get("image_elements", 0)
        html += f"""
                    <tr>
                        <td>Images</td>
                        <td>{image_total}</td>
                        <td>-</td>
                    </tr>
        """

        html += """
                </tbody>
            </table>
        </div>
        """

        return html

    def _build_pages_section(self, pages: List[Dict]) -> str:
        """Build pages analysis section."""
        html = """
        <div class="section">
            <h2 class="section-title">📄 Page-by-Page Analysis</h2>
        """

        for page in pages:
            html += self._build_page_card(page)

        html += """
        </div>
        """

        return html

    def _build_page_card(self, page: Dict) -> str:
        """Build individual page card."""
        page_num = page.get("page_number", 0)
        status = page.get("status", "unknown")

        # Determine verdict
        if status == "failed":
            verdict_class = "failed"
            verdict_text = "FAILED"
        elif status == "no_analysis":
            verdict_class = "failed"
            verdict_text = "NO ANALYSIS"
        else:
            contains_ai = page.get("contains_ai", False)
            ai_prob = page.get("ai_probability", 0)

            if contains_ai:
                verdict_class = "ai"
                verdict_text = "AI DETECTED"
            elif ai_prob >= 0.5:
                verdict_class = "uncertain"
                verdict_text = "UNCERTAIN"
            else:
                verdict_class = "human"
                verdict_text = "HUMAN CONTENT"

        html = f"""
        <div class="page-card">
            <div class="page-header">
                <h3>Page {page_num}</h3>
                <span class="verdict {verdict_class}">{verdict_text}</span>
            </div>
            <div class="page-content">
        """

        if status == "failed":
            error_msg = page.get("error_message", "Unknown error")
            html += f"""
                <div class="explanation">
                    <strong>Error:</strong> {error_msg}
                </div>
            """
        elif status == "no_analysis":
            reason = page.get("reason", "Unknown reason")
            html += f"""
                <div class="explanation">
                    <strong>Reason:</strong> {reason}
                </div>
            """
        else:
            # Show page info
            ai_prob = page.get("ai_probability", 0)
            confidence = page.get("confidence", 0)
            primary_type = page.get("primary_type", "unknown")
            is_mixed = page.get("is_mixed_content", False)

            html += f"""
                <div style="margin-bottom: 15px;">
                    <strong>AI Probability:</strong> {ai_prob:.1%} &nbsp;
                    <strong>Confidence:</strong> {confidence:.1%} &nbsp;
                    <strong>Type:</strong> {primary_type}
                    {' (mixed content)' if is_mixed else ''}
                </div>
            """

            # Elements
            elements = page.get("elements", [])
            if elements:
                html += """
                    <div class="elements-list">
                        <h4>Elements:</h4>
                """

                for element in elements:
                    html += self._build_element_card(element)

                html += """
                    </div>
                """

        html += """
            </div>
        </div>
        """

        return html

    def _build_element_card(self, element: Dict) -> str:
        """Build individual element card."""
        elem_type = element.get("element_type", "unknown")
        status = element.get("status", "unknown")

        if status == "skipped":
            return f"""
                <div class="element-card">
                    <div class="element-header">
                        <span class="element-type">{elem_type}</span>
                        <span class="element-score">Skipped</span>
                    </div>
                    <div class="element-details">
                        {element.get('reason', 'Unknown reason')}
                    </div>
                </div>
            """

        if status == "error":
            return f"""
                <div class="element-card">
                    <div class="element-header">
                        <span class="element-type">{elem_type}</span>
                        <span class="element-score">Error</span>
                    </div>
                    <div class="element-details">
                        {element.get('error', 'Unknown error')}
                    </div>
                </div>
            """

        if status != "analyzed":
            return ""

        # Analyzed element
        ai_prob = element.get("ai_probability", 0)
        confidence = element.get("confidence", 0)

        if ai_prob >= 0.8:
            card_class = "ai"
            verdict = "AI"
        elif ai_prob >= 0.5:
            card_class = "uncertain"
            verdict = "Uncertain"
        else:
            card_class = "human"
            verdict = "Human"

        html = f"""
            <div class="element-card {card_class}">
                <div class="element-header">
                    <span class="element-type">{elem_type}</span>
                    <span class="element-score">
                        {verdict} (AI: {ai_prob:.1%}, Conf: {confidence:.1%})
                    </span>
                </div>
        """

        # Type-specific details
        if elem_type == "text":
            word_count = element.get("word_count", 0)
            html += f"""
                <div class="element-details">
                    Words: {word_count}
            """

            suspected_model = element.get("suspected_model")
            if suspected_model and suspected_model not in ["unknown", "human", None]:
                html += f""" | Suspected Model: {suspected_model}"""

            html += """
                </div>
            """

        elif elem_type == "table":
            table_size = element.get("table_size", "unknown")
            html += f"""
                <div class="element-details">
                    Size: {table_size}
                </div>
            """

        elif elem_type == "image":
            image_size = element.get("image_size", "unknown")
            has_text = element.get("has_text", False)
            html += f"""
                <div class="element-details">
                    Size: {image_size}
            """
            if has_text:
                html += """ | Contains text"""
            html += """
                </div>
            """

        # Explanation (for text elements)
        if elem_type == "text" and "explanation" in element:
            explanation = element["explanation"]
            # Truncate if too long
            if len(explanation) > 500:
                explanation = explanation[:500] + "..."
            html += f"""
                <div class="explanation">
                    {explanation}
                </div>
            """

        html += """
            </div>
        """

        return html

    def _build_footer(self) -> str:
        """Build footer."""
        return """
        <div class="footer">
            <p>Generated by AI Content Detection System</p>
            <p>Powered by Ensemble Detection (OpenAI + RoBERTa + Linguistic Analysis)</p>
        </div>
        """
