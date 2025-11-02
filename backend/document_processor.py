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
        
        # Step 3: Analyze with LLM (optional)
        if analyze_with_llm:
            try:
                self.llm_analyzer = LLMAnalyzer()
                
                # Use new semantic grouping approach:
                # Send ALL placeholders + full document to LLM
                # LLM identifies which are duplicates and groups them
                # Returns ONE question per unique semantic group
                self.placeholder_analyses = self.llm_analyzer.group_placeholders_by_semantic_meaning(
                    placeholders_data,
                    self.full_text  # Full document context
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
                print(f"Warning: LLM semantic grouping failed: {e}")
        
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
            
            # Separate position-based keys from regular keys
            position_based = {}
            regular = {}
            
            for key, value in values.items():
                if '__pos_' in key:
                    position_based[key] = value
                else:
                    regular[key] = value
            
            total_replacements = 0
            
            # Replace position-based placeholders first (most specific)
            for key, value in position_based.items():
                # Extract placeholder text and position: "text__pos_0" -> ("text", 0)
                placeholder_text = key.rsplit('__pos_', 1)[0]
                try:
                    position = int(key.rsplit('__pos_', 1)[1])
                    success = self.doc_handler.replace_placeholder_at_position(placeholder_text, value, position)
                    if success:
                        total_replacements += 1
                    else:
                        # Try regular replacement as fallback
                        success = self.doc_handler.replace_placeholder(placeholder_text, value)
                        if success:
                            total_replacements += 1
                            print(f"Fallback: Replaced {key} using regular method")
                        else:
                            print(f"Warning: Failed to replace {key}")
                except Exception as e:
                    print(f"Error with position-based replacement {key}: {e}")
                    # Try regular replacement as fallback
                    try:
                        success = self.doc_handler.replace_placeholder(placeholder_text, value)
                        if success:
                            total_replacements += 1
                    except:
                        pass
            
            # Replace remaining regular placeholders
            for placeholder_text, value in regular.items():
                success = self.doc_handler.replace_placeholder(placeholder_text, value)
                if success:
                    total_replacements += 1
                else:
                    print(f"Warning: Failed to replace: {placeholder_text}")
            
            print(f"Successfully replaced {total_replacements}/{len(values)} placeholders")
            
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
