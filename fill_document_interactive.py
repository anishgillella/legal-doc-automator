#!/usr/bin/env python3
"""
Fill document with user-provided values interactively
With LLM-powered input validation, formatting, and ambiguity detection

Usage: python fill_document_interactive.py <path_to_document.docx>
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.document_processor import DocumentProcessor
from backend.input_validator import validate_user_input


# Get document path from command line argument
if len(sys.argv) < 2:
    print("❌ Usage: python fill_document_interactive.py <path_to_document.docx>")
    print("\nExample:")
    print('  python fill_document_interactive.py "/Users/anishgillella/Desktop/Stuff/Projects/Lexys AI/rent-receipt.docx"')
    sys.exit(1)

DOCUMENT_PATH = sys.argv[1]

# Verify document exists
if not os.path.exists(DOCUMENT_PATH):
    print(f"❌ Error: Document not found at {DOCUMENT_PATH}")
    sys.exit(1)


def get_user_input_with_validation(
    placeholder_text: str, 
    placeholder_name: str, 
    suggested_question: str,
    data_type: str,
    example: str = None
) -> str:
    """
    Get user input with LLM validation, formatting, and retry logic
    
    Args:
        placeholder_text: Exact placeholder text
        placeholder_name: Field name
        suggested_question: Question to ask user
        data_type: Expected data type
        example: Example value
    
    Returns:
        Validated and formatted user input
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        # Get user input
        print(f"\n{'='*70}")
        print(f"Placeholder: {placeholder_text}")
        print(f"Field: {placeholder_name}")
        print(f"Question: {suggested_question}")
        if example:
            print(f"Example: {example}")
        
        user_input = input(f"\n>>> Enter value: ").strip()
        
        if not user_input:
            print("⚠️  Value cannot be empty. Please try again.")
            retry_count += 1
            continue
        
        # Validate using LLM
        print(f"\n⏳ Validating input...")
        validation = validate_user_input(
            user_input, 
            placeholder_name, 
            data_type, 
            suggested_question
        )
        
        # Check validation result
        if validation.is_valid and not validation.is_ambiguous:
            # Check if value was formatted
            if validation.formatted_value != user_input:
                # ✏️ Value was formatted - ask for confirmation
                print(f"\n✏️  LLM formatted your input:")
                print(f"  Original: '{user_input}'")
                print(f"  Formatted: '{validation.formatted_value}'")
                confirm = input(f"\nIs this correct? (yes/no): ").strip().lower()
                
                if confirm == 'yes':
                    print(f"✓ Confirmed with {validation.confidence:.0%} confidence")
                    return validation.formatted_value
                else:
                    print(f"  Please enter again or provide the correct value:")
                    retry_count += 1
                    continue
            else:
                # ✅ No formatting, value is valid and clear!
                print(f"✓ {validation.message}")
                print(f"✓ Value accepted with {validation.confidence:.0%} confidence")
                return validation.formatted_value
        
        elif validation.is_ambiguous:
            # ❓ Needs clarification
            print(f"⚠️  {validation.message}")
            if validation.clarification_needed:
                clarification = input(f"\n{validation.clarification_needed}\n>>> Enter 'yes' or provide corrected value: ").strip().lower()
                
                if clarification == 'yes':
                    print(f"✓ Confirmed: {validation.formatted_value}")
                    return validation.formatted_value
                else:
                    # User provided correction
                    print(f"  Using corrected value: {clarification}")
                    return clarification
        
        else:
            # ❌ Invalid
            print(f"❌ {validation.message}")
            retry_count += 1
            
            if retry_count < max_retries:
                print(f"   Attempt {retry_count}/3 failed. Please try again.")
            else:
                print(f"\n   ❌ Max retries ({max_retries}) reached.")
                # Ask if user wants to force it
                force = input(f"   Force accept '{user_input}' anyway? (yes/no): ").strip().lower()
                if force == 'yes':
                    print(f"   ⚠️  Using unvalidated value: {user_input}")
                    return user_input
                else:
                    print(f"   Skipping this field.")
                    return None
    
    return None


print("\n" + "="*70)
print("INTERACTIVE DOCUMENT FILLER (WITH LLM VALIDATION)")
print("="*70)
print(f"\nDocument: {os.path.basename(DOCUMENT_PATH)}")

# Process document
processor = DocumentProcessor(DOCUMENT_PATH)
result = processor.process(analyze_with_llm=True)

if not result.get('success'):
    print("❌ Error loading document")
    sys.exit(1)

print(f"✓ Document loaded with {result['placeholder_count']} placeholders")

if result['placeholder_count'] == 0:
    print("\n⚠️  No placeholders found in document!")
    sys.exit(0)

print("\nLet's fill them in with LLM validation...\n")

# Collect user values with validation
placeholder_values = {}
skipped = []

if result.get('analyses'):
    for i, analysis in enumerate(result['analyses'], 1):
        placeholder_text = analysis['placeholder_text']
        placeholder_name = analysis['placeholder_name']
        suggested_question = analysis.get('suggested_question')
        data_type = analysis.get('data_type')
        example = analysis.get('example')
        
        # Skip if already filled
        if placeholder_text in placeholder_values:
            print(f"\n✓ {placeholder_text} (already filled)")
            continue
        
        # Get validated input
        value = get_user_input_with_validation(
            placeholder_text,
            placeholder_name,
            suggested_question,
            data_type,
            example
        )
        
        if value is not None:
            placeholder_values[placeholder_text] = value
            print(f"✓ Value saved: {value}")
        else:
            skipped.append(placeholder_text)
            print(f"⊘ Field skipped")

print("\n" + "="*70)
print("FILLING DOCUMENT...")
print("="*70)

# Fill the document
success, output_path = processor.fill_placeholders(placeholder_values)

if success:
    print(f"\n✅ Document filled successfully!")
    
    # Save to same directory as source document
    base_name = os.path.splitext(os.path.basename(DOCUMENT_PATH))[0]
    output_filename = f"{base_name}_Filled.docx"
    output_project_path = os.path.join(
        os.path.dirname(DOCUMENT_PATH),
        output_filename
    )
    
    import shutil
    shutil.copy(output_path, output_project_path)
    
    print(f"\n💾 Saved: {output_filename}")
    print(f"📍 Path: {output_project_path}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY:")
    print("="*70)
    
    print(f"\n✓ Filled fields ({len(placeholder_values)}):")
    for ph_text, value in placeholder_values.items():
        print(f"  • {ph_text:25} → {value}")
    
    if skipped:
        print(f"\n⊘ Skipped fields ({len(skipped)}):")
        for ph in skipped:
            print(f"  • {ph}")
    
    print("\n" + "="*70)
    print("✅ COMPLETE! Document is ready.")
    print("="*70)
else:
    print(f"❌ Failed to fill document")
    sys.exit(1)
