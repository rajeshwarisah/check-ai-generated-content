# AI-Generated Content Detection System

A comprehensive system for detecting AI-generated content in PDF documents, including text, images, and tables. Designed for fraud verification with per-page analysis and detailed reporting.

## Features

- **Multi-Modal Detection**: Analyzes text, images, and tables
- **Per-Page Analysis**: Detailed reports for each page with confidence scores
- **AI Model Identification**: Identifies which AI model likely generated the content (GPT, Claude, etc.)
- **Ensemble Detection**: Combines multiple detection methods for higher accuracy
- **Visual Reports**: HTML reports with bounding boxes and color-coded highlighting
- **Dual Interface**: Both CLI and Web UI available
- **Large Document Support**: Handle PDFs up to 450 pages
- **Mixed Content Handling**: Detects both AI-generated and human-created content in the same document

## Detection Methods

### Text Detection
- **OpenAI API**: GPT-4 based detection with model identification
- **RoBERTa Classifier**: Open-source transformer-based detector
- **Linguistic Analysis**: Perplexity, burstiness, entropy measurements
- **Ensemble Voting**: Weighted combination of all methods

### Image Detection
- **CNN-Based**: Deep learning classifier for AI-generated images
- **Forensic Analysis**: JPEG artifacts, noise patterns, frequency domain analysis
- **Text Extraction**: OCR to detect AI-generated text in images

## Installation

### Prerequisites
- Python 3.9 or higher
- Tesseract OCR
- OpenAI API key

### macOS Setup

1. **Install Tesseract**:
```bash
brew install tesseract
```

2. **Clone the repository**:
```bash
git clone https://github.com/yourusername/check-ai-generated-content.git
cd check-ai-generated-content
```

3. **Create virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate
```

4. **Install dependencies**:
```bash
pip install -r requirements.txt
```

5. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

6. **Download detection models**:
```bash
python scripts/download_models.py --all
```

## Usage

### Command Line Interface

**Analyze entire PDF**:
```bash
python -m src.cli.main analyze document.pdf
```

**Analyze specific pages**:
```bash
python -m src.cli.main analyze document.pdf --pages 1-10
```

**Batch processing**:
```bash
python -m src.cli.main analyze document.pdf --batch-size 5
```

**Custom output location**:
```bash
python -m src.cli.main analyze document.pdf --output reports/my_report.html
```

### Web Interface

**Start the web server**:
```bash
python -m src.web.app
```

Then open your browser to `http://localhost:5000`

## Output

The system generates comprehensive HTML reports with:

- **Page-by-page analysis** with visual previews
- **Bounding boxes** highlighting detected AI-generated regions
- **Confidence scores** for each detection
- **AI model identification** (when possible)
- **Detection method breakdown** showing individual detector results
- **Explanations** for each determination
- **Color-coded results**:
  - 🟢 Green: Human-generated (< 50% AI probability)
  - 🟡 Yellow: Inconclusive (50-79% AI probability)
  - 🔴 Red: AI-generated (≥ 80% AI probability)
  - ⚫ Gray: Analysis failed or insufficient data

## Configuration

Edit `config/default.yaml` to customize:
- Detection thresholds
- Model weights
- Processing options
- Output formats
- Error handling behavior

## Project Structure

```
check-ai-generated-content/
├── src/
│   ├── core/              # PDF extraction and content classification
│   ├── detectors/         # Text and image detection engines
│   ├── report/            # Report generation
│   ├── utils/             # Utilities and helpers
│   ├── cli/               # Command-line interface
│   └── web/               # Web interface
├── models/                # Pre-trained detection models
├── config/                # Configuration files
├── outputs/               # Generated reports
└── tests/                 # Unit tests
```

## Development

**Run tests**:
```bash
pytest tests/
```

**Code formatting**:
```bash
black src/ tests/
```

**Type checking**:
```bash
mypy src/
```

## Cost Considerations

- **OpenAI API**: ~$0.01-0.03 per page
- **Local Models**: Free after initial download
- **Estimated cost for 450-page document**: $4.50-$13.50

## Limitations

- Text detection requires minimum 50 words
- Image detection works best with high-resolution images (≥ 64x64 pixels)
- Model identification is probabilistic and may not always be accurate
- Does not support password-protected PDFs
- English text only (multilingual support planned)

## Roadmap

- [ ] Phase 1: PDF extraction and content classification
- [ ] Phase 2: Text detection implementation
- [ ] Phase 3: Image detection implementation
- [ ] Phase 4: Report generation
- [ ] Phase 5: CLI interface
- [ ] Phase 6: Web interface
- [ ] Phase 7: Integration testing
- [ ] Phase 8: Polish and deployment

See [DESIGN.md](DESIGN.md) for detailed design documentation.

## Contributing

Contributions are welcome! Please read the design document and implementation guidelines before submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for detection API
- HuggingFace for transformer models
- PyTorch community
- PyMuPDF and pdfplumber developers

## Support

For questions or issues, please open an issue on GitHub.
