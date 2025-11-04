import os
import json
import tempfile
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

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
    
    def process(self, analyze_with_llm: bool = True) -> Dict:
        """
        Full processing pipeline:
        1. Load document
        2. Extract text
        3. Detect placeholders
        4. Analyze with LLM (optional)
        
        Args:
            analyze_with_llm: Whether to use LLM for analysis
        
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
                "analyses": []
            }
        
        # Convert to dict format for JSON serialization and LLM
        # Include surrounding context for each placeholder to help LLM distinguish duplicates
        placeholders_data = []
        for idx, p in enumerate(self.placeholders):
            # Extract surrounding context (100 chars before and after for semantic meaning)
            start = max(0, p.position - 100)
            end = min(len(self.full_text), p.position + len(p.text) + 100)
            surrounding_context = self.full_text[start:end].strip()
            
            placeholders_data.append({
                'index': idx,  # Position index to identify duplicates
                'text': p.text,
                'name': p.name,
                'format': p.format_type,
                'position': p.position,
                'context': surrounding_context  # Extended context for better distinction
            })
        
        result = {
            "success": True,
            "document_path": self.doc_path,
            "text_length": len(self.full_text),
            "placeholder_count": len(self.placeholders),
            "placeholders": placeholders_data
        }
        
        # Step 3: Analyze with LLM (optional) - LLM-FIRST approach
        if analyze_with_llm:
            try:
                self.llm_analyzer = LLMAnalyzer()
                
                # TRY LLM-FIRST: Ask LLM to detect ALL fields comprehensively
                print("🔍 Attempting LLM-first field detection...")
                llm_detected_fields = self.llm_analyzer.detect_all_fields(self.full_text)
                
                if llm_detected_fields:
                    # LLM successfully detected all fields
                    print(f"✓ LLM detected {len(llm_detected_fields)} fields")
                    self.placeholder_analyses = llm_detected_fields
                else:
                    # LLM detected nothing, fall back to regex+heuristic based analysis
                    print("⚠ LLM detected no fields, using regex+heuristic detection...")
                    self.placeholder_analyses = self.llm_analyzer.group_placeholders_by_semantic_meaning(
                        placeholders_data,
                        self.full_text
                    )
                
                # Convert analyses to dict format
                analyses_data = [
                    {
                        'placeholder_text': a.placeholder_text,
                        'placeholder_name': a.placeholder_name,
                        'data_type': a.data_type,
                        'description': a.description,
                        'suggested_question': a.suggested_question,
                        'example': a.example,
                        'required': a.required,
                        'validation_hint': a.validation_hint
                    }
                    for a in self.placeholder_analyses
                ]
                
                result['analyses'] = analyses_data
                result['analyzed'] = True
                
            except Exception as e:
                result['error_analyzing'] = str(e)
                result['analyzed'] = False
                print(f"Warning: LLM analysis failed: {e}")
        
        return result
    
    def _get_analysis_context(self, max_length: int = 2000) -> str:
        """
        Get relevant context from document for LLM analysis
        
        Args:
            max_length: Maximum character length of context
        
        Returns:
            Context string
        """
        if len(self.full_text) <= max_length:
            return self.full_text
        
        # Return first part of document (usually most relevant)
        return self.full_text[:max_length] + "\n[... document continues ...]"
    
    def fill_placeholders(self, values: Dict[str, str]) -> Tuple[bool, str]:
        """
        Fill placeholders with provided values
        
        Args:
            values: Dictionary mapping placeholder text -> replacement value
                   Supports both direct text keys and position-based keys (text__pos_N)
                   e.g., {"_founder_name_": "John Doe", "[_____________]__pos_0": "150000"}
        
        Returns:
            Tuple of (success: bool, output_path: str)
        """
        try:
            # IMPORTANT: Load the document first!
            if not self.doc_handler.load_document():
                print("Failed to load document")
                return False, ""
            
            total_replacements = 0
            
            # Separate different types of keys
            field_name_keys = {}  # field_name -> value
            placeholder_keys = {}  # placeholder_text -> value
            position_based = {} # placeholder__pos_N -> value
            
            for key, value in values.items():
                if '__pos_' in key:
                    position_based[key] = value
                elif key in ['company_address', 'investor_address', 'company_email', 'investor_email', 
                             'company_name', 'investor_name', 'company_title', 'investor_title',
                             'purchase_amount', 'post_money_valuation_cap', 'date_of_safe', 
                             'state_of_incorporation', 'company_representative_name', 'company_representative_title',
                             'investor_signature', 'governing_law_jurisdiction']:
                    # This is a field name
                    field_name_keys[key] = value
                else:
                    # This is a placeholder text
                    placeholder_keys[key] = value
            
            # Priority 1: Use field names with context-aware replacement
            if field_name_keys:
                print(f"✓ Using {len(field_name_keys)} field-name-based replacements (context-aware)\n")
                # Use context-aware replacement based on field name
                for field_name, value in field_name_keys.items():
                    # Determine the section keyword based on field name
                    section_keyword = 'investor' if 'investor' in field_name else 'company'
                    
                    # Guess the placeholder based on field name
                    if 'address' in field_name:
                        placeholders_to_try = ['Address: ', 'Address:\t', 'Address:  ']
                    elif 'email' in field_name:
                        placeholders_to_try = ['Email: ', 'Email:\t', 'Email:  ']
                    elif 'title' in field_name:
                        placeholders_to_try = ['Title: ', 'Title:\t', 'Title:  ', '[title]', '[Title]']
                    elif 'name' in field_name:
                        placeholders_to_try = ['[name]', '[Name]', '[investor_name]', '[Investor Name]', '[company_name]', '[Company Name]', 'Name: ', 'Name:\t']
                    else:
                        placeholders_to_try = [field_name]
                    
                    # Try each placeholder
                    for placeholder in placeholders_to_try:
                        success = self.doc_handler.replace_placeholder_in_section(placeholder, value, section_keyword)
                        if success:
                            total_replacements += 1
                            print(f"  ✓ Context: {field_name:30} → {value[:25]}")
                            break
                    else:
                        print(f"  ✗ Failed: {field_name}")
                
                print()
            
            # Priority 2: Position-based (fallback)
            elif position_based:
                print(f"✓ Using {len(position_based)} position-based replacements (fallback)\n")
                for key, value in position_based.items():
                    placeholder_text = key.rsplit('__pos_', 1)[0]
                    try:
                        position = int(key.rsplit('__pos_', 1)[1])
                        success = self.doc_handler.replace_placeholder_at_position(placeholder_text, value, position)
                        if success:
                            total_replacements += 1
                        else:
                            success = self.doc_handler.replace_placeholder(placeholder_text, value)
                            if success:
                                total_replacements += 1
                                print(f"  Fallback: Replaced {key}")
                            else:
                                print(f"  ✗ Failed: {key}")
                    except Exception as e:
                        print(f"  Error: {key}: {e}")
                
                print()
            
            # Priority 3: Plain placeholder text (backward compatibility)
            else:
                print(f"✓ Using {len(placeholder_keys)} placeholder-based replacements\n")
                for placeholder_text, value in placeholder_keys.items():
                    success = self.doc_handler.replace_placeholder(placeholder_text, value)
                    if success:
                        total_replacements += 1
                        print(f"  ✓ Replaced: {placeholder_text:40} → {value[:25]}")
                    else:
                        print(f"  ✗ Failed:   {placeholder_text}")
                
                print()
            
            print(f"\n{'='*80}")
            print(f"RESULT: Successfully replaced {total_replacements}/{len(values)} placeholders")
            print(f"{'='*80}\n")
            
            # Save to temporary file
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, "filled_document.docx")
            
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
                   e.g., {"founder_name": "John Doe", "company_name": "Acme Inc"}
        
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
    
    def get_placeholder_info(self) -> List[Dict]:
        """Get information about detected placeholders with analysis"""
        if not self.placeholders:
            return []
        
        result = []
        for i, placeholder in enumerate(self.placeholders):
            info = {
                'index': i,
                'text': placeholder.text,
                'name': placeholder.name,
                'format': placeholder.format_type,
                'position': placeholder.position
            }
            
            # Add analysis if available
            if self.placeholder_analyses and i < len(self.placeholder_analyses):
                analysis = self.placeholder_analyses[i]
                info['analysis'] = {
                    'data_type': analysis.data_type,
                    'description': analysis.description,
                    'suggested_question': analysis.suggested_question,
                    'example': analysis.example,
                    'required': analysis.required,
                    'validation_hint': analysis.validation_hint
                }
            
            result.append(info)
        
        return result


def process_document_workflow(doc_path: str, values: Dict[str, str]) -> Tuple[bool, Optional[str], Dict]:
    """
    Complete workflow: detect, analyze, and fill placeholders
    
    Args:
        doc_path: Path to .docx file
        values: Dictionary of values to fill
    
    Returns:
        Tuple of (success, output_path, details)
    """
    processor = DocumentProcessor(doc_path)
    
    # Process document
    process_result = processor.process(analyze_with_llm=True)
    
    if not process_result.get('success'):
        return False, None, process_result
    
    # Fill placeholders
    success, output_path = processor.fill_by_name(values)
    
    return success, output_path, process_result
