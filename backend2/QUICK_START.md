# Backend2 - Complete Implementation

## ✅ What's Been Created

1. **LLM Analyzer** (`llm_analyzer.py`) - Analyzes placeholders using OpenRouter API
2. **Main Script** (`main.py`) - Interactive script to process documents
3. **Updated Document Processor** - Now supports LLM analysis

## 🚀 How to Run

### 1. Setup Environment

Create a `.env` file in `backend2/` directory:
```bash
OPENROUTER_API_KEY=your_api_key_here
```

### 2. Install Dependencies

```bash
cd backend2
pip install -r requirements.txt
```

### 3. Run the Main Script

```bash
python main.py samples/rent-receipt.docx
```

Or with absolute path:
```bash
python main.py "/Users/anishgillella/Desktop/Stuff/Projects/Lexys AI/samples/rent-receipt.docx"
```

## 📋 What the Script Does

1. **Loads document** using python-docx
2. **Detects placeholders** using regex patterns
3. **Analyzes with LLM** to understand what each field needs
4. **Prompts user** for answers to each field
5. **Fills placeholders** in the document
6. **Saves filled document** to temp directory

## 🔧 Questions Found

The script detected placeholders but needs the API key for LLM analysis. Without it, it falls back to basic detection.

**To get full LLM analysis:**
1. Get an OpenRouter API key from https://openrouter.ai
2. Add it to `.env` file: `OPENROUTER_API_KEY=your_key`
3. Run the script again

## 📝 Example Output

```
============================================================
Lexsy Document AI - Document Processor
============================================================

Processing: samples/rent-receipt.docx

Step 1: Loading document and detecting placeholders...
✓ Found 20 placeholders using python-docx

Step 2: Analyzing placeholders with LLM...
📄 Document size: 1234 chars (small) - sending entire document
✓ LLM analyzed 8 unique fields

Step 3: Collecting user answers...
[1/8]
============================================================
Question: What is the tenant's name?
Example: John Doe
Type: string
============================================================
Your answer (or 'skip' to leave blank): 
```

## 🎯 Next Steps

1. Set up `.env` file with `OPENROUTER_API_KEY`
2. Run the script interactively
3. Answer the questions
4. Get your filled document!

