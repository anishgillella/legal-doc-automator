#!/usr/bin/env python3
"""
Simulation script to test document processing with predefined values
Uses the same values from the terminal output to test Address field replacement
"""

import sys
import os
from pathlib import Path
from document_processor import DocumentProcessor
from llm_analyzer import LLMAnalyzer


def simulate_document_processing(doc_path: str):
    """
    Simulate document processing with predefined answers
    
    Args:
        doc_path: Path to the .docx file
    """
    print("=" * 60)
    print("Lexsy Document AI - Simulation Test")
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
    
    # Step 2: Analyze with LLM
    print("Step 2: Analyzing placeholders with LLM...")
    try:
        llm_analyzer = LLMAnalyzer()
        full_text = processor.full_text
        
        # Use LLM to analyze regex-detected placeholders with context
        placeholders_data = result.get('placeholders', [])
        analyses = llm_analyzer.analyze_placeholders_with_context(full_text, placeholders_data)
        
        if not analyses:
            print("⚠ LLM did not detect fields. Using regex-detected placeholders...")
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
    
    # Step 3: Map predefined answers to analyses
    print("Step 3: Using predefined answers (simulation)...")
    print(f"\nUsing {len(analyses)} predefined answers\n")
    
    # Predefined answers matching the terminal output
    predefined_answers = {
        'company_name': 'Acme Corp',
        'investor_name': 'Anish Gil',
        'purchase_amount': '100000',
        'post_money_valuation_cap': '5000000',
        'date_of_safe': '2023-10-01',
        'state_of_incorporation': 'Delaware',
        'governing_law_jurisdiction': 'California',
        'company_signature_name': 'jane Smith',
        'company_signature_title': 'CTO',
        'company_address': '123 Main St, Suite 400, Anytown, USA',
        'company_email': 'info@acmecorp.com',
        'investor_signature_name': 'Jagan Gil',
        'investor_signature_title': 'MD',
        'investor_address': '456 Elm St, Suite 200, Anytown, USA',
        'investor_email': 'john.doe@example.com',
        'by': '',  # skip
        'investor': 'Sequioa',
        'company': 'Sequioa Capital',
    }
    
    # Check for duplicate placeholder texts with different field names
    placeholder_text_counts = {}
    for analysis in analyses:
        text = analysis.placeholder_text
        if text not in placeholder_text_counts:
            placeholder_text_counts[text] = []
        placeholder_text_counts[text].append(analysis.placeholder_name)
    
    values = {}
    for i, analysis in enumerate(analyses, 1):
        field_name = analysis.placeholder_name
        
        # Get answer from predefined answers
        answer = predefined_answers.get(field_name, '')
        
        if answer:
            print(f"[{i}/{len(analyses)}] {field_name}: {answer}")
            # If multiple analyses have the same placeholder_text but different field_names,
            # use composite key to distinguish them
            if len(placeholder_text_counts[analysis.placeholder_text]) > 1:
                # Use composite key: placeholder_text__field_name
                key = f"{analysis.placeholder_text}__field_{analysis.placeholder_name}"
            else:
                # Single occurrence, use placeholder text directly
                key = analysis.placeholder_text
            values[key] = answer
        else:
            print(f"[{i}/{len(analyses)}] {field_name}: (skipped)")
    
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
        
        # Check if Address fields were replaced
        print("\n" + "=" * 60)
        print("VERIFICATION:")
        print("=" * 60)
        print("Please check the output document to verify:")
        print("  ✓ Company Address: 123 Main St, Suite 400, Anytown, USA")
        print("  ✓ Investor Address: 456 Elm St, Suite 200, Anytown, USA")
        print("  ✓ Company Email: info@acmecorp.com")
        print("  ✓ Investor Email: john.doe@example.com")
        print("=" * 60)
    else:
        print("\n❌ Failed to fill document")


def main():
    """Main entry point"""
    # Use the same document path from the terminal output
    default_doc_path = "/Users/anishgillella/Desktop/Stuff/Projects/Lexys AI/samples/Postmoney_Safe_-_Valuation_Cap_Only_-_FINAL-f2a64add6d21039ab347ee2e7194141a4239e364ffed54bad0fe9cf623bf1691_(4).docx"
    
    if len(sys.argv) >= 2:
        doc_path = sys.argv[1]
    else:
        doc_path = default_doc_path
    
    # Validate file exists
    if not os.path.exists(doc_path):
        print(f"❌ Error: File not found: {doc_path}")
        print(f"\nUsage: python test_simulation.py [path_to_document.docx]")
        print(f"Default: {default_doc_path}")
        sys.exit(1)
    
    # Validate file extension
    if not doc_path.lower().endswith('.docx'):
        print(f"❌ Error: File must be a .docx file")
        sys.exit(1)
    
    try:
        simulate_document_processing(doc_path)
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

