#!/usr/bin/env python3
"""
Main script for processing Word documents
Takes a docx file, detects placeholders with python-docx and LLM,
gets user answers, and fills the document
"""

import sys
import os
from pathlib import Path
from document_processor import DocumentProcessor
from llm_analyzer import LLMAnalyzer


def get_user_input(question: str, example: str = "", data_type: str = "string") -> str:
    """
    Prompt user for input with validation hints
    
    Args:
        question: The question to ask
        example: Example value to show
        data_type: Type of data expected
    
    Returns:
        User's input
    """
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    if example:
        print(f"Example: {example}")
    if data_type:
        print(f"Type: {data_type}")
    print(f"{'='*60}")
    
    while True:
        answer = input("Your answer (or 'skip' to leave blank): ").strip()
        
        if answer.lower() == 'skip':
            return ""
        
        if answer:
            return answer
        else:
            print("Please provide an answer or type 'skip' to leave blank.")


def process_document(doc_path: str):
    """
    Main processing function
    
    Args:
        doc_path: Path to the .docx file
    """
    print("=" * 60)
    print("Lexsy Document AI - Document Processor")
    print("=" * 60)
    print(f"\nProcessing: {doc_path}\n")
    
    # Step 1: Load and detect placeholders with python-docx
    print("Step 1: Loading document and detecting placeholders...")
    processor = DocumentProcessor(doc_path)
    result = processor.process()
    
    if not result.get('success'):
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        return
    
    placeholders_count = result.get('placeholder_count', 0)
    print(f"✓ Found {placeholders_count} placeholders using python-docx\n")
    
    if placeholders_count == 0:
        print("No placeholders detected. Document may already be filled or use a different format.")
        return
    
    # Step 2: Analyze with LLM
    print("Step 2: Analyzing placeholders with LLM...")
    try:
        llm_analyzer = LLMAnalyzer()
        full_text = processor.full_text
        
        # Use LLM to detect and analyze all fields
        analyses = llm_analyzer.detect_all_fields(full_text)
        
        if not analyses:
            print("⚠ LLM did not detect fields. Using regex-detected placeholders...")
            # Fallback: use regex placeholders
            placeholders_data = result.get('placeholders', [])
            analyses = []
            for ph in placeholders_data:
                from llm_analyzer import PlaceholderAnalysis
                analyses.append(PlaceholderAnalysis(
                    placeholder_text=ph['text'],
                    placeholder_name=ph['name'],
                    data_type='string',
                    description=f"Field: {ph['name']}",
                    suggested_question=f"What is the {ph['name'].lower().replace('_', ' ')}?",
                    example="",
                    required=False,
                    validation_hint=None
                ))
        
        print(f"✓ LLM analyzed {len(analyses)} unique fields\n")
        
    except Exception as e:
        print(f"⚠ LLM analysis failed: {e}")
        print("Using basic placeholder detection...")
        # Fallback to basic analysis
        placeholders_data = result.get('placeholders', [])
        analyses = []
        for ph in placeholders_data:
            from llm_analyzer import PlaceholderAnalysis
            analyses.append(PlaceholderAnalysis(
                placeholder_text=ph['text'],
                placeholder_name=ph['name'],
                data_type='string',
                description=f"Field: {ph['name']}",
                suggested_question=f"What is the {ph['name'].lower().replace('_', ' ')}?",
                example="",
                required=False,
                validation_hint=None
            ))
    
    # Step 3: Get user answers
    print("Step 3: Collecting user answers...")
    print(f"\nYou'll be asked {len(analyses)} questions. Answer each one or type 'skip' to leave blank.\n")
    
    values = {}
    for i, analysis in enumerate(analyses, 1):
        print(f"\n[{i}/{len(analyses)}]")
        answer = get_user_input(
            question=analysis.suggested_question,
            example=analysis.example,
            data_type=analysis.data_type
        )
        
        if answer:
            # Map answer to placeholder text
            values[analysis.placeholder_text] = answer
    
    if not values:
        print("\n⚠ No values provided. Exiting without filling document.")
        return
    
    # Step 4: Fill placeholders
    print(f"\nStep 4: Filling {len(values)} placeholders in document...")
    success, output_path = processor.fill_placeholders(values)
    
    if success:
        print(f"\n{'='*60}")
        print("✓ SUCCESS!")
        print(f"✓ Filled document saved to: {output_path}")
        print(f"{'='*60}\n")
    else:
        print("\n❌ Failed to fill document")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_document.docx>")
        print("\nExample:")
        print("  python main.py samples/rent-receipt.docx")
        sys.exit(1)
    
    doc_path = sys.argv[1]
    
    # Validate file exists
    if not os.path.exists(doc_path):
        print(f"❌ Error: File not found: {doc_path}")
        sys.exit(1)
    
    # Validate file extension
    if not doc_path.lower().endswith('.docx'):
        print(f"❌ Error: File must be a .docx file")
        sys.exit(1)
    
    try:
        process_document(doc_path)
    except KeyboardInterrupt:
        print("\n\n⚠ Process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

