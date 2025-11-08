"""
Document Handler for backend2
Handles loading, modifying, and saving Word documents using python-docx
"""

import os
import re
from docx import Document
from typing import Dict, List, Tuple, Optional


class DocumentHandler:
    def __init__(self, doc_path: str):
        """Initialize document handler with path to .docx file"""
        self.doc_path = doc_path
        self.doc = None
        self.full_text = ""
        
    def load_document(self) -> bool:
        """Load the .docx document"""
        try:
            self.doc = Document(self.doc_path)
            self._extract_text_structure()
            return True
        except Exception as e:
            print(f"Error loading document: {e}")
            return False
    
    def _extract_text_structure(self):
        """Extract text while preserving structure"""
        self.full_text = ""
        
        # Extract from regular paragraphs
        for para in self.doc.paragraphs:
            para_text = para.text
            self.full_text += para_text + "\n"
        
        # Extract from table cells
        for table in self.doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text
                    if cell_text.strip():
                        self.full_text += cell_text + "\n"
    
    def get_full_text(self) -> str:
        """Return extracted full text"""
        return self.full_text
    
    def replace_placeholder(self, placeholder: str, value: str) -> bool:
        """
        Replace placeholder with value.
        
        Logic:
        - Explicit placeholder ([text], {text}, (text)): Replace ENTIRE placeholder with value
        - Blank field (ends with : or space): Work with document runs to find and replace underscore/space runs
        
        Args:
            placeholder: The placeholder text to find
            value: The replacement value
        
        Returns:
            True if replacement was successful
        """
        try:
            replaced_count = 0
            
            # Determine type: explicit placeholder or blank field
            is_explicit_placeholder = (
                (placeholder.startswith('[') and placeholder.endswith(']')) or
                (placeholder.startswith('{') and placeholder.endswith('}')) or
                (placeholder.startswith('(') and placeholder.endswith(')')) or
                (placeholder.startswith('<') and placeholder.endswith('>')) or
                (placeholder.startswith('_') and placeholder.count('_') >= 2 and not ':' in placeholder)
            )
            
            # Check if this is a blank field - be more lenient
            # Blank fields might be detected as just the label name (e.g., "Date", "No.")
            # or with colon (e.g., "Date:", "Date: ")
            # Also check if placeholder name suggests it's a blank field (common field names)
            common_blank_field_names = ['date', 'no', 'sum', 'amount', 'paid', 'check']
            placeholder_lower = placeholder.strip().lower().rstrip('.:')
            is_blank_field = (
                placeholder.endswith(': ') or 
                placeholder.endswith(':') or
                placeholder.endswith(':\t') or
                (':' in placeholder and placeholder.strip().endswith(':')) or
                # Check if it matches common blank field patterns
                any(name in placeholder_lower for name in common_blank_field_names if len(placeholder_lower) < 30)
            )
            
            # Extract label base for blank fields
            if is_blank_field:
                if ':' in placeholder:
                    base_label = placeholder.split(':')[0].strip()
                else:
                    # Placeholder is just the label name (e.g., "Date", "No.")
                    base_label = placeholder.strip()
            else:
                base_label = None
            
            # Debug: Print what we're looking for
            if is_blank_field:
                print(f"  [DEBUG] Blank field: placeholder='{placeholder}', base_label='{base_label}'")
            
            # Replace in paragraphs
            for para in self.doc.paragraphs:
                full_para_text = ''.join([run.text for run in para.runs])
                
                if is_explicit_placeholder:
                    # Replace entire placeholder
                    if placeholder in full_para_text:
                        new_text = full_para_text.replace(placeholder, value, 1)
                        if new_text != full_para_text:
                            # Clear and rewrite paragraph
                            for run in para.runs:
                                r = run._element
                                r.getparent().remove(r)
                            para.add_run(new_text)
                            replaced_count += 1
                            continue
                
                elif is_blank_field and base_label:
                    # Blank field: work with runs directly
                    # Find runs that contain the label, then look for underscore/space runs after it
                    if self._replace_blank_field_in_runs(para, base_label, value):
                        replaced_count += 1
            
            # Replace in table cells
            for table in self.doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            if is_explicit_placeholder:
                                full_para_text = ''.join([run.text for run in para.runs])
                                if placeholder in full_para_text:
                                    new_text = full_para_text.replace(placeholder, value, 1)
                                    if new_text != full_para_text:
                                        for run in para.runs:
                                            r = run._element
                                            r.getparent().remove(r)
                                        para.add_run(new_text)
                                        replaced_count += 1
                                        continue
                            
                            elif is_blank_field and base_label:
                                if self._replace_blank_field_in_runs(para, base_label, value):
                                    replaced_count += 1
            
            return replaced_count > 0
        except Exception as e:
            print(f"Error replacing placeholder: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _replace_blank_field_in_runs(self, para, label: str, value: str) -> bool:
        """
        Replace blank field by working with runs directly.
        Finds the label run, then finds and replaces underscore/space runs after it.
        
        Args:
            para: The paragraph to search
            label: The label text (e.g., "Date", "No", "The Sum of")
            value: The value to insert
        
        Returns:
            True if replacement was successful
        """
        try:
            runs = list(para.runs)
            if not runs:
                return False
            
            # Build full text from runs to find label position
            full_text = ''.join([run.text for run in runs])
            
            # Try different label patterns - be more flexible
            # Handle cases where placeholder might be "Date", "Date:", "Date: ", "No.", "No.:", etc.
            label_patterns = [
                f"{label}:",           # "Date:"
                f"{label}: ",          # "Date: "
                f"{label} ",           # "Date "
                f"{label}",            # "Date" (standalone - might be in same run as underscores)
            ]
            
            # Special handling for labels with periods (e.g., "No.")
            if '.' in label:
                # If label is "No.", also try "No.:" and "No.: "
                label_without_period = label.rstrip('.')
                label_patterns.extend([
                    f"{label_without_period}.:",      # "No.:"
                    f"{label_without_period}.: ",     # "No.: "
                ])
            
            # Debug: Print what patterns we're trying
            print(f"    [DEBUG] Trying patterns: {label_patterns[:4]}...")
            
            for label_pattern in label_patterns:
                if label_pattern not in full_text:
                    continue
                
                print(f"    [DEBUG] Found pattern '{label_pattern}' in paragraph text: '{full_text[:100]}...'")
                
                # Find which run(s) contain the label
                current_pos = 0
                label_start_run_idx = None
                label_end_pos = None
                
                for i, run in enumerate(runs):
                    run_text = run.text
                    run_start = current_pos
                    run_end = current_pos + len(run_text)
                    
                    # Check if label starts in this run
                    if label_pattern in full_text[current_pos:]:
                        label_pos_in_full = full_text.find(label_pattern, current_pos)
                        if run_start <= label_pos_in_full < run_end:
                            label_start_run_idx = i
                            label_end_pos = label_pos_in_full + len(label_pattern)
                            break
                    
                    current_pos = run_end
                
                if label_start_run_idx is None:
                    continue
                
                # Now find underscore/space runs after the label
                # Look at runs starting from label_start_run_idx
                underscore_run_indices = []
                current_pos = label_end_pos
                
                # Check remaining runs for underscores or spaces
                # Also check the label run itself - it might contain underscores after the label
                runs_to_check = list(range(label_start_run_idx, len(runs)))
                
                for i in runs_to_check:
                    run = runs[i]
                    run_text = run.text
                    
                    # If this is the label run, check only the part after the label
                    if i == label_start_run_idx:
                        # Get text after the label pattern
                        label_end_in_run = run_text.find(label_pattern) + len(label_pattern)
                        if label_end_in_run < len(run_text):
                            remaining_text = run_text[label_end_in_run:]
                            # Check if remaining text in this run is underscores/spaces
                            if remaining_text.strip('_ \t') == '' and len(remaining_text.strip()) > 0:
                                # This run has underscores after the label - mark it for processing
                                underscore_run_indices.append(i)
                    else:
                        # Check if this run contains mostly underscores, spaces, or tabs
                        stripped = run_text.strip()
                        if not stripped:
                            # Empty or whitespace-only run
                            underscore_run_indices.append(i)
                        elif stripped.strip('_') == '':
                            # Contains only underscores (possibly with spaces)
                            underscore_run_indices.append(i)
                        elif '_' in run_text and len(stripped.strip('_ \t')) == 0:
                            # Mix of underscores and spaces/tabs
                            underscore_run_indices.append(i)
                        else:
                            # Found non-blank content, stop looking
                            break
                
                # If we found underscore runs, replace them
                if underscore_run_indices:
                    # First, handle the label run if it contains underscores
                    label_run = runs[label_start_run_idx]
                    label_run_text = label_run.text
                    
                    # Check if label run is in underscore_run_indices (has underscores after label)
                    if label_start_run_idx in underscore_run_indices:
                        # Remove underscores from label run, keep only the label part
                        label_end_in_run = label_run_text.find(label_pattern) + len(label_pattern)
                        label_run.text = label_run_text[:label_end_in_run]
                        # Remove from indices since we've already handled it
                        underscore_run_indices.remove(label_start_run_idx)
                    
                    # Remove other underscore runs
                    for idx in reversed(underscore_run_indices):
                        run = runs[idx]
                        r = run._element
                        r.getparent().remove(r)
                    
                    # Insert value after the label run
                    label_run = runs[label_start_run_idx]
                    label_run_text = label_run.text
                    
                    # Check if label run ends with ": " or just ":"
                    if label_run_text.rstrip().endswith(':'):
                        # Add value after colon
                        new_label_text = label_run_text.rstrip() + ' ' + value
                    else:
                        # Label already has space, just append value
                        new_label_text = label_run_text.rstrip() + value
                    
                    # Replace label run text
                    label_run.text = new_label_text
                    return True
                
                # No underscore runs found - insert value after label
                # This handles cases where "Date: " is detected but no underscores follow
                label_run = runs[label_start_run_idx]
                label_run_text = label_run.text
                
                # Find where label ends in the run
                if label_pattern in label_run_text:
                    # Label is in this run, append value
                    if label_run_text.rstrip().endswith(':'):
                        label_run.text = label_run_text.rstrip() + ' ' + value
                    else:
                        label_run.text = label_run_text.rstrip() + value
                    return True
            
            return False
        except Exception as e:
            print(f"Error in _replace_blank_field_in_runs: {e}")
            return False
    
    def replace_placeholder_at_position(self, placeholder: str, value: str, position_index: int = 0) -> bool:
        """
        Replace a specific occurrence (by position) of a placeholder.
        
        Args:
            placeholder: The placeholder text to find
            value: The replacement value  
            position_index: Which occurrence (0=first, 1=second, etc.)
        
        Returns:
            True if replacement was successful
        """
        try:
            # Determine type
            is_explicit_placeholder = (
                (placeholder.startswith('[') and placeholder.endswith(']')) or
                (placeholder.startswith('{') and placeholder.endswith('}')) or
                (placeholder.startswith('(') and placeholder.endswith(')')) or
                (placeholder.startswith('<') and placeholder.endswith('>')) or
                (placeholder.startswith('_') and placeholder.count('_') >= 2 and not ':' in placeholder)
            )
            is_blank_field = (
                placeholder.endswith(': ') or 
                placeholder.endswith(':') or
                placeholder.endswith(':\t') or
                (':' in placeholder and ('_' in placeholder or placeholder.strip().endswith(':')))
            )
            
            # Extract label base for blank fields
            if is_blank_field:
                if ':' in placeholder:
                    base_label = placeholder.split(':')[0].strip()
                else:
                    base_label = placeholder.rstrip('_ \t')
            else:
                base_label = None
            
            # Collect all occurrences
            occurrences = []
            
            for para in self.doc.paragraphs:
                full_text = ''.join([run.text for run in para.runs])
                
                if is_explicit_placeholder:
                    if placeholder in full_text:
                        occurrences.append((para, 'paragraph'))
                elif is_blank_field and base_label:
                    # Check if this paragraph has the label
                    label_patterns = [f"{base_label}:", f"{base_label}: ", f"{base_label} "]
                    if any(pattern in full_text for pattern in label_patterns):
                        occurrences.append((para, 'paragraph'))
            
            for table in self.doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            full_text = ''.join([run.text for run in para.runs])
                            
                            if is_explicit_placeholder:
                                if placeholder in full_text:
                                    occurrences.append((para, 'table'))
                            elif is_blank_field and base_label:
                                label_patterns = [f"{base_label}:", f"{base_label}: ", f"{base_label} "]
                                if any(pattern in full_text for pattern in label_patterns):
                                    occurrences.append((para, 'table'))
            
            # Get target occurrence
            if position_index >= len(occurrences):
                return False
            
            target_para, para_type = occurrences[position_index]
            
            # Replace
            if is_explicit_placeholder:
                full_para_text = ''.join([run.text for run in target_para.runs])
                if placeholder in full_para_text:
                    new_text = full_para_text.replace(placeholder, value, 1)
                    # Write back
                    for run in target_para.runs:
                        r = run._element
                        r.getparent().remove(r)
                    target_para.add_run(new_text)
                    return True
            elif is_blank_field and base_label:
                # Use run-based replacement
                return self._replace_blank_field_in_runs(target_para, base_label, value)
            
            return False
        except Exception as e:
            print(f"Error replacing placeholder at position: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def replace_multiple_placeholders(self, replacements: Dict[str, str]) -> Dict[str, bool]:
        """
        Replace multiple placeholders at once
        
        Args:
            replacements: Dictionary mapping placeholder -> value
        
        Returns:
            Dictionary mapping placeholder -> success status
        """
        results = {}
        for placeholder, value in replacements.items():
            results[placeholder] = self.replace_placeholder(placeholder, value)
        return results
    
    def save_document(self, output_path: str) -> bool:
        """Save the modified document to a new file"""
        try:
            self.doc.save(output_path)
            return True
        except Exception as e:
            print(f"Error saving document: {e}")
            return False



