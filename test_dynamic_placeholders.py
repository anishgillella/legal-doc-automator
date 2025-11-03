"""Test script for dynamic placeholder detection"""
import sys
sys.path.insert(0, '/Users/anishgillella/Desktop/Stuff/Projects/Lexys\ AI/backend')

from placeholder_detector import PlaceholderDetector
from llm_analyzer import LLMAnalyzer

# Sample SAFE document text
sample_text = """
IN WITNESS WHEREOF, the undersigned have caused this Safe to be duly executed and delivered.

[COMPANY]

By: _____________________
    _____________________

Address: _____________________

Email: _____________________


INVESTOR:

By: _____________________

Name: _____________________

Title: _____________________

Address: _____________________

Email: _____________________
"""

print("=" * 60)
print("Testing Dynamic Placeholder Detection")
print("=" * 60)

# Test 1: Detect placeholders
print("\n1. DETECTING PLACEHOLDERS...")
detector = PlaceholderDetector()
placeholders = detector.detect_placeholders(sample_text)

print(f"\nFound {len(placeholders)} placeholders:")
for p in placeholders:
    print(f"  - Name: {p.name:20} | Type: {p.format_type:15} | Detected by: {p.detected_by}")

# Count by type
regex_count = sum(1 for p in placeholders if p.detected_by == 'regex')
heuristic_count = sum(1 for p in placeholders if p.detected_by == 'heuristic')
print(f"\nSummary: {regex_count} from regex, {heuristic_count} from blank field heuristic")

# Test 2: Show what fields were detected
print("\n2. DETECTED FIELDS BREAKDOWN:")
bracket_fields = [p for p in placeholders if p.format_type == 'bracket']
blank_fields = [p for p in placeholders if p.format_type == 'blank_field']

if bracket_fields:
    print("\n  Explicit Bracket Placeholders:")
    for p in bracket_fields:
        print(f"    - {p.name}")

if blank_fields:
    print("\n  Blank Field Placeholders:")
    for p in blank_fields:
        print(f"    - {p.name}")

print("\n" + "=" * 60)
print("✓ Dynamic placeholder detection test complete!")
print("=" * 60)
