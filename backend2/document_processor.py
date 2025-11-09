"""
Document Processor for backend2
Orchestrates placeholder detection and replacement
"""

import os
import json
from typing import Dict, List, Optional, Tuple

from document_handler import DocumentHandler
from placeholder_detector import PlaceholderDetector, detect_placeholders_simple
from llm_analyzer import LLMAnalyzer, PlaceholderAnalysis


class DocumentProcessor:
    def __init__(self, doc_path: str):
        """
        Initialize document processor
        
        Args:
            doc_path: Path to the .docx file
        """
        self.doc_path = doc_path
        self.doc_handler = DocumentHandler(doc_path)
        self.placeholder_detector = PlaceholderDetector()
        self.llm_analyzer = None
        
        self.full_text = None
        self.placeholders = None
        self.placeholder_analyses = None
    
    def process(self) -> Dict:
        """
        Full processing pipeline:
        1. Load document
        2. Extract text
        3. Detect placeholders
        
        Returns:
            Dictionary with processing results
        """
        # Step 1: Load document
        if not self.doc_handler.load_document():
            return {"error": "Failed to load document"}
        
        self.full_text = self.doc_handler.get_full_text()
        
        # Step 2: Detect placeholders
        self.placeholders = self.placeholder_detector.detect_placeholders(self.full_text)
        
        if not self.placeholders:
            return {
                "success": True,
                "message": "Document loaded but no placeholders detected",
                "document_path": self.doc_path,
                "text_length": len(self.full_text),
                "placeholder_count": 0,
                "placeholders": [],
            }
        
        # Convert to dict format for JSON serialization
        placeholders_data = []
        # Group placeholders by text to show occurrences
        placeholder_groups = {}
        for idx, p in enumerate(self.placeholders):
            placeholder_groups.setdefault(p.text, []).append({
                'index': idx,
                'text': p.text,
                'name': p.name,
                'format': p.format_type,
                'position': p.position,
                'end_position': p.end_position,
                'detected_by': p.detected_by,
                'position_index': len(placeholder_groups.get(p.text, []))  # 0-based index for this specific placeholder text
            })
        
        # Flatten for backward compatibility
        for group in placeholder_groups.values():
            placeholders_data.extend(group)
        
        # Add summary of occurrences
        occurrences_summary = {}
        for text, occurrences in placeholder_groups.items():
            occurrences_summary[text] = len(occurrences)
        
        result = {
            "success": True,
            "message": f"Document processed successfully. Found {len(self.placeholders)} placeholders.",
            "document_path": self.doc_path,
            "text_length": len(self.full_text),
            "placeholder_count": len(self.placeholders),
            "placeholders": placeholders_data,
            "occurrences_summary": occurrences_summary  # Shows how many times each placeholder appears
        }
        
        return result
    
    def fill_placeholders(self, values: Dict[str, str]) -> Tuple[bool, str]:
        """
        Fill placeholders with provided values
        
        Args:
            values: Dictionary mapping placeholder text -> replacement value
                   Supports both direct text keys and position-based keys (text__pos_N)
                   e.g., {"[Name]": "John Doe", "[Company Name]__pos_0": "Acme Inc"}
        
        Returns:
            Tuple of (success: bool, output_path: str)
        """
        try:
            # IMPORTANT: Load the document first!
            if not self.doc_handler.load_document():
                print("Failed to load document")
                return False, ""
            
            # Ensure placeholders are detected (needed for counting occurrences)
            if self.placeholders is None:
                self.full_text = self.doc_handler.get_full_text()
                self.placeholders = self.placeholder_detector.detect_placeholders(self.full_text)
            
            total_replacements = 0
            
            # Separate different types of keys
            placeholder_keys = {}  # placeholder_text -> value
            position_based = {}    # placeholder__pos_N -> value
            
            for key, value in values.items():
                if '__pos_' in key:
                    position_based[key] = value
                else:
                    # This is a placeholder text
                    placeholder_keys[key] = value
            
            # Priority 1: Position-based replacements (more specific)
            if position_based:
                print(f"✓ Using {len(position_based)} position-based replacements\n")
                for key, value in position_based.items():
                    placeholder_text = key.rsplit('__pos_', 1)[0]
                    try:
                        position = int(key.rsplit('__pos_', 1)[1])
                        success = self.doc_handler.replace_placeholder_at_position(placeholder_text, value, position)
                        if success:
                            total_replacements += 1
                            print(f"  ✓ Replaced: {key:40} → {value[:25]}")
                        else:
                            # Fallback to regular replacement
                            success = self.doc_handler.replace_placeholder(placeholder_text, value)
                            if success:
                                total_replacements += 1
                                print(f"  ✓ Fallback: {key:40} → {value[:25]}")
                            else:
                                print(f"  ✗ Failed: {key}")
                    except Exception as e:
                        print(f"  Error: {key}: {e}")
                
                print()
            
            # Priority 2: Plain placeholder text replacements
            # For placeholders that appear multiple times, replace ALL occurrences with the same value
            if placeholder_keys:
                print(f"✓ Using {len(placeholder_keys)} placeholder-based replacements\n")
                for placeholder_text, value in placeholder_keys.items():
                    # Count how many times this placeholder appears
                    occurrences_count = sum(1 for p in self.placeholders if p.text == placeholder_text)
                    
                    if occurrences_count > 1:
                        # Replace all occurrences one by one
                        # IMPORTANT: Replace in reverse order (last to first) to avoid position shifts
                        replaced_this_placeholder = 0
                        for i in range(occurrences_count - 1, -1, -1):  # Reverse order: last occurrence first
                            success = self.doc_handler.replace_placeholder_at_position(placeholder_text, value, i)
                            if success:
                                replaced_this_placeholder += 1
                                total_replacements += 1
                        
                        if replaced_this_placeholder > 0:
                            print(f"  ✓ Replaced: {placeholder_text:40} → {value[:25]} ({replaced_this_placeholder}/{occurrences_count} occurrences)")
                        else:
                            print(f"  ✗ Failed:   {placeholder_text} (0/{occurrences_count} occurrences)")
                    else:
                        # Single occurrence, use regular replacement
                        success = self.doc_handler.replace_placeholder(placeholder_text, value)
                        if success:
                            total_replacements += 1
                            print(f"  ✓ Replaced: {placeholder_text:40} → {value[:25]}")
                        else:
                            # Debug: check if placeholder exists
                            matching_placeholders = [p for p in self.placeholders if p.text == placeholder_text]
                            if matching_placeholders:
                                print(f"  ✗ Failed:   {placeholder_text} (found {len(matching_placeholders)} occurrences but replacement failed)")
                            else:
                                print(f"  ✗ Failed:   {placeholder_text} (not found in document)")
                
                print()
            
            print(f"\n{'='*80}")
            print(f"RESULT: Successfully replaced {total_replacements}/{len(values)} placeholders")
            print(f"{'='*80}\n")
            
            # Save to output folder
            # Get the project root (parent of backend2)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            output_dir = os.path.join(project_root, "output")
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename based on input filename
            input_filename = os.path.basename(self.doc_path)
            name_without_ext = os.path.splitext(input_filename)[0]
            output_filename = f"{name_without_ext}_filled.docx"
            output_path = os.path.join(output_dir, output_filename)
            
            if self.doc_handler.save_document(output_path):
                return True, output_path
            else:
                print("Failed to save document")
                return False, ""
            
        except Exception as e:
            print(f"Error filling placeholders: {e}")
            import traceback
            traceback.print_exc()
            return False, ""
    
    def fill_by_name(self, values: Dict[str, str]) -> Tuple[bool, str]:
        """
        Fill placeholders by their extracted name (instead of full placeholder text)
        
        Args:
            values: Dictionary mapping placeholder name -> replacement value
                   e.g., {"name_of_tenant": "John Doe", "company_name": "Acme Inc"}
        
        Returns:
            Tuple of (success: bool, output_path: str)
        """
        try:
            # Convert placeholder names to full text
            replacements = {}
            for placeholder in self.placeholders:
                if placeholder.name in values:
                    replacements[placeholder.text] = values[placeholder.name]
            
            return self.fill_placeholders(replacements)
        
        except Exception as e:
            print(f"Error filling by name: {e}")
            return False, ""

