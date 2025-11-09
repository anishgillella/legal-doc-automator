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
    
    def _replace_text_preserving_format(self, para, new_text: str, label_start_pos: Optional[int] = None):
        """
        Replace text in paragraph while preserving formatting.
        If label_start_pos is provided, preserve formatting from that position.
        
        Args:
            para: The paragraph to modify
            new_text: The new text to replace with
            label_start_pos: Optional position where label starts (to preserve its formatting)
        """
        # Build character-to-run mapping to preserve formatting BEFORE clearing runs
        char_to_run = []
        char_pos = 0
        runs_list = list(para.runs)  # Copy list before clearing
        for run in runs_list:
            run_text = run.text
            for i in range(len(run_text)):
                char_to_run.append((char_pos + i, run))
            char_pos += len(run_text)
        
        # Determine which run to use as formatting template
        template_run = None
        if label_start_pos is not None and label_start_pos < len(char_to_run):
            # Use formatting from the label position
            template_run = char_to_run[label_start_pos][1]
        elif char_to_run:
            # Use formatting from the first character
            template_run = char_to_run[0][1]
        
        # Clear all runs
        for run in para.runs:
            r = run._element
            r.getparent().remove(r)
        
        # Add new text with preserved formatting
        if template_run:
            # Copy formatting from template run
            new_run = para.add_run(new_text)
            # Copy formatting properties
            if template_run.bold is not None:
                new_run.bold = template_run.bold
            if template_run.italic is not None:
                new_run.italic = template_run.italic
            if template_run.underline is not None:
                new_run.underline = template_run.underline
            if template_run.font.name:
                new_run.font.name = template_run.font.name
            if template_run.font.size:
                new_run.font.size = template_run.font.size
            if template_run.font.color.rgb:
                new_run.font.color.rgb = template_run.font.color.rgb
        else:
            # No template, just add plain text
            para.add_run(new_text)
    
    def replace_placeholder(self, placeholder: str, value: str) -> bool:
        """
        Replace placeholder with value.
        
        Logic:
        - Explicit placeholder ([text], {text}, (text)): Replace ENTIRE placeholder with value
        - Label field (text like "Date", "No.", "The Sum of"): Keep label, add space, then insert value
        
        Args:
            placeholder: The placeholder text to find
            value: The replacement value
        
        Returns:
            True if replacement was successful
        """
        try:
            replaced_count = 0
            
            # Determine type: explicit placeholder or label field
            is_explicit_placeholder = (
                (placeholder.startswith('[') and placeholder.endswith(']')) or
                (placeholder.startswith('{') and placeholder.endswith('}')) or
                (placeholder.startswith('(') and placeholder.endswith(')')) or
                (placeholder.startswith('<') and placeholder.endswith('>')) or
                '_' in placeholder  # Underscores are explicit
            )
            
            is_label_field = not is_explicit_placeholder  # Any non-bracketed placeholder is a label field
            
            # Build list of patterns to try (handle whitespace variations)
            patterns_to_try = [placeholder]
            if is_label_field:
                # For label fields, try variations with/without colon, spaces, etc.
                base = placeholder.rstrip(': \t')  # Get the label without trailing space/colon
                patterns_to_try.extend([
                    base + ':\t',    # Tab variant
                    base + ':  ',    # Double space variant
                    base + ': ',     # Space variant
                    base + ':',     # Just colon
                    base,           # Just the label name (for cases like "Date2023-10-01" or "The Sum of1200.00")
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
                            # Label field: keep label, add space, then insert value
                            label_pos = full_para_text.find(pattern)
                            if label_pos != -1:
                                label_end = label_pos + len(pattern)
                                remaining_text = full_para_text[label_end:]
                                
                                # Strip trailing spaces from pattern to get actual label end
                                label_without_trailing_space = pattern.rstrip(' \t')
                                actual_label_end = label_pos + len(label_without_trailing_space)
                                remaining_after_label = full_para_text[actual_label_end:]
                                
                                # Check what comes after the label
                                if remaining_text and not remaining_text[0].isspace():
                                    # There's text immediately after label (no space), replace it
                                    # Find where the existing value ends (look for space, newline, or end)
                                    match = re.match(r'^([^\s\n]+)', remaining_text)
                                    if match:
                                        # Replace the existing value
                                        existing_value_end = match.end()
                                        new_text = full_para_text[:label_end] + ' ' + value + remaining_text[existing_value_end:]
                                    else:
                                        # No clear existing value, just append
                                        new_text = full_para_text[:label_end] + ' ' + value
                                else:
                                    # There's whitespace/blank lines after label - REPLACE them with value
                                    # For label fields, we want: label + ' ' + value (all on same line)
                                    # Replace ALL whitespace/newlines after label with just space + value
                                    match = re.match(r'^[\s\n\t]+', remaining_after_label)
                                    if match:
                                        # Replace the blank content
                                        after_whitespace = remaining_after_label[match.end():]
                                        if after_whitespace.strip():
                                            # There's content after whitespace, keep it
                                            new_text = full_para_text[:actual_label_end] + ' ' + value + ' ' + after_whitespace
                                        else:
                                            # No content after whitespace, just replace with label + space + value
                                            new_text = full_para_text[:actual_label_end] + ' ' + value
                                    else:
                                        # No blank content, just append value with space
                                        new_text = full_para_text[:actual_label_end] + ' ' + value
                            else:
                                continue
                        
                        if new_text != full_para_text:
                            # Preserve formatting by modifying runs in place
                            self._replace_text_preserving_format(para, new_text, label_pos if not is_explicit_placeholder else None)
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
                                        # Replace only the FIRST occurrence (same placeholder might mean different things)
                                        new_text = full_para_text.replace(pattern, value, 1)
                                    else:
                                        # Label field: keep label, add space, then insert value
                                        label_pos = full_para_text.find(pattern)
                                        if label_pos != -1:
                                            label_end = label_pos + len(pattern)
                                            remaining_text = full_para_text[label_end:]
                                            
                                            # Strip trailing spaces from pattern to get actual label end
                                            label_without_trailing_space = pattern.rstrip(' \t')
                                            actual_label_end = label_pos + len(label_without_trailing_space)
                                            remaining_after_label = full_para_text[actual_label_end:]
                                            
                                            # Check what comes after the label
                                            if remaining_text and not remaining_text[0].isspace():
                                                # There's text immediately after label, replace it
                                                match = re.match(r'^([^\s\n]+)', remaining_text)
                                                if match:
                                                    existing_value_end = match.end()
                                                    new_text = full_para_text[:label_end] + ' ' + value + remaining_text[existing_value_end:]
                                                else:
                                                    new_text = full_para_text[:label_end] + ' ' + value
                                            else:
                                                # There's whitespace/blank lines after label - REPLACE them with value
                                                match = re.match(r'^[\s\n\t]+', remaining_after_label)
                                                if match:
                                                    after_whitespace = remaining_after_label[match.end():]
                                                    if after_whitespace.strip():
                                                        new_text = full_para_text[:actual_label_end] + ' ' + value + ' ' + after_whitespace
                                                    else:
                                                        new_text = full_para_text[:actual_label_end] + ' ' + value
                                                else:
                                                    new_text = full_para_text[:actual_label_end] + ' ' + value
                                        else:
                                            continue
                                    
                                    if new_text != full_para_text:
                                        # Preserve formatting by modifying runs in place
                                        self._replace_text_preserving_format(para, new_text, label_pos if not is_explicit_placeholder else None)
                                        replaced_count += 1
                                        break  # Move to next paragraph
            
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
            is_label_field = not is_explicit_placeholder
            
            # Build patterns
            patterns_to_try = [placeholder]
            if is_label_field:
                base = placeholder.rstrip(': \t')
                patterns_to_try.extend([
                    base + ':\t',
                    base + ':  ',
                    base + ': ',
                    base + ':',
                    base,           # Just the label name
                ])
            
            # Collect all occurrences
            occurrences = []
            
            for para in self.doc.paragraphs:
                full_text = ''.join([run.text for run in para.runs])
                for pattern in patterns_to_try:
                    if pattern in full_text:
                        occurrences.append((para, pattern))
                        break
            
            for table in self.doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            full_text = ''.join([run.text for run in para.runs])
                            for pattern in patterns_to_try:
                                if pattern in full_text:
                                    occurrences.append((para, pattern))
                                    break
            
            # Get target occurrence
            if position_index >= len(occurrences):
                return False
            
            target_para, matching_pattern = occurrences[position_index]
            full_para_text = ''.join([run.text for run in target_para.runs])
            
            # Replace
            if is_explicit_placeholder:
                new_text = full_para_text.replace(matching_pattern, value, 1)
            else:
                # Label field: keep label, add space, then insert value
                label_pos = full_para_text.find(matching_pattern)
                if label_pos != -1:
                    label_end = label_pos + len(matching_pattern)
                    remaining_text = full_para_text[label_end:]
                    
                    # Strip trailing spaces from pattern to get actual label end
                    label_without_trailing_space = matching_pattern.rstrip(' \t')
                    actual_label_end = label_pos + len(label_without_trailing_space)
                    remaining_after_label = full_para_text[actual_label_end:]
                    
                    # Check what comes after the label
                    if remaining_text and not remaining_text[0].isspace():
                        # There's text immediately after label, replace it
                        match = re.match(r'^([^\s\n]+)', remaining_text)
                        if match:
                            existing_value_end = match.end()
                            new_text = full_para_text[:label_end] + ' ' + value + remaining_text[existing_value_end:]
                        else:
                            new_text = full_para_text[:label_end] + ' ' + value
                    else:
                        # There's whitespace/blank lines after label - REPLACE them with value
                        match = re.match(r'^[\s\n\t]+', remaining_after_label)
                        if match:
                            after_whitespace = remaining_after_label[match.end():]
                            if after_whitespace.strip():
                                new_text = full_para_text[:actual_label_end] + ' ' + value + ' ' + after_whitespace
                            else:
                                new_text = full_para_text[:actual_label_end] + ' ' + value
                        else:
                            new_text = full_para_text[:actual_label_end] + ' ' + value
                else:
                    return False
            
            # Write back with formatting preservation
            self._replace_text_preserving_format(target_para, new_text, label_pos if not is_explicit_placeholder else None)
            return True
        except Exception as e:
            print(f"Error replacing placeholder at position: {e}")
            return False
    
    def save_document(self, output_path: str) -> bool:
        """Save the modified document to a new file"""
        try:
            self.doc.save(output_path)
            return True
        except Exception as e:
            print(f"Error saving document: {e}")
            return False

