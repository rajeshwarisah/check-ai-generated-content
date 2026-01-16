# AI-Generated Content Detection System - Design Document

## 1. System Overview

### Purpose
Detect AI-generated content (text and images) in PDF documents for fraud verification purposes.

### Key Requirements
- **Accuracy Target**: 80% confidence threshold
- **Document Size**: Up to 450 pages per PDF
- **Processing Mode**: Per-page analysis with individual reports
- **Content Types**: Text, images (with embedded text), tables, charts/graphs
- **AI Model Identification**: Detect and identify which AI model generated the content
- **Mixed Content Support**: Handle pages with both human and AI-generated content

---

## 2. System Architecture

### 2.1 High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                         Input Layer                              │
│  PDF Upload (Web UI / CLI) → Validation → Page Range Selection  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Processing Pipeline                         │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   PDF        │ → │   Content     │ → │  Detection    │      │
│  │  Extraction  │    │ Classification│    │   Engine      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         ↓                    ↓                     ↓             │
│  Extract pages      Identify type per page    Run detectors     │
│  Extract text       (text/image/table/mixed)  per content type  │
│  Extract images                                                  │
│  Extract tables                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Analysis & Reporting                        │
│  Ensemble Results → Confidence Scoring → HTML Report Generation │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Modular Pipeline Components

1. **PDF Extraction Module**
   - Parse PDF and extract individual pages
   - Extract text content (including OCR for scanned PDFs)
   - Extract images with bounding boxes
   - Detect and extract tables as structured data
   - Preserve document structure and metadata

2. **Content Classification Module**
   - Analyze each page to determine content types
   - Priority: Tables > Images with text > Plain text
   - Tag each element with type and coordinates

3. **Text Detection Engine**
   - OpenAI API-based detection
   - Open-source model detection (RoBERTa-based)
   - Linguistic feature analysis (perplexity, burstiness, entropy)
   - Ensemble voting across all detectors
   - Minimum 50 words for analysis

4. **Image Detection Engine**
   - CNN-based AI image detection
   - Forensic analysis (JPEG artifacts, noise patterns, frequency analysis)
   - Extract and analyze text embedded in images
   - Handle charts, graphs, diagrams

5. **AI Model Identification Module**
   - Text: Detect GPT variants, Claude, other LLMs
   - Images: Detect generation signatures (limited to forensic analysis)
   - Use pattern matching and model-specific artifacts

6. **Reporting Engine**
   - Generate HTML reports with visual highlighting
   - Per-page scores and confidence intervals
   - Bounding boxes for detected regions
   - Explanations for determinations
   - Detection method attribution

---

## 3. Component Breakdown

### 3.1 PDF Extraction Module

**Technology**: PyMuPDF (fitz) for primary extraction, pdfplumber for tables

**Responsibilities**:
- Convert each page to image for layout preservation
- Extract text with position coordinates
- Detect and extract tables using table detection algorithms
- Extract embedded images
- Handle both native and scanned PDFs (Tesseract OCR)
- Support complex layouts (multi-column, annotations)

**Outputs**:
```python
{
    "page_number": int,
    "page_image": PIL.Image,
    "text_blocks": [
        {
            "text": str,
            "bbox": [x0, y0, x1, y1],
            "font_info": dict
        }
    ],
    "images": [
        {
            "image": PIL.Image,
            "bbox": [x0, y0, x1, y1]
        }
    ],
    "tables": [
        {
            "data": pd.DataFrame,
            "bbox": [x0, y0, x1, y1]
        }
    ]
}
```

### 3.2 Content Classification Module

**Technology**: Custom logic + layout analysis

**Responsibilities**:
- Classify page content type(s)
- Prioritize tables in mixed content
- Identify text regions vs. image regions
- Extract text from images (OCR)

**Classification Logic**:
```python
priority_order = ["table", "image_with_text", "image", "text"]

def classify_page(extracted_data):
    content_types = {
        "has_tables": len(extracted_data["tables"]) > 0,
        "has_images": len(extracted_data["images"]) > 0,
        "has_text": len(extracted_data["text_blocks"]) > 0
    }

    # Priority: Tables > Images > Text
    if content_types["has_tables"]:
        primary_type = "table"
    elif content_types["has_images"]:
        primary_type = "image"
    else:
        primary_type = "text"

    return primary_type, content_types
```

### 3.3 Text Detection Engine

**Components**:

1. **OpenAI API Detector**
   - Use GPT-4 API with specialized prompts
   - Request likelihood scores and model identification
   - Cost: ~$0.01-0.03 per page (depending on text length)

2. **Open-Source Model Detector**
   - RoBERTa-based classifier (e.g., `roberta-base-openai-detector`)
   - Fine-tuned on AI-generated text datasets
   - Local inference using PyTorch

3. **Linguistic Feature Analyzer**
   - Calculate perplexity using small language model
   - Measure burstiness (sentence length variance)
   - Compute entropy and token distribution
   - Statistical features: avg word length, vocabulary richness

4. **Ensemble Voting**
   - Weighted average across all detectors
   - Confidence scoring based on agreement level
   - Model identification through API and pattern analysis

**Text Detection Flow**:
```python
def detect_ai_text(text: str) -> dict:
    if len(text.split()) < 50:
        return {"status": "insufficient_text"}

    results = []

    # Detector 1: OpenAI API
    openai_result = openai_detector.detect(text)
    results.append({
        "method": "openai_api",
        "score": openai_result.ai_probability,
        "model_guess": openai_result.suspected_model,
        "weight": 0.4
    })

    # Detector 2: RoBERTa
    roberta_result = roberta_detector.predict(text)
    results.append({
        "method": "roberta",
        "score": roberta_result.ai_probability,
        "weight": 0.3
    })

    # Detector 3: Linguistic features
    linguistic_score = linguistic_analyzer.analyze(text)
    results.append({
        "method": "linguistic_features",
        "score": linguistic_score,
        "weight": 0.3
    })

    # Ensemble
    ensemble_score = sum(r["score"] * r["weight"] for r in results)
    confidence = calculate_confidence(results)

    return {
        "status": "analyzed",
        "ai_probability": ensemble_score,
        "confidence": confidence,
        "individual_results": results,
        "suspected_model": identify_model(results),
        "explanation": generate_explanation(results)
    }
```

### 3.4 Image Detection Engine

**Components**:

1. **CNN-Based Detector**
   - Pre-trained model: Fine-tuned ResNet50 or EfficientNet
   - Training dataset: Real vs. AI-generated images
   - Local inference using PyTorch

2. **Forensic Analyzer**
   - JPEG compression artifact analysis
   - Noise pattern inconsistencies
   - Frequency domain analysis (DCT coefficients)
   - GAN fingerprint detection

3. **Text Extraction from Images**
   - Tesseract OCR for text in images
   - Feed extracted text to text detection engine

**Image Detection Flow**:
```python
def detect_ai_image(image: PIL.Image) -> dict:
    results = []

    # Detector 1: CNN-based
    cnn_result = cnn_detector.predict(image)
    results.append({
        "method": "cnn_classifier",
        "score": cnn_result.ai_probability,
        "weight": 0.6
    })

    # Detector 2: Forensic analysis
    forensic_score = forensic_analyzer.analyze(image)
    results.append({
        "method": "forensic_analysis",
        "score": forensic_score,
        "features": forensic_analyzer.get_features(),
        "weight": 0.4
    })

    # Extract and analyze text in image
    extracted_text = ocr.extract_text(image)
    text_analysis = None
    if len(extracted_text.split()) >= 50:
        text_analysis = detect_ai_text(extracted_text)

    ensemble_score = sum(r["score"] * r["weight"] for r in results)
    confidence = calculate_confidence(results)

    return {
        "status": "analyzed",
        "ai_probability": ensemble_score,
        "confidence": confidence,
        "individual_results": results,
        "embedded_text_analysis": text_analysis,
        "explanation": generate_explanation(results)
    }
```

### 3.5 Table Detection Strategy

**Approach**: Extract table data → Convert to text → Run text detection

```python
def detect_ai_table(table_df: pd.DataFrame, bbox: list) -> dict:
    # Convert table to text representation
    table_text = table_to_text(table_df)

    # Run text detection
    text_result = detect_ai_text(table_text)

    # Add table-specific metadata
    return {
        **text_result,
        "content_type": "table",
        "dimensions": table_df.shape,
        "bbox": bbox
    }
```

### 3.6 AI Model Identification

**Text Model Identification**:
- Use OpenAI API responses
- Pattern matching for known model signatures:
  - GPT models: Specific phrasing patterns, token usage
  - Claude: Characteristic structure and tone
  - Other LLMs: Distinct artifacts

**Image Model Identification**:
- Limited to forensic signatures (challenging without labeled data)
- Look for known artifacts from Stable Diffusion, DALL-E, Midjourney
- Report as "unknown AI generator" if specific model can't be identified

### 3.7 Reporting Engine

**Technology**: HTML/CSS with embedded JavaScript for interactivity

**Report Structure**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Detection Report - [filename]</title>
    <style>/* Modern, clean styling */</style>
</head>
<body>
    <header>
        <h1>AI-Generated Content Detection Report</h1>
        <div class="summary">
            <p>Document: [filename]</p>
            <p>Total Pages: [total]</p>
            <p>Pages Analyzed: [analyzed]</p>
            <p>Date: [timestamp]</p>
        </div>
    </header>

    <main>
        <!-- Per-page results -->
        <section class="page-result" id="page-1">
            <h2>Page 1</h2>

            <!-- Page preview with bounding boxes -->
            <div class="page-preview">
                <img src="data:image/png;base64,[page_image]">
                <!-- SVG overlay for bounding boxes -->
                <svg class="bbox-overlay">
                    <rect class="ai-detected" x="10" y="20" width="100" height="50"/>
                </svg>
            </div>

            <!-- Detection results -->
            <div class="detection-results">
                <h3>Content Type: Text + Image</h3>

                <div class="element-result">
                    <h4>Text Block 1</h4>
                    <p class="score ai-detected">AI Probability: 92% (High Confidence)</p>
                    <p class="model">Suspected Model: GPT-4</p>
                    <p class="methods">Detection Methods: OpenAI API (95%), RoBERTa (90%), Linguistic (91%)</p>
                    <p class="explanation">
                        This text shows characteristic patterns of AI generation:
                        - Low perplexity score (2.3)
                        - Consistent sentence structure
                        - High vocabulary diversity typical of GPT models
                    </p>
                    <div class="bbox-info">Location: [10, 20, 500, 300]</div>
                </div>

                <div class="element-result">
                    <h4>Image 1</h4>
                    <p class="score inconclusive">AI Probability: 65% (Low Confidence)</p>
                    <p class="model">Suspected Model: Unable to determine</p>
                    <p class="methods">Detection Methods: CNN (70%), Forensic (60%)</p>
                    <p class="explanation">
                        Detection is inconclusive due to:
                        - Low resolution affecting forensic analysis
                        - Mixed signals from CNN classifier
                        - Recommend manual review
                    </p>
                </div>
            </div>
        </section>
    </main>

    <footer>
        <p>Generated by AI Content Detection System v1.0</p>
    </footer>
</body>
</html>
```

**Visual Highlighting**:
- Green: Human-generated (AI probability < 50%)
- Yellow: Inconclusive (50-79%)
- Red: AI-generated (≥80%)
- Gray: Insufficient data / Analysis failed

---

## 4. Technology Stack

### Core Technologies
- **Language**: Python 3.9+
- **ML Framework**: PyTorch 2.0+
- **PDF Processing**: PyMuPDF (fitz), pdfplumber
- **OCR**: Tesseract 5.0+
- **Table Extraction**: pdfplumber, tabula-py (backup)

### Detection Models
- **Text Detection**:
  - OpenAI API (GPT-4)
  - HuggingFace Transformers (RoBERTa-based detectors)
  - Custom linguistic analyzers
- **Image Detection**:
  - Pre-trained CNN (ResNet50/EfficientNet via PyTorch)
  - Custom forensic analysis tools

### Web Interface
- **Backend**: Flask or FastAPI
- **Frontend**: HTML5, CSS3, JavaScript (vanilla or minimal framework)
- **File Upload**: Resumable.js for large files

### CLI Tool
- **Framework**: Click or Typer
- **Progress Display**: Rich library

### Configuration & Environment
- **Environment Variables**: python-dotenv (.env file)
- **Configuration**: YAML or JSON config files

### Development Tools
- **Package Manager**: pip + requirements.txt (or Poetry)
- **Code Quality**: black, flake8, mypy
- **Testing**: pytest

---

## 5. Data Flow

### 5.1 Processing Flow

```
Input PDF
    ↓
Validate & Parse (check corruption, page count)
    ↓
Select Pages (user can specify range or all)
    ↓
For each page:
    ├─→ Extract Text (native + OCR)
    ├─→ Extract Images
    ├─→ Extract Tables
    └─→ Classification
         ↓
    Determine Content Type(s)
         ↓
    Route to Appropriate Detector(s):
         ├─→ Text → Text Detection Engine → Results
         ├─→ Image → Image Detection Engine → Results
         └─→ Table → Table Detection Engine → Results
         ↓
    Aggregate Results per Page
         ↓
Store Results in Memory
    ↓
Generate HTML Report
    ↓
Save Report to File
    ↓
Display Summary (CLI) / Show Report (Web UI)
```

### 5.2 Error Handling Flow

```
At each stage:
    Try:
        Execute operation
    Except CriticalError (corrupted PDF, API unavailable):
        ├─→ Log error
        ├─→ Display alert message
        └─→ Exit gracefully
    Except PageError (single page failed):
        ├─→ Mark page as "FAILED" in report
        ├─→ Log error with page number
        └─→ Continue to next page
    Except InconclusiveResult (confidence < threshold):
        ├─→ Mark as "INCONCLUSIVE" in report
        ├─→ Provide explanation
        └─→ Continue processing
```

---

## 6. Project Structure

```
check-ai-generated-content/
├── README.md
├── DESIGN.md
├── LICENSE
├── requirements.txt
├── .env.example
├── .gitignore
│
├── config/
│   ├── default.yaml          # Default configuration
│   └── models.yaml            # Model paths and parameters
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py       # PDF extraction logic
│   │   ├── content_classifier.py  # Content type classification
│   │   └── page_processor.py      # Main page processing orchestrator
│   │
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── base_detector.py       # Abstract base class
│   │   ├── text/
│   │   │   ├── __init__.py
│   │   │   ├── openai_detector.py
│   │   │   ├── roberta_detector.py
│   │   │   ├── linguistic_analyzer.py
│   │   │   └── ensemble_text.py
│   │   ├── image/
│   │   │   ├── __init__.py
│   │   │   ├── cnn_detector.py
│   │   │   ├── forensic_analyzer.py
│   │   │   └── ensemble_image.py
│   │   └── model_identifier.py    # AI model identification
│   │
│   ├── report/
│   │   ├── __init__.py
│   │   ├── report_generator.py    # HTML report generation
│   │   ├── visualizer.py          # Bounding box visualization
│   │   └── templates/
│   │       └── report_template.html
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration loader
│   │   ├── logger.py              # Logging setup
│   │   ├── validators.py          # Input validation
│   │   └── error_handlers.py      # Error handling utilities
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py                # CLI interface
│   │
│   └── web/
│       ├── __init__.py
│       ├── app.py                 # Flask/FastAPI app
│       ├── routes.py              # API routes
│       └── static/
│           ├── css/
│           ├── js/
│           └── uploads/
│
├── models/
│   ├── text/
│   │   └── roberta_detector/      # Pre-trained model files
│   └── image/
│       └── cnn_detector/          # Pre-trained model files
│
├── tests/
│   ├── __init__.py
│   ├── test_pdf_extractor.py
│   ├── test_detectors.py
│   ├── test_report_generator.py
│   └── fixtures/
│       └── sample_pdfs/
│
├── outputs/
│   └── reports/                   # Generated HTML reports
│
└── docs/
    ├── API.md                     # API documentation
    ├── CLI_USAGE.md               # CLI usage guide
    └── WEB_UI.md                  # Web UI guide
```

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal**: Set up project structure and core extraction

- [ ] Initialize project structure
- [ ] Set up virtual environment and dependencies
- [ ] Implement PDF extraction module
  - Text extraction
  - Image extraction
  - Table extraction
  - OCR integration
- [ ] Implement content classification module
- [ ] Create basic logging and error handling
- [ ] Write unit tests for extraction

**Deliverable**: Working PDF extraction that outputs structured data per page

### Phase 2: Text Detection (Week 2)
**Goal**: Implement all text detection methods

- [ ] Implement OpenAI API detector
  - API integration
  - Prompt engineering for detection
  - Model identification logic
- [ ] Implement RoBERTa-based detector
  - Model loading and inference
  - Result formatting
- [ ] Implement linguistic feature analyzer
  - Perplexity calculation
  - Burstiness measurement
  - Entropy analysis
- [ ] Implement ensemble voting system
- [ ] Write unit tests for text detection
- [ ] Test on sample documents

**Deliverable**: Working text detection with ensemble results

### Phase 3: Image Detection (Week 3)
**Goal**: Implement image detection methods

- [ ] Implement or fine-tune CNN-based detector
  - Model selection (ResNet50 vs. EfficientNet)
  - Training on AI image dataset (if needed)
  - Inference pipeline
- [ ] Implement forensic analyzer
  - JPEG artifact analysis
  - Noise pattern detection
  - Frequency domain analysis
- [ ] Integrate OCR for text in images
- [ ] Implement ensemble for image detection
- [ ] Write unit tests for image detection

**Deliverable**: Working image detection pipeline

### Phase 4: Reporting (Week 4)
**Goal**: Generate comprehensive HTML reports

- [ ] Design HTML report template
  - Responsive layout
  - Visual styling (color coding)
  - Bounding box overlays
- [ ] Implement report generator
  - Per-page result formatting
  - Explanation generation
  - Confidence scoring
- [ ] Implement visualization module
  - Bounding box drawing
  - Page image rendering
  - Interactive elements (optional)
- [ ] Test report generation with various scenarios

**Deliverable**: Polished HTML reports with all required information

### Phase 5: CLI Interface (Week 5)
**Goal**: Build command-line interface

- [ ] Implement CLI using Click/Typer
  - PDF input argument
  - Page range selection
  - Configuration options
  - Progress indicators (Rich library)
- [ ] Implement batch processing
- [ ] Add configuration file support
- [ ] Write CLI documentation
- [ ] Test CLI with various use cases

**Deliverable**: Fully functional CLI tool

### Phase 6: Web Interface (Week 6)
**Goal**: Build web UI

- [ ] Set up Flask/FastAPI application
- [ ] Implement file upload endpoint
  - Large file support (up to 450 pages)
  - Validation
- [ ] Implement processing endpoint
  - Job queue for batch processing
  - Progress tracking
- [ ] Create frontend
  - Upload interface
  - Page range selection
  - Results display
  - Report viewing
- [ ] Test web interface
- [ ] Write web UI documentation

**Deliverable**: Working web interface

### Phase 7: Integration & Testing (Week 7)
**Goal**: End-to-end testing and refinement

- [ ] Integration testing
  - Test full pipeline with real documents
  - Test edge cases
  - Test error handling
- [ ] Performance optimization
  - Profile slow components
  - Optimize inference times
  - Memory usage optimization
- [ ] Documentation
  - README with setup instructions
  - API documentation
  - User guides
- [ ] Create example datasets
  - Sample PDFs for testing
  - Expected output examples

**Deliverable**: Production-ready system

### Phase 8: Polish & Deployment (Week 8)
**Goal**: Final refinements

- [ ] Code cleanup and refactoring
- [ ] Final testing on Mac
- [ ] Create installation guide
- [ ] Add error message improvements
- [ ] Performance benchmarking
- [ ] Create demo video/screenshots

**Deliverable**: Deployable system ready for use

---

## 8. Key Design Decisions

### 8.1 Why PyMuPDF over other PDF libraries?
- Excellent performance for large PDFs
- Strong image extraction capabilities
- Good text positioning data
- Active maintenance
- Complemented by pdfplumber for table extraction

### 8.2 Why Ensemble Approach for Detection?
- No single detector is 100% accurate
- Combining multiple methods increases reliability
- Provides confidence scoring based on agreement
- Allows adaptation as AI models evolve

### 8.3 Why Synchronous Processing?
- Simpler implementation for local machine use
- Easier debugging and error tracking
- User can monitor progress in real-time
- No need for complex job queue on single-user system

### 8.4 Why HTML Reports?
- Rich visual representation with images
- Interactive elements possible
- Easy to view on any device
- Can be archived and shared
- Supports embedded images (base64)

### 8.5 Why Local Processing + OpenAI API Hybrid?
- Balances accuracy (OpenAI) with privacy (local models)
- Local models handle bulk of processing
- API used for validation and model identification
- Cost-effective for moderate usage

---

## 9. Estimated Costs & Resources

### API Costs (OpenAI)
- Text detection: ~$0.01-0.03 per page
- For 450-page document: ~$4.50-$13.50
- Monthly usage (estimate 10 documents/month): ~$45-$135

### Compute Requirements (Mac)
- **RAM**: 16GB minimum (for model loading)
- **Storage**: ~5GB for models and dependencies
- **Processing Time**:
  - Text-only page: ~5-10 seconds
  - Image-heavy page: ~15-30 seconds
  - 450-page document: ~1.5-3 hours

### Model Storage
- RoBERTa text detector: ~500MB
- CNN image detector: ~100-300MB
- Tesseract OCR data: ~50MB

---

## 10. Future Enhancements (Post-MVP)

1. **Multi-language Support**: Extend to non-English content
2. **Video Analysis**: Detect AI-generated video frames
3. **Audio Detection**: Detect AI-generated voice/audio
4. **Parallel Processing**: Multi-page parallel processing
5. **Cloud Deployment**: AWS/GCP deployment option
6. **API Service**: REST API for integration
7. **Database Storage**: Store analysis history
8. **Improved Model Identification**: Fine-tune for specific AI models
9. **Watermark Detection**: Detect invisible AI watermarks
10. **Export Formats**: JSON, CSV, PDF annotations

---

## 11. Success Metrics

- **Accuracy**: ≥80% correct detection rate
- **Processing Speed**: <30 seconds per page average
- **Report Quality**: Clear, actionable insights with visual highlighting
- **Reliability**: <5% failure rate on valid PDFs
- **User Experience**: Easy setup, intuitive interface

---

## Next Steps

1. **Review & Approve Design**: Please review this design document
2. **Setup Environment**: Prepare development environment
3. **Begin Phase 1**: Start with PDF extraction module
4. **Iterative Development**: Build and test incrementally

---

*Document Version: 1.0*
*Last Updated: 2026-01-16*
