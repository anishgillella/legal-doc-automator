"""
Document Handler for backend2
Handles loading, modifying, and saving Word documents using python-docx
"""

import os
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
        - Blank field (ends with : or space): Replace only the blank part, keep label
        
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
                '_' in placeholder  # Underscores are explicit
            )
            
            is_blank_field = (
                placeholder.endswith(': ') or 
                placeholder.endswith(':') or
                placeholder.endswith(':\t')
            )
            
            # Build list of patterns to try (handle whitespace variations)
            patterns_to_try = [placeholder]
            if is_blank_field:
                base = placeholder.rstrip(': \t')  # Get the label without trailing space/colon
                patterns_to_try.extend([
                    base + ':\t',    # Tab variant
                    base + ':  ',    # Double space variant
                    base + ': ',     # Space variant
                    base + ': _____', # Underscores variant
                    base + ':',     # Just colon
                ])
            
            # Replace in paragraphs
            for para in self.doc.paragraphs:
                full_para_text = ''.join([run.text for run in para.runs])
                
                for pattern in patterns_to_try:
                    if pattern in full_para_text:
                        if is_explicit_placeholder:
                            # Replace entire placeholder
                            new_text = full_para_text.replace(pattern, value, 1)
                        else:
                            # Blank field: keep label, replace blank part
                            label_pos = full_para_text.find(pattern)
                            if label_pos != -1:
                                # Keep everything up to and including the label, then add value
                                new_text = full_para_text[:label_pos + len(pattern)] + value
                            else:
                                continue
                        
                        if new_text != full_para_text:
                            # Clear and rewrite paragraph
                            for run in para.runs:
                                r = run._element
                                r.getparent().remove(r)
                            
                            para.add_run(new_text)
                            replaced_count += 1
                            break  # Move to next paragraph
            
            # Replace in table cells
            for table in self.doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            full_para_text = ''.join([run.text for run in para.runs])
                            
                            for pattern in patterns_to_try:
                                if pattern in full_para_text:
                                    if is_explicit_placeholder:
                                        new_text = full_para_text.replace(pattern, value, 1)
                                    else:
                                        label_pos = full_para_text.find(pattern)
                                        if label_pos != -1:
                                            new_text = full_para_text[:label_pos + len(pattern)] + value
                                        else:
                                            continue
                                    
                                    if new_text != full_para_text:
                                        for run in para.runs:
                                            r = run._element
                                            r.getparent().remove(r)
                                        
                                        para.add_run(new_text)
                                        replaced_count += 1
                                        break
            
            return replaced_count > 0
        except Exception as e:
            print(f"Error replacing placeholder: {e}")
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
                '_' in placeholder
            )
            is_blank_field = placeholder.endswith(': ') or placeholder.endswith(':')
            
            # Build patterns
            patterns_to_try = [placeholder]
            if is_blank_field:
                base = placeholder.rstrip(': \t')
                patterns_to_try.extend([
                    base + ':\t',
                    base + ':  ',
                    base + ': ',
                    base + ': _____',
                    base + ':',
                ])
            
            # Collect all occurrences
            occurrences = []
            
            for para in self.doc.paragraphs:
                full_text = ''.join([run.text for run in para.runs])
                for pattern in patterns_to_try:
                    if pattern in full_text:
                        occurrences.append((para, pattern, 'paragraph'))
                        break
            
            for table in self.doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            full_text = ''.join([run.text for run in para.runs])
                            for pattern in patterns_to_try:
                                if pattern in full_text:
                                    occurrences.append((para, pattern, 'table'))
                                    break
            
            # Get target occurrence
            if position_index >= len(occurrences):
                return False
            
            target_para, matching_pattern, para_type = occurrences[position_index]
            full_para_text = ''.join([run.text for run in target_para.runs])
            
            # Replace
            if is_explicit_placeholder:
                new_text = full_para_text.replace(matching_pattern, value, 1)
            else:
                label_pos = full_para_text.find(matching_pattern)
                if label_pos != -1:
                    new_text = full_para_text[:label_pos + len(matching_pattern)] + value
                else:
                    return False
            
            # Write back
            for run in target_para.runs:
                r = run._element
                r.getparent().remove(r)
            
            target_para.add_run(new_text)
            return True
        except Exception as e:
            print(f"Error replacing placeholder at position: {e}")
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

