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
            field_based = {}      # placeholder__field_fieldname -> value
            
            for key, value in values.items():
                if '__pos_' in key:
                    position_based[key] = value
                elif '__field_' in key:
                    field_based[key] = value
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
            
            # Priority 2: Field-based replacements (match by field_name and context)
            # IMPORTANT: Replace in reverse order (last to first) to avoid position shifts
            if field_based:
                print(f"✓ Using {len(field_based)} field-based replacements\n")
                
                # Group by placeholder_text to handle multiple occurrences
                placeholder_groups = {}
                for key, value in field_based.items():
                    parts = key.rsplit('__field_', 1)
                    if len(parts) != 2:
                        print(f"  ✗ Invalid field key format: {key}")
                        continue
                    
                    placeholder_text = parts[0]
                    field_name = parts[1]
                    
                    if placeholder_text not in placeholder_groups:
                        placeholder_groups[placeholder_text] = []
                    placeholder_groups[placeholder_text].append((field_name, value, key))
                
                # Process each placeholder text group
                for placeholder_text, field_entries in placeholder_groups.items():
                    # Normalize placeholder text for matching (handle whitespace variations)
                    def normalize_for_matching(text):
                        """Normalize text by extracting base label name"""
                        if ':' in text:
                            # Label field: extract label name before colon
                            return text.split(':')[0].strip().lower()
                        return text.strip().lower()
                    
                    normalized_search = normalize_for_matching(placeholder_text)
                    
                    # Find all occurrences that match (normalize both sides for comparison)
                    # IMPORTANT: Only match placeholders that START with the label (not composite ones)
                    matching_placeholders = []
                    is_label_field = ':' in placeholder_text
                    
                    if is_label_field:
                        # Label field: check for composite placeholders
                        search_label = placeholder_text.split(':')[0].strip().lower()
                        
                        for p in self.placeholders:
                            normalized_p = normalize_for_matching(p.text)
                            # Match if normalized labels are equal
                            if normalized_p == normalized_search:
                                # Check that the placeholder text starts with the label (after whitespace)
                                # AND doesn't contain another label after it (to exclude composite placeholders)
                                p_text_stripped = p.text.strip()
                                if p_text_stripped.lower().startswith(search_label + ':'):
                                    # Check if there's another label after this one (composite placeholder)
                                    # Look for patterns like "Label1:\nLabel2:" or "Label1: Label2:"
                                    after_first_label = p_text_stripped[len(search_label) + 1:].strip()
                                    # If there's content after the colon, check if it contains another label pattern
                                    # (word followed by colon)
                                    import re
                                    # Check if there's another label pattern (word: or word : or word:\n)
                                    has_another_label = bool(re.search(r'\b\w+\s*:', after_first_label, re.IGNORECASE))
                                    if not has_another_label:
                                        # This is a pure label field, not a composite
                                        matching_placeholders.append(p)
                    else:
                        # Explicit placeholder (like [_____________]): match with bracket variations
                        # But be precise - if placeholder_text has brackets, only match ones with brackets
                        placeholder_has_brackets = (
                            placeholder_text.startswith('[') and placeholder_text.endswith(']') or
                            placeholder_text.startswith('{') and placeholder_text.endswith('}') or
                            placeholder_text.startswith('(') and placeholder_text.endswith(')')
                        )
                        
                        for p in self.placeholders:
                            p_has_brackets = (
                                p.text.startswith('[') and p.text.endswith(']') or
                                p.text.startswith('{') and p.text.endswith('}') or
                                p.text.startswith('(') and p.text.endswith(')')
                            )
                            
                            # Match if both have brackets or both don't have brackets
                            if placeholder_has_brackets == p_has_brackets:
                                # For explicit placeholders, match exactly (normalize whitespace)
                                p_normalized = normalize_for_matching(p.text)
                                placeholder_normalized = normalize_for_matching(placeholder_text)
                                
                                # Match if normalized text is equal
                                if p_normalized == placeholder_normalized:
                                    matching_placeholders.append(p)
                                # Also match if brackets are the same but content matches
                                elif placeholder_has_brackets and p_has_brackets:
                                    # Both have brackets, check if content matches
                                    p_content = p.text.strip('[]{}()').strip()
                                    placeholder_content = placeholder_text.strip('[]{}()').strip()
                                    if p_content.lower() == placeholder_content.lower():
                                        matching_placeholders.append(p)
                    
                    if not matching_placeholders:
                        for _, _, key in field_entries:
                            print(f"  ✗ Failed: {key} (placeholder '{placeholder_text}' not found)")
                        continue
                    
                    # For each field entry, find the best matching occurrence
                    matched_indices = []  # Track which indices we've matched
                    replacements_to_do = []  # Collect all replacements to do
                    
                    for field_name, value, key in field_entries:
                        # Extract keywords from field_name
                        field_keywords = field_name.replace('_', ' ').lower().split()
                        
                        # Common field name to label mappings
                        field_label_mappings = {
                            'purchase_amount': ['purchase amount', 'the purchase amount'],
                            'post_money_valuation_cap': ['post-money valuation cap', 'post money valuation cap', 'valuation cap'],
                            'pre_money_valuation_cap': ['pre-money valuation cap', 'pre money valuation cap'],
                            'discount_rate': ['discount rate', 'discount'],
                            'conversion_price': ['conversion price', 'safe price'],
                        }
                        
                        # Get potential labels for this field
                        potential_labels = field_label_mappings.get(field_name, [])
                        potential_labels.append(field_name.replace('_', ' '))  # Add field_name itself
                        
                        # Find the best matching occurrence by checking context
                        best_match_idx = None
                        best_score = 0
                        
                        for idx, ph in enumerate(matching_placeholders):
                            # Skip if this index was already matched
                            if idx in matched_indices:
                                continue
                            
                            # Extract context around this occurrence (100 chars before and after)
                            context_start = max(0, ph.position - 100)
                            context_end = min(len(self.full_text), ph.end_position + 100)
                            context = self.full_text[context_start:context_end].lower()
                            
                            score = 0
                            
                            # High score if any potential label appears in context
                            for label in potential_labels:
                                if label.lower() in context:
                                    score += 20  # Strong match
                            
                            # Medium score for individual keywords
                            score += sum(2 for keyword in field_keywords if keyword in context)
                            
                            if score > best_score:
                                best_score = score
                                best_match_idx = idx
                        
                        if best_match_idx is not None:
                            matched_indices.append(best_match_idx)
                            # Get the actual placeholder text from the detected placeholder
                            # IMPORTANT: Use the actual text as-is, don't normalize whitespace
                            # The replacement function will extract the pattern from the document
                            actual_placeholder_text = matching_placeholders[best_match_idx].text
                            
                            # For label fields, we need to extract just the base label name
                            # but preserve it for matching - the handler will find the actual pattern
                            if ':' in actual_placeholder_text:
                                # Extract base label name (for context matching)
                                base_label = actual_placeholder_text.split(':')[0].strip()
                                # Use base label + colon - the handler will match this flexibly
                                replacement_pattern = base_label + ':'
                            else:
                                replacement_pattern = actual_placeholder_text
                            
                            # Store replacement info: (original_index, replacement_pattern, value, key, actual_text)
                            # Include actual_text so handler can use it if needed
                            replacements_to_do.append((best_match_idx, replacement_pattern, value, key, actual_placeholder_text))
                        else:
                            print(f"  ✗ Failed: {key} (could not match field_name '{field_name}' to any occurrence)")
                    
                    # Now replace all matches in reverse order (last occurrence first)
                    # Sort by original index descending
                    replacements_to_do.sort(key=lambda x: x[0], reverse=True)
                    
                    replacements_done = 0
                    for original_idx, replacement_pattern, value, key, actual_text in replacements_to_do:
                        # Calculate reverse index correctly
                        # We're processing in reverse order (last occurrence first)
                        # After each replacement, the handler re-searches and finds fewer occurrences
                        # So we always want the LAST remaining occurrence = index (remaining_count - 1)
                        remaining_count = len(matching_placeholders) - replacements_done
                        reverse_idx = remaining_count - 1
                        
                        # Safety check: ensure reverse_idx is valid
                        if reverse_idx < 0:
                            print(f"  ✗ Failed: {key} (invalid reverse_idx: {reverse_idx}, remaining_count: {remaining_count}, replacements_done: {replacements_done})")
                            continue
                        
                        # Use the base label pattern for replacement (pattern matching handles whitespace)
                        # The handler will extract the actual pattern from the document
                        success = self.doc_handler.replace_placeholder_at_position(replacement_pattern, value, reverse_idx)
                        if success:
                            total_replacements += 1
                            replacements_done += 1
                            print(f"  ✓ Replaced: {key:40} → {value[:25]} (matched occurrence {original_idx + 1}/{len(matching_placeholders)}, reverse_idx={reverse_idx})")
                        else:
                            # Fallback: try with normalized text
                            success = self.doc_handler.replace_placeholder_at_position(placeholder_text, value, reverse_idx)
                            if success:
                                total_replacements += 1
                                replacements_done += 1
                                print(f"  ✓ Replaced: {key:40} → {value[:25]} (matched occurrence {original_idx + 1}/{len(matching_placeholders)}, fallback, reverse_idx={reverse_idx})")
                            else:
                                print(f"  ✗ Failed: {key} (replacement failed - tried '{replacement_pattern}' and '{placeholder_text}', reverse_idx={reverse_idx}, remaining_count={remaining_count})")
                
                print()
            
            # Priority 3: Plain placeholder text replacements
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

