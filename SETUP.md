# Setup Guide - AI Content Detection System

Complete setup instructions for the AI Content Detection System.

## System Requirements

- **Python**: 3.9 or higher
- **RAM**: 8GB minimum (system uses ~1.5GB peak)
- **Storage**: ~2GB (1GB for models, 1GB for dependencies)
- **OS**: macOS, Linux, or Windows with WSL
- **Tesseract OCR**: Required for scanned PDFs

## Quick Setup (5 minutes)

### 1. Install System Dependencies

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows (WSL):**
```bash
sudo apt-get install tesseract-ocr
```

### 2. Clone Repository

```bash
git clone https://github.com/rajeshwarisah/check-ai-generated-content.git
cd check-ai-generated-content
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- PyTorch (CPU-only, ~500MB)
- Transformers (~200MB)
- PDF processing libraries
- All other dependencies

### 5. Download AI Detection Models

```bash
python scripts/download_models.py --text
```

This downloads:
- RoBERTa text detector (~500MB)
- GPT-2 perplexity model (~500MB)
- Total: ~1GB

### 6. Configure API Keys (Optional)

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key (optional)
```

**Note**: OpenAI API is optional. System works without it using local models.

### 7. Test Installation

```bash
# Run CLI help
python -m src.cli.main --help

# Test with sample PDF
python -m src.cli.main analyze tests/fixtures/sample_pdfs/test_document.pdf
```

## Detailed Setup

### Environment Variables (.env file)

```bash
# OpenAI API (Optional - system works without it)
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4

# Detection Thresholds
AI_DETECTION_THRESHOLD=0.80
CONFIDENCE_THRESHOLD=0.70
MIN_TEXT_WORDS=50

# Processing
MAX_PDF_PAGES=450
ENABLE_OCR=true

# Output
OUTPUT_DIR=outputs/reports
LOG_DIR=logs
LOG_LEVEL=INFO
```

### Configuration (config/default.yaml)

The main configuration file controls all system behavior:

```yaml
# Text detection thresholds
text_detection:
  min_words: 50
  detectors:
    openai:
      enabled: true
      weight: 0.4
    roberta:
      enabled: true
      weight: 0.3
    linguistic:
      enabled: true
      weight: 0.3

# AI detection threshold
thresholds:
  ai_detection: 0.80  # 80% = AI content

# PDF processing
pdf_processing:
  max_pages: 450
  dpi: 150
  ocr:
    enabled: true
```

## Project Structure

```
check-ai-generated-content/
├── src/
│   ├── cli/                    # Command-line interface
│   │   └── main.py            # CLI entry point
│   ├── core/                   # Core processing
│   │   ├── pdf_extractor.py   # PDF extraction
│   │   ├── content_classifier.py  # Content classification
│   │   ├── page_processor.py  # Page processing
│   │   └── content_analyzer.py    # Main analyzer
│   ├── detectors/              # AI detectors
│   │   ├── base_detector.py   # Base class
│   │   ├── text/              # Text detection
│   │   │   ├── openai_detector.py
│   │   │   ├── roberta_detector.py
│   │   │   ├── linguistic_analyzer.py
│   │   │   └── ensemble_text.py
│   │   └── image/             # Image detection
│   │       ├── forensic_analyzer.py
│   │       └── image_detector.py
│   ├── report/                 # Report generation
│   │   └── html_generator.py
│   └── utils/                  # Utilities
│       ├── config.py
│       ├── logger.py
│       ├── validators.py
│       └── error_handlers.py
├── config/                     # Configuration files
├── models/                     # AI models (downloaded)
├── scripts/                    # Utility scripts
├── outputs/                    # Generated reports
├── logs/                       # Log files
└── tests/                      # Test files
```

## Where to Find Logs

### Log Files Location

**Default:** `logs/ai_detector_YYYYMMDD_HHMMSS.log`

Example: `logs/ai_detector_20260116_220901.log`

### What's in the Logs

- System initialization
- PDF processing steps
- AI detection results
- Errors and warnings
- Performance metrics

### Viewing Logs

```bash
# View latest log
tail -f logs/ai_detector_*.log | head -100

# View all logs
ls -lt logs/

# Search for errors
grep ERROR logs/ai_detector_*.log

# Search for specific page
grep "Page 5" logs/ai_detector_*.log
```

### Log Levels

Configure in `.env`:
```bash
LOG_LEVEL=DEBUG   # Detailed debugging
LOG_LEVEL=INFO    # Normal operation (default)
LOG_LEVEL=WARNING # Only warnings and errors
LOG_LEVEL=ERROR   # Only errors
```

## Usage

### CLI Commands

#### Analyze a PDF

```bash
# Basic usage
python -m src.cli.main analyze document.pdf

# Specific pages
python -m src.cli.main analyze document.pdf --pages 1-10

# Custom output
python -m src.cli.main analyze document.pdf --output my_report.html

# Disable progress bars
python -m src.cli.main analyze document.pdf --no-progress

# Custom config
python -m src.cli.main analyze document.pdf --config my_config.yaml
```

#### Get PDF Info

```bash
python -m src.cli.main info document.pdf
```

#### Show Configuration

```bash
python -m src.cli.main config-show
```

### Python API

```python
from src.core.content_analyzer import ContentAnalyzer
from src.report.html_generator import HTMLReportGenerator

# Initialize
analyzer = ContentAnalyzer()

# Analyze PDF
results = analyzer.analyze_pdf("document.pdf")

# Generate report
generator = HTMLReportGenerator()
generator.generate(results, "report.html")

# Access results
summary = results["summary"]
print(f"AI detected: {summary['ai_percentage']:.1f}%")

# Per-page analysis
for page in results["pages"]:
    if page["contains_ai"]:
        print(f"Page {page['page_number']}: {page['ai_probability']:.1%}")
```

## Output

### HTML Reports

**Location:** `outputs/reports/` (default)

**Format:** Beautiful HTML with:
- Summary statistics
- Per-page analysis
- Element-level details
- Color-coded verdicts
- Confidence scores
- AI model identification

**View:** Open in any web browser

### Console Output

Real-time progress with:
- Progress bars
- Summary tables
- Element breakdowns
- Color-coded results

## Troubleshooting

### Common Issues

#### 1. "Tesseract not found"

**Solution:**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Check installation
tesseract --version
```

#### 2. "Out of memory"

**Solutions:**
- Process fewer pages at once: `--pages 1-50`
- Reduce DPI in config (150 → 100)
- Close other applications
- System has 8GB RAM - should work for most PDFs

#### 3. "OpenAI API error"

**Solutions:**
- Check API key in `.env`
- System works without OpenAI (uses local models)
- Disable OpenAI in `config/default.yaml`:
  ```yaml
  text_detection:
    detectors:
      openai:
        enabled: false
  ```

#### 4. "Model not found"

**Solution:**
```bash
# Re-download models
python scripts/download_models.py --text
```

#### 5. "PDF is corrupted"

**Causes:**
- Password-protected PDFs (not supported)
- Damaged PDF files
- Invalid PDF format

**Check:**
```bash
python -m src.cli.main info document.pdf
```

### Debug Mode

Enable detailed logging:

```bash
# Edit .env
LOG_LEVEL=DEBUG

# Or in config/default.yaml
logging:
  level: DEBUG

# View debug logs
tail -f logs/ai_detector_*.log
```

### Performance Issues

**Slow processing:**
- Expected: ~1 second per page
- For 100 pages: ~2-3 minutes
- For 450 pages: ~10-15 minutes

**Speed up:**
- Disable progress bars: `--no-progress`
- Process specific pages: `--pages 1-10`
- Reduce OCR if not needed

## Uninstallation

```bash
# Remove virtual environment
rm -rf venv/

# Remove downloaded models (optional)
rm -rf models/

# Remove generated reports (optional)
rm -rf outputs/

# Remove logs (optional)
rm -rf logs/
```

## Getting Help

### Documentation

- [README.md](README.md) - Overview
- [DESIGN.md](DESIGN.md) - Architecture
- [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) - PDF extraction
- [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md) - Text detection
- [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) - Integration

### CLI Help

```bash
# General help
python -m src.cli.main --help

# Command help
python -m src.cli.main analyze --help
```

### Check Logs

```bash
# Latest log
ls -lt logs/ | head -2

# View log
cat logs/ai_detector_*.log
```

## Advanced Configuration

### Custom Model Paths

Edit `config/models.yaml`:

```yaml
text_models:
  roberta_detector:
    model_id: "your-custom-model"
    local_path: "custom/path"
```

### Custom Thresholds

Edit `config/default.yaml`:

```yaml
thresholds:
  ai_detection: 0.70  # Lower = more sensitive
  confidence: 0.60
```

### Detector Weights

Balance detector influence:

```yaml
text_detection:
  detectors:
    openai:
      weight: 0.5  # Increase OpenAI influence
    roberta:
      weight: 0.3
    linguistic:
      weight: 0.2
```

## System Status Check

```bash
# Check Python version
python3 --version

# Check Tesseract
tesseract --version

# Check installation
python -m src.cli.main config-show

# Test with sample
python -m src.cli.main analyze tests/fixtures/sample_pdfs/test_document.pdf
```

## Next Steps

1. ✅ **Setup complete** - System is ready to use
2. 📄 **Test with your PDFs** - Try analyzing your documents
3. ⚙️ **Tune configuration** - Adjust thresholds as needed
4. 📊 **Review reports** - Check HTML output quality
5. 🔍 **Monitor logs** - Watch for errors or issues

---

**Last Updated**: 2026-01-16
**Version**: 1.0.0
