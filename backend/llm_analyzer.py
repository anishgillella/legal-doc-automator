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
        self.model = "qwen/qwen2.5-vl-72b-instruct"  # Using the requested model
        self.base_url = "https://openrouter.ai/api/v1"  # Fixed: .ai not .io
        
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY in .env")
    
    def assess_document_content(self, text: str) -> str:
        """
        Provide intelligent assessment when no placeholders found
        Uses LLM to understand document type and provide context-aware message
        """
        if len(text.strip()) == 0:
            return "Document appears to be empty. No content found to analyze."
        
        try:
            # Ask LLM to assess document type and provide helpful message
            prompt = f"""Analyze this document and provide a brief assessment:

Document Text (first 1000 chars):
{text[:1000]}

Provide ONE sentence explaining what type of document this is and why it might not have placeholder fields.
Be concise and helpful. Examples:
- "This appears to be a completed rental agreement with all fields already filled in."
- "This is a template document that uses a different format for variables (e.g., {{{{variable}}}}) rather than underscores."
- "This document contains mostly text content without structured fields or placeholders."

Response (one sentence only):"""
            
            response = self._call_openrouter(prompt)
            # Extract just the first sentence
            message = response.split('.')[0] + '.'
            return message.strip()
        except Exception as e:
            print(f"Could not generate assessment: {e}")
            return "Document processed - no placeholder fields detected in this document."
    
    def analyze_placeholders(self, placeholders: List[Dict], document_context: str) -> List[PlaceholderAnalysis]:
        """
        Analyze a list of placeholders to understand what they need
        
        Args:
            placeholders: List of placeholder dictionaries with 'text', 'name', 'format'
            document_context: Context from the document (excerpt around placeholders)
        
        Returns:
            List of PlaceholderAnalysis objects
        """
        prompt = self._build_analysis_prompt(placeholders, document_context)
        
        try:
            response = self._call_openrouter(prompt)
            analyses = self._parse_analysis_response(response, placeholders)
            return analyses
        except Exception as e:
            print(f"⚠️  LLM analysis unavailable (fallback mode): {str(e)[:100]}")
            # Return fallback analysis if LLM call fails
            return self._fallback_analysis(placeholders)
    
    def _build_analysis_prompt(self, placeholders: List[Dict], context: str) -> str:
        """Build the prompt for analyzing placeholders"""
        placeholders_str = json.dumps(placeholders, indent=2)
        
        prompt = f"""You are analyzing ALL placeholders found in a legal document by regex pattern matching.
Your CRITICAL task is to provide UNIQUE analysis for EACH placeholder, even if they have identical text.

You MUST use the 'context' field to distinguish what each placeholder represents.

CRITICAL EXAMPLES:
If you see the SAME placeholder text like "[_____________]" appearing twice:
1. First occurrence with context: "...of $[_____________] (the "Purchase Amount")..."
   → This is the PURCHASE AMOUNT - ask "What is the investment amount in dollars?"
   
2. Second occurrence with context: "...The "Post-Money Valuation Cap" is $[_____________]..."
   → This is the VALUATION CAP - ask "What is the post-money valuation cap?"

These are DIFFERENT fields with DIFFERENT meanings despite identical placeholder text!

For each placeholder, determine:
1. Data type (string, currency, date, email, number, address, phone, etc.)
2. What this field represents based on SURROUNDING CONTEXT (not just the placeholder text)
3. A UNIQUE natural question to ask the user (different for each placeholder even if text is identical)
4. An example value
5. Whether it's required
6. Any validation hints

MUST: Each placeholder gets a DIFFERENT question if context reveals different meanings!
MUST: Use 'context' field to understand semantic meaning of each placeholder!
MUST: Two placeholders with same text but different context = two different questions!

Document Context (for reference):
{context}

All regex-detected placeholders with their index and surrounding context:
{placeholders_str}

Respond in JSON format with an array of objects (one per placeholder), each with:
{{
    "placeholder_text": "the placeholder as it appears",
    "placeholder_name": "extracted name",
    "data_type": "string/email/currency/date/number/...",
    "description": "what this field is for",
    "suggested_question": "how to ask user for this",
    "example": "example value",
    "required": true/false,
    "validation_hint": "validation guidance or null"
}}

Return ONLY the JSON array, no other text."""
        
        return prompt
    
    def _call_openrouter(self, prompt: str) -> str:
        """
        Call OpenRouter API with the Qwen model
        
        Args:
            prompt: The prompt to send
        
        Returns:
            The model's response text
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/anishgillella/lexsy-document-ai",
            "X-Title": "Lexsy Document AI",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0,  # Deterministic: 0 for consistent, reproducible results
            "top_p": 0.9,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                data=json.dumps(payload),  # Use data with json.dumps instead of json parameter
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise ValueError(f"Unexpected OpenRouter response: {result}")
        except requests.exceptions.HTTPError as e:
            print(f"OpenRouter API HTTP Error: {e.response.status_code} - {e.response.text[:200]}")
            raise
    
    def _parse_analysis_response(self, response: str, placeholders: List[Dict]) -> List[PlaceholderAnalysis]:
        """
        Parse the LLM response into PlaceholderAnalysis objects
        
        Args:
            response: The LLM's JSON response
            placeholders: Original placeholders (for fallback)
        
        Returns:
            List of PlaceholderAnalysis objects
        """
        try:
            # Extract JSON from response (in case there's extra text)
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response
            
            analyses_data = json.loads(json_str)
            
            analyses = []
            for data in analyses_data:
                analysis = PlaceholderAnalysis(
                    placeholder_text=data.get('placeholder_text', ''),
                    placeholder_name=data.get('placeholder_name', ''),
                    data_type=data.get('data_type', 'string'),
                    description=data.get('description', ''),
                    suggested_question=data.get('suggested_question', ''),
                    example=data.get('example', ''),
                    required=data.get('required', True),
                    validation_hint=data.get('validation_hint')
                )
                analyses.append(analysis)
            
            return analyses
        except Exception as e:
            print(f"Error parsing analysis response: {e}")
            print(f"Response was: {response}")
            return self._fallback_analysis(placeholders)
    
    def _fallback_analysis(self, placeholders: List[Dict]) -> List[PlaceholderAnalysis]:
        """
        Provide fallback analysis when LLM fails
        Uses heuristics based on placeholder names
        """
        analyses = []
        
        # Common heuristics for placeholder names
        type_hints = {
            'email': 'email',
            'amount': 'currency',
            'date': 'date',
            'number': 'number',
            'phone': 'string',
            'address': 'string',
            'name': 'string',
            'price': 'currency',
            'percentage': 'number',
        }
        
        for ph in placeholders:
            name_lower = ph['name'].lower()
            data_type = 'string'  # default
            
            # Check for type hints in name
            for hint, dtype in type_hints.items():
                if hint in name_lower:
                    data_type = dtype
                    break
            
            analysis = PlaceholderAnalysis(
                placeholder_text=ph['text'],
                placeholder_name=ph['name'],
                data_type=data_type,
                description=f"Field: {ph['name']}",
                suggested_question=f"Please provide {ph['name']}:",
                example="[example value]",
                required=True,
                validation_hint=None
            )
            analyses.append(analysis)
        
        return analyses

    def group_placeholders_by_semantic_meaning(self, placeholders: List[Dict], document_context: str) -> List[PlaceholderAnalysis]:
        """
        Analyze ALL placeholders together to identify semantic duplicates and group them.
        
        Args:
            placeholders: ALL regex-detected placeholders with text and index
            document_context: Full document text for context
        
        Returns:
            List of PlaceholderAnalysis - one per unique semantic group
        """
        placeholders_str = json.dumps(placeholders, indent=2)
        
        prompt = f"""You are analyzing ALL placeholders found in a legal document.
Your task is to identify which placeholders represent the SAME semantic field (even if text looks different).

CRITICAL: Identify semantic grouping:
- Placeholders [_____________] at indices 2 and 7 might represent DIFFERENT fields
  - Index 2 context: purchase amount
  - Index 7 context: valuation cap
  → These are DIFFERENT groups - need 2 questions

For each UNIQUE semantic field, provide:
1. Which placeholder indices belong to this group (e.g., [2, 7] or just [0])
2. The placeholder text(s) that represent this field
3. Data type
4. ONE clear, concise question to ask the user (not paraphrased variants)
5. Description based on document context
6. Example value
7. Whether required
8. Validation hints

IMPORTANT: 
- If multiple placeholders represent the SAME field → group them, ONE question
- If placeholders look same but represent DIFFERENT fields → separate groups, different questions
- Generate EXACTLY ONE question per unique semantic group
- Do NOT paraphrase similar questions

Full document context:
{document_context}

All regex-detected placeholders (with index for grouping):
{placeholders_str}

Return JSON format with array of analysis objects:
[
  {{
    "placeholder_indices": [2],
    "placeholder_texts": ["[_____________]"],
    "placeholder_name": "Purchase Amount",
    "data_type": "currency",
    "suggested_question": "What is the purchase amount in dollars?",
    "description": "The investment amount paid by the investor",
    "example": "$500,000",
    "required": true,
    "validation_hint": "Must be a positive amount"
  }},
  ...
]

IMPORTANT: Return only this JSON array, no other text."""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/anishgillella/lexsy-document-ai",
                "X-Title": "Lexsy Document AI",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,  # Deterministic
                "max_tokens": 4000
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                llm_response = result['choices'][0]['message']['content']
                
                # Parse JSON response
                import re as regex_module
                json_match = regex_module.search(r'\[.*\]', llm_response, regex_module.DOTALL)
                if not json_match:
                    print("Could not find JSON in LLM response")
                    return []
                
                grouped_data = json.loads(json_match.group(0))
                
                # Convert to PlaceholderAnalysis objects
                analyses = []
                for group in grouped_data:
                    analysis = PlaceholderAnalysis(
                        placeholder_text=group.get('placeholder_texts', [group.get('placeholder_text', '')])[0],
                        placeholder_name=group.get('placeholder_name', 'Unknown'),
                        data_type=group.get('data_type', 'string'),
                        description=group.get('description', ''),
                        suggested_question=group.get('suggested_question', 'What is this field?'),
                        example=group.get('example', ''),
                        required=group.get('required', True),
                        validation_hint=group.get('validation_hint', None)
                    )
                    analyses.append(analysis)
                
                return analyses
            
            return []
        
        except Exception as e:
            print(f"Error grouping placeholders: {e}")
            return []


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
        """
        Split large document intelligently and detect fields from all chunks.
        Deduplicates results from multiple chunks.
        """
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
        """
        Split document intelligently into pages.
        Uses fixed chunk size as "pages" since we don't have explicit page breaks in text.
        Each chunk represents approximately one page of content.
        """
        chunks = []
        
        # Split into pages (~8000 chars per page, typical page of text)
        lines = document_text.split('\n')
        current_page = []
        current_size = 0
        page_num = 1
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            # If adding this line exceeds page size and we have content, save as page
            if current_size + line_size > chunk_size and current_page:
                chunks.append((f"Page {page_num}", '\n'.join(current_page)))
                current_page = []
                current_size = 0
                page_num += 1
            
            current_page.append(line)
            current_size += line_size
        
        # Add final page
        if current_page:
            chunks.append((f"Page {page_num}", '\n'.join(current_page)))
        
        return chunks
    
    def _detect_fields_in_chunk(self, chunk_text: str, chunk_name: str) -> List[PlaceholderAnalysis]:
        """Analyze a single chunk and detect fields in it"""
        prompt = f"""Analyze this document chunk and identify ONLY ACTUAL FIELDS that need to be filled in.

Chunk: {chunk_name}

Document:
{chunk_text}

IMPORTANT: Only identify fields that meet ONE of these criteria:
1. Has explicit placeholder markers: [field], _field_, {{field}}, __field__, <field>, etc.
2. Has blank spaces/underscores after the label: "Name: _____" or "Address:        "
3. Is clearly a signature line or form field: "By:", "Signature:", "Date:"
4. Is in a table cell that's empty or has placeholder text

DO NOT identify as fields:
❌ Random text with punctuation like "()" or other symbols that are part of sentences
❌ Explanatory text that happens to have colons, like "Note: This is important"
❌ Section headers or labels that aren't meant to be filled (like "1. Introduction:")
❌ Words in parentheses that are just clarifications
❌ Any text that's clearly part of the document prose

For EACH valid field you identify:
1. Field name or label (e.g., "Name", "Email Address", "Company Name")
2. Data type (email, address, string, date, currency, phone, number, url, signature, etc.)
3. Natural question to ask the user
4. Example value
5. Mark as NOT required (all fields are optional)

Return as JSON array:
[
  {{
    "field_name": "investor_name",
    "field_label": "Name",
    "data_type": "string",
    "suggested_question": "What is the investor's full name?",
    "example": "John Smith",
    "required": false,
    "description": "The full name of the investor"
  }}
]

Be selective and only identify true placeholders/form fields, not random text."""

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
                # Use field_name if available, otherwise use field_label
                field_id = data.get('field_name', data.get('field_label', '').lower().replace(' ', '_'))
                
                analysis = PlaceholderAnalysis(
                    placeholder_text=f"[{field_id}]",
                    placeholder_name=field_id,
                    data_type=data.get('data_type', 'string'),
                    description=data.get('description', data.get('field_label', '')),
                    suggested_question=data.get('suggested_question', f"What is the {data.get('field_label', 'field').lower()}?"),
                    example=data.get('example', ''),
                    required=False,  # All fields are non-mandatory
                    validation_hint=None
                )
                analyses.append(analysis)
            
            return analyses
        except Exception as e:
            print(f"Error parsing detect_all_fields response: {e}")
            print(f"Response was: {response[:200]}")
            return []

    def analyze_blank_fields(self, blank_fields: List[Dict], document_context: str) -> List[PlaceholderAnalysis]:
        """
        Analyze blank fields (Label: ____ patterns) to understand what data they need.
        Uses LLM to infer data types and generate questions.
        
        Args:
            blank_fields: List of detected blank fields with their labels
            document_context: Context from the document
        
        Returns:
            List of PlaceholderAnalysis objects for blank fields
        """
        if not blank_fields:
            return []
        
        # Build field list for LLM
        fields_text = "\n".join([f["name"] for f in blank_fields])
        
        prompt = f"""You are analyzing blank fields in a SAFE (Simple Agreement for Future Equity) document.

Detected fields:
{fields_text}

Document context (first 500 chars):
{document_context[:500]}

For each field, determine:
1. Data type (email, address, string, date, currency, phone, number, url, etc.)
2. Natural question to ask the user
3. Example value
4. Whether it's required

Return as JSON array with this structure:
[
  {{
    "field_name": "address",
    "data_type": "address",
    "suggested_question": "What is the investor's mailing address?",
    "example": "123 Main St, San Francisco, CA 94102",
    "required": true,
    "description": "The physical address of the investor"
  }}
]

Be concise and practical."""

        try:
            response = self._call_openrouter(prompt)
            analyses = self._parse_blank_field_response(response, blank_fields)
            return analyses
        except Exception as e:
            print(f"Error analyzing blank fields with LLM: {e}")
            return self._fallback_blank_field_analysis(blank_fields)
    
    def _parse_blank_field_response(self, response: str, blank_fields: List[Dict]) -> List[PlaceholderAnalysis]:
        """Parse LLM response for blank field analysis"""
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
                analysis = PlaceholderAnalysis(
                    placeholder_text=f"[{data.get('field_name', '')}]",
                    placeholder_name=data.get('field_name', '').lower().replace(' ', '_'),
                    data_type=data.get('data_type', 'string'),
                    description=data.get('description', data.get('field_name', '')),
                    suggested_question=data.get('suggested_question', f"What is the {data.get('field_name', '')}?"),
                    example=data.get('example', ''),
                    required=data.get('required', True),
                    validation_hint=None
                )
                analyses.append(analysis)
            
            return analyses
        except Exception as e:
            print(f"Error parsing blank field response: {e}")
            return self._fallback_blank_field_analysis(blank_fields)
    
    def _fallback_blank_field_analysis(self, blank_fields: List[Dict]) -> List[PlaceholderAnalysis]:
        """Fallback analysis for blank fields using heuristics"""
        analyses = []
        
        type_hints = {
            'email': 'email',
            'address': 'address',
            'name': 'string',
            'phone': 'phone',
            'date': 'date',
            'signature': 'string',
            'title': 'string'
        }
        
        for field in blank_fields:
            field_name = field['name'].lower()
            
            # Try to infer type from field name
            inferred_type = 'string'
            for hint, data_type in type_hints.items():
                if hint in field_name:
                    inferred_type = data_type
                    break
            
            analysis = PlaceholderAnalysis(
                placeholder_text=f"[{field['name']}]",
                placeholder_name=field['name'].lower().replace(' ', '_'),
                data_type=inferred_type,
                description=f"Field: {field['name']}",
                suggested_question=f"What is the {field['name'].lower()}?",
                example=f"[Example {field['name']}]",
                required=True,
                validation_hint=None
            )
            analyses.append(analysis)
        
        return analyses


def analyze_placeholders(placeholders: List[Dict], context: str, 
                        api_key: Optional[str] = None) -> List[PlaceholderAnalysis]:
    """
    Convenience function for placeholder analysis
    
    Args:
        placeholders: List of placeholder dictionaries
        context: Document context
        api_key: Optional OpenRouter API key
    
    Returns:
        List of PlaceholderAnalysis objects
    """
    analyzer = LLMAnalyzer(api_key=api_key)
    return analyzer.analyze_placeholders(placeholders, context)
