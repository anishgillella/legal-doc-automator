import requests
import json
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from dataclasses import dataclass


@dataclass
class PlaceholderAnalysis:
    """Analysis result for a placeholder"""
    placeholder_text: str
    placeholder_name: str
    data_type: str  # e.g., 'string', 'email', 'currency', 'date', 'number'
    description: str  # What this field represents
    suggested_question: str  # How to ask the user for this
    example: str  # Example value
    required: bool  # Is this field required?
    validation_hint: Optional[str]  # Hint for validation (e.g., "Must be valid email")


class LLMAnalyzer:
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM Analyzer with OpenRouter API
        
        Args:
            api_key: OpenRouter API key. If not provided, will use OPENROUTER_API_KEY from .env
        """
        load_dotenv()
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = "qwen/qwen2.5-vl-72b-instruct"
        self.base_url = "https://openrouter.ai/api/v1"
        
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY in .env")
    
    def detect_all_fields(self, document_text: str) -> List[PlaceholderAnalysis]:
        """
        LLM-first comprehensive field detection.
        Send entire document to LLM and ask it to identify ALL fields that need filling.
        This includes explicit placeholders AND blank fields in a single pass.
        
        Handles large documents by intelligent chunking:
        - Documents < 10k chars: Send entire document
        - Larger documents: Split by sections, analyze each, deduplicate
        
        Args:
            document_text: The full document text
        
        Returns:
            List of PlaceholderAnalysis objects for all detected fields
        """
        if len(document_text.strip()) < 100:
            return []
        
        doc_length = len(document_text)
        
        # Strategy based on document size
        if doc_length < 10000:
            # Small document: send entire thing
            print(f"📄 Document size: {doc_length} chars (small) - sending entire document")
            return self._detect_fields_in_chunk(document_text, "Full Document")
        else:
            # Large document: split into intelligent chunks
            print(f"📄 Document size: {doc_length} chars (large) - using intelligent chunking")
            return self._detect_fields_with_chunking(document_text)
    
    def _detect_fields_with_chunking(self, document_text: str) -> List[PlaceholderAnalysis]:
        """Split large document intelligently and detect fields from all chunks."""
        chunks = self._split_document_intelligent(document_text)
        print(f"📑 Split document into {len(chunks)} chunks for analysis")
        
        all_fields = []
        seen_field_names = set()
        
        for i, (chunk_name, chunk_text) in enumerate(chunks, 1):
            print(f"  Analyzing chunk {i}/{len(chunks)}: {chunk_name}")
            
            chunk_fields = self._detect_fields_in_chunk(chunk_text, chunk_name)
            
            # Add fields, skip duplicates based on field name
            for field in chunk_fields:
                if field.placeholder_name not in seen_field_names:
                    all_fields.append(field)
                    seen_field_names.add(field.placeholder_name)
        
        print(f"✓ Total unique fields detected: {len(all_fields)}")
        return all_fields
    
    def _split_document_intelligent(self, document_text: str, chunk_size: int = 8000) -> List[tuple]:
        """Split document intelligently into pages."""
        chunks = []
        lines = document_text.split('\n')
        current_page = []
        current_size = 0
        page_num = 1
        
        for line in lines:
            line_size = len(line) + 1
            if current_size + line_size > chunk_size and current_page:
                chunks.append((f"Page {page_num}", '\n'.join(current_page)))
                current_page = []
                current_size = 0
                page_num += 1
            
            current_page.append(line)
            current_size += line_size
        
        if current_page:
            chunks.append((f"Page {page_num}", '\n'.join(current_page)))
        
        return chunks
    
    def _detect_fields_in_chunk(self, chunk_text: str, chunk_name: str) -> List[PlaceholderAnalysis]:
        """Analyze a single chunk and detect fields in it"""
        prompt = f"""Analyze this document chunk and identify ONLY ACTUAL FIELDS that need to be filled in.

Chunk: {chunk_name}

Document:
{chunk_text}

IDENTIFY ALL PLACEHOLDER TYPES:

Explicit placeholders (replace entire placeholder):
- [field name] - Square brackets
- {{field name}} - Curly braces  
- (field name) - Parentheses
- _____  - Underscores

Blank fields (keep label, replace blank part):
- "Label: _____" - Label with underscores
- "Label:        " - Label with spaces
- "Label: " - Label with blank
- "Name:" - Just colon (blank to fill)

For EACH valid field you identify:
1. Field name (e.g., "investor_name", "company_address")
2. The EXACT placeholder text AS IT APPEARS (e.g., "[Company Name]", "Address: ", "$[_____________]")
3. Data type (email, address, string, date, currency, phone, number, url)
4. Natural question to ask user
5. Example value
6. Mark as NOT required

Return as JSON array:
[
  {{
    "field_name": "company_email",
    "field_label": "Email",
    "placeholder_text": "Email: ",
    "data_type": "email",
    "suggested_question": "What is the company's email address?",
    "example": "company@example.com",
    "required": false,
    "description": "The email address of the company"
  }}
]"""

        try:
            response = self._call_openrouter(prompt)
            analyses = self._parse_detect_all_fields_response(response)
            return analyses
        except Exception as e:
            print(f"⚠ Error analyzing chunk '{chunk_name}': {e}")
            return []
    
    def _parse_detect_all_fields_response(self, response: str) -> List[PlaceholderAnalysis]:
        """Parse LLM response for detect_all_fields"""
        try:
            import re as regex_module
            json_match = regex_module.search(r'\[.*\]', response, regex_module.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response
            
            fields_data = json.loads(json_str)
            analyses = []
            
            for data in fields_data:
                field_id = data.get('field_name', data.get('field_label', '').lower().replace(' ', '_'))
                actual_placeholder = data.get('placeholder_text') or data.get('actual_placeholder')
                
                if not actual_placeholder:
                    actual_placeholder = f"[{field_id}]"
                
                analysis = PlaceholderAnalysis(
                    placeholder_text=actual_placeholder,
                    placeholder_name=field_id,
                    data_type=data.get('data_type', 'string'),
                    description=data.get('description', data.get('field_label', '')),
                    suggested_question=data.get('suggested_question', f"What is the {data.get('field_label', 'field').lower()}?"),
                    example=data.get('example', ''),
                    required=False,
                    validation_hint=None
                )
                analyses.append(analysis)
            
            return analyses
        except Exception as e:
            print(f"Error parsing detect_all_fields response: {e}")
            return []
    
    def _call_openrouter(self, prompt: str) -> str:
        """Call OpenRouter API with the Qwen model"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/anishgillella/lexsy-document-ai",
            "X-Title": "Lexsy Document AI",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise ValueError(f"Unexpected OpenRouter response: {result}")
        except Exception as e:
            print(f"OpenRouter API Error: {e}")
            raise

