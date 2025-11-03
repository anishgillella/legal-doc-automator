import os
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from typing import Dict, List, Tuple, Optional


class DocumentHandler:
    def __init__(self, doc_path: str):
        """Initialize document handler with path to .docx file"""
        self.doc_path = doc_path
        self.doc = None
        self.full_text = ""
        self.paragraphs_data = []
        
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
        """Extract text while preserving paragraph structure and formatting info"""
        self.full_text = ""
        self.paragraphs_data = []
        
        # Extract from regular paragraphs
        for para_idx, para in enumerate(self.doc.paragraphs):
            para_text = para.text
            self.full_text += para_text + "\n"
            
            # Store paragraph metadata
            self.paragraphs_data.append({
                'index': para_idx,
                'text': para_text,
                'alignment': para.alignment,
                'style': para.style.name if para.style else 'Normal',
                'runs': [(run.text, {
                    'bold': run.bold,
                    'italic': run.italic,
                    'font_name': run.font.name,
                    'font_size': run.font.size,
                }) for run in para.runs]
            })
        
        # Extract from table cells
        for table_idx, table in enumerate(self.doc.tables):
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    cell_text = cell.text
                    if cell_text.strip():
                        self.full_text += cell_text + "\n"
                        
                        # Store cell metadata (similar to paragraph)
                        self.paragraphs_data.append({
                            'index': f"table_{table_idx}_row_{row_idx}_cell_{cell_idx}",
                            'text': cell_text,
                            'alignment': None,
                            'style': 'Table Cell',
                            'runs': []
                        })
    
    def get_full_text(self) -> str:
        """Return extracted full text"""
        return self.full_text
    
    def get_paragraph_count(self) -> int:
        """Return number of paragraphs"""
        return len(self.doc.paragraphs)
    
    def replace_placeholder(self, placeholder: str, value: str) -> bool:
        """
        Replace a placeholder with actual value while preserving formatting.
        Works with whitespace variations (tabs, spaces, etc).
        
        Args:
            placeholder: The placeholder text to find (e.g., "[founder_name]", "Email: ")
            value: The replacement value
        
        Returns:
            True if at least one replacement was successful
        """
        try:
            replaced_count = 0
            
            # Normalize placeholder for matching: convert tabs/multiple spaces to flexible pattern
            # For blank fields ending with ": ", also match ":  " with tabs
            search_patterns = [placeholder]
            if placeholder.endswith(': '):
                # For "Email: ", also try to match "Email:\t", "Email:  ", etc.
                base = placeholder[:-2]  # Remove the ": "
                search_patterns.extend([
                    base + ':\t',  # Tab
                    base + ':  ',  # Two spaces
                    base + ': ',   # Already have this
                ])
            
            # Replace in regular paragraphs
            for para in self.doc.paragraphs:
                full_para_text = ''.join([run.text for run in para.runs])
                replaced_this_para = False
                
                for search_pattern in search_patterns:
                    if search_pattern in full_para_text and not replaced_this_para:
                        # Detect if this is a blank field placeholder
                        is_blank_field = (
                            (': ' in search_pattern and search_pattern.endswith(': ')) or
                            (': ' in search_pattern and search_pattern.endswith(':\t')) or
                            search_pattern.endswith(':')
                        )
                        
                        # For blank fields, only add value after the label
                        if is_blank_field:
                            new_text = full_para_text.replace(search_pattern, search_pattern + value, 1)
                        else:
                            # For explicit placeholders, replace the whole placeholder
                            new_text = full_para_text.replace(search_pattern, value, 1)
                        
                        if new_text != full_para_text:  # Verify replacement happened
                            # Get formatting from first run
                            first_run_format = None
                            if para.runs:
                                first_run = para.runs[0]
                                first_run_format = {
                                    'bold': first_run.bold,
                                    'italic': first_run.italic,
                                    'font_name': first_run.font.name,
                                    'font_size': first_run.font.size,
                                    'color': first_run.font.color.rgb if first_run.font.color and first_run.font.color.rgb else None
                                }
                            
                            # Clear all runs
                            for run in para.runs:
                                r = run._element
                                r.getparent().remove(r)
                            
                            # Add new run with replaced text
                            new_run = para.add_run(new_text)
                            
                            # Apply preserved formatting
                            if first_run_format:
                                new_run.bold = first_run_format['bold']
                                new_run.italic = first_run_format['italic']
                                if first_run_format['font_name']:
                                    new_run.font.name = first_run_format['font_name']
                                if first_run_format['font_size']:
                                    new_run.font.size = first_run_format['font_size']
                                if first_run_format['color']:
                                    new_run.font.color.rgb = first_run_format['color']
                            
                            replaced_count += 1
                            replaced_this_para = True
                            break  # Found and replaced, move to next para
            
            # Replace in table cells
            for table in self.doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if placeholder in cell.text:
                            # For cells, replace in each paragraph within the cell
                            for para in cell.paragraphs:
                                if placeholder in para.text:
                                    full_para_text = ''.join([run.text for run in para.runs])
                                    
                                    if placeholder in full_para_text:
                                        # For blank fields, only add value after the label
                                        if is_blank_field:
                                            new_text = full_para_text.replace(placeholder, placeholder + value)
                                        else:
                                            # For explicit placeholders, replace the whole placeholder
                                            new_text = full_para_text.replace(placeholder, value)
                                        
                                        # Get formatting from first run
                                        first_run_format = None
                                        if para.runs:
                                            first_run = para.runs[0]
                                            first_run_format = {
                                                'bold': first_run.bold,
                                                'italic': first_run.italic,
                                                'font_name': first_run.font.name,
                                                'font_size': first_run.font.size,
                                                'color': first_run.font.color.rgb if first_run.font.color and first_run.font.color.rgb else None
                                            }
                                        
                                        # Clear all runs
                                        for run in para.runs:
                                            r = run._element
                                            r.getparent().remove(r)
                                        
                                        # Add new run with replaced text
                                        new_run = para.add_run(new_text)
                                        
                                        # Apply preserved formatting
                                        if first_run_format:
                                            new_run.bold = first_run_format['bold']
                                            new_run.italic = first_run_format['italic']
                                            if first_run_format['font_name']:
                                                new_run.font.name = first_run_format['font_name']
                                            if first_run_format['font_size']:
                                                new_run.font.size = first_run_format['font_size']
                                            if first_run_format['color']:
                                                new_run.font.color.rgb = first_run_format['color']
                                        
                                        replaced_count += 1
            
            # Log result
            if replaced_count == 0:
                pass  # Silently return False for not found - will be logged by caller
            
            return replaced_count > 0
        except Exception as e:
            print(f"Error replacing placeholder: {e}")
            return False
    
    def replace_placeholder_at_position(self, placeholder: str, value: str, position_index: int = 0) -> bool:
        """
        Replace a specific occurrence of a placeholder (useful for duplicates).
        Handles whitespace variations (tabs, spaces, etc).
        
        Args:
            placeholder: The placeholder text to find
            value: The replacement value  
            position_index: Which occurrence to replace (0 = first, 1 = second, etc.)
        
        Returns:
            True if replacement was successful
        """
        try:
            # Build list of possible patterns for this placeholder
            search_patterns = [placeholder]
            if placeholder.endswith(': '):
                base = placeholder[:-2]
                search_patterns.extend([
                    base + ':\t',  # Tab
                    base + ':  ',  # Two spaces
                ])
            
            # First pass: collect all paragraphs/cells with the placeholder
            all_elements = []  
            
            for para in self.doc.paragraphs:
                full_text = ''.join([run.text for run in para.runs])
                # Check if any pattern matches
                matches_any = any(p in full_text for p in search_patterns)
                if matches_any:
                    all_elements.append((para, para, True))
            
            for table in self.doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        full_cell_text = cell.text
                        matches_any = any(p in full_cell_text for p in search_patterns)
                        if matches_any:
                            for para in cell.paragraphs:
                                full_text = ''.join([run.text for run in para.runs])
                                matches_any = any(p in full_text for p in search_patterns)
                                if matches_any:
                                    all_elements.append((para, cell, False))
            
            # Check if position is valid
            if position_index >= len(all_elements):
                return False
            
            # Get target paragraph
            target_para, container, is_para = all_elements[position_index]
            full_para_text = ''.join([run.text for run in target_para.runs])
            
            # Find which pattern matches
            matching_pattern = None
            for pattern in search_patterns:
                if pattern in full_para_text:
                    matching_pattern = pattern
                    break
            
            if not matching_pattern:
                return False
            
            # Detect if this is a blank field
            is_blank_field = (
                matching_pattern.endswith(': ') or
                matching_pattern.endswith(':\t')
            )
            
            # Replace
            if is_blank_field:
                new_text = full_para_text.replace(matching_pattern, matching_pattern + value, 1)
            else:
                new_text = full_para_text.replace(matching_pattern, value, 1)
            
            # Get formatting
            first_run_format = None
            if target_para.runs:
                first_run = target_para.runs[0]
                first_run_format = {
                    'bold': first_run.bold,
                    'italic': first_run.italic,
                    'font_name': first_run.font.name,
                    'font_size': first_run.font.size,
                    'color': first_run.font.color.rgb if first_run.font.color and first_run.font.color.rgb else None
                }
            
            # Clear all runs
            for run in target_para.runs:
                r = run._element
                r.getparent().remove(r)
            
            # Add new run
            new_run = target_para.add_run(new_text)
            
            # Apply formatting
            if first_run_format:
                new_run.bold = first_run_format['bold']
                new_run.italic = first_run_format['italic']
                if first_run_format['font_name']:
                    new_run.font.name = first_run_format['font_name']
                if first_run_format['font_size']:
                    new_run.font.size = first_run_format['font_size']
                if first_run_format['color']:
                    new_run.font.color.rgb = first_run_format['color']
            
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

    def replace_placeholder_in_section(self, placeholder: str, value: str, section_keyword: Optional[str] = None) -> bool:
        """
        Replace a placeholder only in a specific section of the document.
        Useful for duplicate placeholders like "Address:" in company vs investor sections.
        
        Args:
            placeholder: The placeholder text to find (e.g., "Address: ")
            value: The replacement value
            section_keyword: Optional keyword to identify the section (e.g., "INVESTOR", "COMPANY")
        
        Returns:
            True if replacement was successful
        """
        try:
            replaced_count = 0
            found_section = False
            
            # Detect if this is a blank field placeholder
            is_blank_field = (
                (': ' in placeholder and placeholder.endswith(': ')) or
                placeholder.endswith(':')
            )
            
            # Search in paragraphs
            for i, para in enumerate(self.doc.paragraphs):
                # Check if we're in the right section
                if section_keyword:
                    # Look backwards from current paragraph for section header
                    in_section = False
                    for j in range(max(0, i - 20), i):  # Check up to 20 paragraphs back
                        if section_keyword.upper() in self.doc.paragraphs[j].text.upper():
                            in_section = True
                            break
                    
                    if not in_section:
                        continue
                
                if placeholder in para.text:
                    full_para_text = ''.join([run.text for run in para.runs])
                    
                    if placeholder in full_para_text:
                        # For blank fields, only add value after the label
                        if is_blank_field:
                            new_text = full_para_text.replace(placeholder, placeholder + value)
                        else:
                            # For explicit placeholders, replace the whole placeholder
                            new_text = full_para_text.replace(placeholder, value)
                        
                        # Get formatting from first run
                        first_run_format = None
                        if para.runs:
                            first_run = para.runs[0]
                            first_run_format = {
                                'bold': first_run.bold,
                                'italic': first_run.italic,
                                'font_name': first_run.font.name,
                                'font_size': first_run.font.size,
                                'color': first_run.font.color.rgb if first_run.font.color and first_run.font.color.rgb else None
                            }
                        
                        # Clear all runs
                        for run in para.runs:
                            r = run._element
                            r.getparent().remove(r)
                        
                        # Add new run with replaced text
                        new_run = para.add_run(new_text)
                        
                        # Apply preserved formatting
                        if first_run_format:
                            new_run.bold = first_run_format['bold']
                            new_run.italic = first_run_format['italic']
                            if first_run_format['font_name']:
                                new_run.font.name = first_run_format['font_name']
                            if first_run_format['font_size']:
                                new_run.font.size = first_run_format['font_size']
                            if first_run_format['color']:
                                new_run.font.color.rgb = first_run_format['color']
                        
                        replaced_count += 1
                        found_section = True
                        break  # Only replace first occurrence in section
            
            return replaced_count > 0
        except Exception as e:
            print(f"Error in section-aware replacement: {e}")
            return False
