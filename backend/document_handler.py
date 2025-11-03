import os
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from typing import Dict, List, Tuple


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
        Replace a placeholder with actual value while preserving formatting
        Works in both regular paragraphs AND table cells.
        Replaces ALL occurrences in the document.
        
        Handles two types of placeholders:
        1. Explicit placeholders: [Company Name] -> Replace entire placeholder
        2. Blank field placeholders: "Email: " or "Address: " -> Keep label, replace blank
        
        Args:
            placeholder: The placeholder text to find (e.g., "[founder_name]" or "Email: ")
            value: The replacement value
        
        Returns:
            True if at least one replacement was successful
        """
        try:
            replaced_count = 0
            
            # Detect if this is a blank field placeholder (label ending with ": " or ":")
            is_blank_field = (
                (': ' in placeholder and placeholder.endswith(': ')) or
                placeholder.endswith(':')
            )
            
            # Debug: Show what we're looking for
            field_type = "BLANK FIELD" if is_blank_field else "EXPLICIT PLACEHOLDER"
            
            # Replace in regular paragraphs
            for para in self.doc.paragraphs:
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
        Replace a specific occurrence of a placeholder (useful for duplicates)
        
        Args:
            placeholder: The placeholder text to find
            value: The replacement value
            position_index: Which occurrence to replace (0 = first, 1 = second, etc.)
        
        Returns:
            True if replacement was successful
        """
        try:
            occurrence_count = 0
            
            # Search in paragraphs first
            for para in self.doc.paragraphs:
                if placeholder in para.text:
                    full_para_text = ''.join([run.text for run in para.runs])
                    
                    if placeholder in full_para_text:
                        # Count occurrences up to this point
                        count_in_para = full_para_text.count(placeholder)
                        
                        if occurrence_count <= position_index < occurrence_count + count_in_para:
                            # This is the paragraph containing our target
                            # For simplicity, replace all in this paragraph
                            # (More complex logic needed for multiple in same para)
                            new_text = full_para_text.replace(placeholder, value, 1)
                            
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
                            
                            return True
                        
                        occurrence_count += count_in_para
            
            # Search in table cells
            for table in self.doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if placeholder in cell.text:
                            for para in cell.paragraphs:
                                if placeholder in para.text:
                                    full_para_text = ''.join([run.text for run in para.runs])
                                    
                                    if placeholder in full_para_text:
                                        count_in_para = full_para_text.count(placeholder)
                                        
                                        if occurrence_count <= position_index < occurrence_count + count_in_para:
                                            new_text = full_para_text.replace(placeholder, value, 1)
                                            
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
                                            
                                            for run in para.runs:
                                                r = run._element
                                                r.getparent().remove(r)
                                            
                                            new_run = para.add_run(new_text)
                                            
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
                                        
                                        occurrence_count += count_in_para
            
            return False
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
