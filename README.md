# Lexsy Document AI - Backend

AI-powered legal document processor that automatically detects placeholders, analyzes their context, and enables intelligent document filling.

## Overview

This Python backend provides:

1. **Placeholder Detection** - Identifies various placeholder formats in .docx files using regex patterns
2. **LLM Analysis** - Uses Qwen2.5-VL through OpenRouter to understand placeholder context and requirements
3. **Document Filling** - Replaces detected placeholders with user-provided values while preserving formatting
4. **Conversational UX** - Generates natural questions for collecting placeholder values

## Architecture

### Core Modules

#### `document_handler.py`
- **Purpose**: Loads, parses, and modifies .docx files
- **Key Classes**: `DocumentHandler`
- **Capabilities**:
  - Extract text while preserving paragraph structure
  - Store formatting metadata (alignment, font, style)
  - Replace placeholders while preserving formatting
  - Save modified documents

#### `placeholder_detector.py`
- **Purpose**: Detects placeholders in document text
- **Key Classes**: `PlaceholderDetector`, `Placeholder`
- **Supported Formats**:
  - `_placeholder_` (underscore)
  - `__placeholder__` (double underscore)
  - `[placeholder]` (square brackets)
  - `{placeholder}` (curly brackets)
  - `{{placeholder}}` (double curly brackets)
  - `<placeholder>` (angle brackets)
- **Capabilities**:
  - Find all placeholders with exact positions
  - Extract placeholder names
  - Provide context around placeholders
  - Format data for LLM analysis

#### `llm_analyzer.py`
- **Purpose**: Analyzes placeholders using LLM to understand requirements
- **Key Classes**: `LLMAnalyzer`, `PlaceholderAnalysis`
- **Provider**: OpenRouter (Qwen2.5-VL)
- **Capabilities**:
  - Determine data type (string, email, currency, date, etc.)
  - Generate natural questions for users
  - Provide validation hints
  - Fallback heuristics if LLM fails

#### `document_processor.py`
- **Purpose**: Orchestrates the entire workflow
- **Key Classes**: `DocumentProcessor`
- **Workflow**:
  1. Load document
  2. Extract text
  3. Detect placeholders
  4. Analyze with LLM (optional)
  5. Fill placeholders
  6. Save output

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure OpenRouter API**:
   - Get API key from https://openrouter.io
   - Add to `.env` file:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

## Usage

### Basic Usage

```python
from document_processor import DocumentProcessor

# Initialize processor
processor = DocumentProcessor("path/to/document.docx")

# Process document (detect placeholders + LLM analysis)
result = processor.process(analyze_with_llm=True)

print(f"Found {result['placeholder_count']} placeholders")
for ph in result['placeholders']:
    print(f"- {ph['text']}: {ph['format']}")
```

### Detection Only (No LLM)

```python
processor = DocumentProcessor("path/to/document.docx")
result = processor.process(analyze_with_llm=False)
```

### Fill Placeholders

```python
# Fill by placeholder name
values = {
    "founder_name": "John Doe",
    "company_name": "Acme Inc",
    "valuation_cap": "$1,000,000"
}

success, output_path = processor.fill_by_name(values)

if success:
    print(f"Filled document saved to: {output_path}")
```

### Get Placeholder Information

```python
placeholder_info = processor.get_placeholder_info()

for info in placeholder_info:
    print(f"Name: {info['name']}")
    print(f"Type: {info['analysis']['data_type']}")
    print(f"Question: {info['analysis']['suggested_question']}")
    print(f"Example: {info['analysis']['example']}")
```

## API Response Format

### Process Result

```json
{
  "success": true,
  "document_path": "path/to/document.docx",
  "text_length": 5000,
  "placeholder_count": 5,
  "placeholders": [
    {
      "text": "_founder_name_",
      "name": "founder_name",
      "format": "underscore",
      "position": 1234
    }
  ],
  "analyses": [
    {
      "placeholder_text": "_founder_name_",
      "placeholder_name": "founder_name",
      "data_type": "string",
      "description": "The name of the lead founder",
      "suggested_question": "What is the founder's full name?",
      "example": "Jane Smith",
      "required": true,
      "validation_hint": null
    }
  ],
  "analyzed": true
}
```

## Placeholder Detection

### Regex Patterns

The system uses these regex patterns (in order of precedence):

1. `__([a-zA-Z0-9_\s]+)__` - Double underscore
2. `_([a-zA-Z0-9_\s]+)_` - Single underscore
3. `\[([a-zA-Z0-9_\s]+)\]` - Square brackets
4. `\{([a-zA-Z0-9_\s]+)\}` - Curly brackets
5. `\{\{([a-zA-Z0-9_\s]+)\}\}` - Double curly brackets
6. `<([a-zA-Z0-9_\s]+)>` - Angle brackets

### Custom Patterns

To add custom placeholder patterns, modify the `patterns` list in `placeholder_detector.py`:

```python
self.patterns = [
    (r'custom_regex_pattern', 'format_name'),
    # ... existing patterns ...
]
```

## LLM Integration

### Model Configuration

- **Provider**: OpenRouter
- **Model**: `qwen/qwen2.5-72b-instruct`
- **Temperature**: 0.3 (for consistency)
- **Max Tokens**: 4000

### Customizing Analysis

Modify the prompt in `llm_analyzer.py`'s `_build_analysis_prompt()` method to change how placeholders are analyzed.

### Fallback Behavior

If LLM analysis fails, the system falls back to heuristic-based analysis:
- Checks placeholder name for type hints (email, amount, date, etc.)
- Generates basic descriptions
- Sets reasonable defaults

## Testing

Run the test suite:

```bash
python test_backend.py
```

Tests include:
1. **Placeholder Detection** - Verifies placeholder finding
2. **LLM Analysis** - Tests LLM integration
3. **Placeholder Filling** - Tests document modification

## Document Formatting Preservation

The system preserves:
- ✓ Paragraph alignment (left, center, right)
- ✓ Paragraph spacing
- ✓ Font properties (name, size)
- ✓ Text formatting (bold, italic, underline)
- ✓ Font color
- ✓ Document structure

### How It Works

1. When replacing placeholders, the system:
   - Identifies the paragraph containing the placeholder
   - Extracts formatting from the first run (text segment)
   - Replaces placeholder text
   - Applies original formatting to replacement text

2. Paragraph-level properties are automatically preserved by `python-docx`

## Dependencies

```
python-docx==0.8.11    # .docx file handling
requests==2.31.0       # HTTP requests for OpenRouter API
python-dotenv==1.0.0   # Environment variable management
Pillow==10.1.0         # Image processing (if needed for future VL capabilities)
regex==2023.11.8       # Advanced regex patterns
```

## Error Handling

### Common Issues

**Issue**: `OpenRouter API key not found`
- **Solution**: Add `OPENROUTER_API_KEY` to `.env` file

**Issue**: Placeholder not replaced
- **Possible Causes**:
  - Placeholder text doesn't exactly match (case-sensitive)
  - Placeholder split across multiple runs in .docx

**Issue**: LLM analysis fails
- **Solution**: System falls back to heuristic analysis. Check OpenRouter API status.

## Performance

- **Placeholder Detection**: < 100ms for typical documents
- **LLM Analysis**: 2-5 seconds (depends on OpenRouter API)
- **Placeholder Filling**: < 200ms
- **Document Saving**: < 500ms

## Roadmap

- [ ] Batch processing multiple documents
- [ ] Template creation and management
- [ ] Placeholder validation rules
- [ ] Multi-language support
- [ ] PDF support
- [ ] Document signing integration

## License

Internal use only - Lexsy AI

## Support

For issues or questions, contact: tech@lexsy.ai
