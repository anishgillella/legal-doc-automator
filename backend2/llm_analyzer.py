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
    
    def analyze_placeholders_with_context(self, document_text: str, regex_placeholders: List[Dict]) -> List[PlaceholderAnalysis]:
        """
        Analyze regex-detected placeholders with LLM to provide context and deduplication.
        
        Args:
            document_text: The full document text
            regex_placeholders: List of placeholder dicts from regex detection with 'text', 'name', 'position', etc.
        
        Returns:
            List of PlaceholderAnalysis objects with context for unique fields
        """
        if not regex_placeholders:
            return []
        
        # Group placeholders by text to find duplicates
        placeholder_groups = {}
        for ph in regex_placeholders:
            text = ph['text']
            if text not in placeholder_groups:
                placeholder_groups[text] = []
            placeholder_groups[text].append(ph)
        
        # Extract context around each placeholder occurrence (100 chars before and after for better context)
        placeholder_contexts = []
        for text, occurrences in placeholder_groups.items():
            for occ in occurrences:
                pos = occ.get('position', 0)
                end_pos = occ.get('end_position', pos + len(text))
                
                # Extract context (100 chars before and after for better context matching)
                context_start = max(0, pos - 100)
                context_end = min(len(document_text), end_pos + 100)
                context = document_text[context_start:context_end]
                
                placeholder_contexts.append({
                    'text': text,
                    'name': occ.get('name', ''),
                    'position': pos,
                    'context': context,
                    'occurrence_index': placeholder_groups[text].index(occ)
                })
        
        # Send to LLM for analysis with context
        return self._analyze_placeholders_with_llm(document_text, placeholder_contexts)
    
    def detect_all_fields(self, document_text: str) -> List[PlaceholderAnalysis]:
        """
        Legacy method - kept for backward compatibility.
        Use analyze_placeholders_with_context instead.
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
- "By:" - Signature fields with colon
- "By:        " - Signature fields with spaces after colon
- "Name:   " - Name fields with spaces
- Any label ending with ":" followed by spaces/underscores/blank

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
    
    def _analyze_placeholders_with_llm(self, document_text: str, placeholder_contexts: List[Dict]) -> List[PlaceholderAnalysis]:
        """
        Analyze placeholders with full document context using LLM.
        
        Args:
            document_text: Full document text
            placeholder_contexts: List of dicts with 'text', 'name', 'position', 'context', 'occurrence_index'
        
        Returns:
            List of PlaceholderAnalysis objects
        """
        # Build list of detected placeholders WITH CONTEXT for each occurrence
        # This is critical for distinguishing identical placeholders like [_____________] that represent different fields
        placeholders_list = ""
        for idx, ctx in enumerate(placeholder_contexts, 1):
            placeholder_text = ctx['text']
            context = ctx.get('context', '')
            placeholders_list += f"\n{idx}. Placeholder: '{placeholder_text}'\n"
            placeholders_list += f"   Context (100 chars before/after): ...{context}...\n"
        
        prompt = f"""Analyze this document and the placeholders detected by regex. Identify which placeholders are ACTUAL FIELDS that need to be filled in by the user, versus legal text or definitions that should NOT be filled.

FULL DOCUMENT TEXT:
{document_text}

PLACEHOLDERS DETECTED BY REGEX (WITH CONTEXT):
{placeholders_list}

CRITICAL INSTRUCTIONS:
1. Review the FULL document context AND the surrounding context for EACH placeholder occurrence listed above
2. Identify which placeholders are ACTUAL FIELDS that need user input:
   - Short bracketed placeholders (1-3 words): "[Company Name]", "[COMPANY]", "[Investor Name]", "[name]", "[title]", "[Date of Safe]"
   - Underscore placeholders like "[_____________]" - these are actual fields that need values
   - Label fields like "Address: ", "Email: ", "Name: ", "By:"
   - Signature section fields (even if similar to header fields)
   - DO NOT include long legal text in brackets/parentheses (even if detected by regex)
3. IGNORE placeholders that are:
   - Legal definitions or explanations in parentheses like "(a) Equity Financing..."
   - Section references like "(i)", "(ii)", "(iii)" when they're just list markers
   - Legal citations like "(within the meaning of Section 13(d)...)"
   - Long legal text blocks in parentheses
4. IMPORTANT: Include ALL signature section placeholders:
   - "[COMPANY]" is different from "[Company Name]" - include both
   - "[name]" in company section vs investor section - include both separately
   - "By:", "Name:", "Title:", "Address:", "Email:" in signature sections
5. ABSOLUTELY CRITICAL: For placeholders with IDENTICAL TEXT but DIFFERENT CONTEXT:
   - You MUST examine EACH occurrence's context separately
   - If the same placeholder text appears with DIFFERENT surrounding context → treat as SEPARATE FIELDS
   - Example: If "[_____________]" appears multiple times:
     * Occurrence 1 near "Purchase Amount" or "$" → field_name: "purchase_amount"
     * Occurrence 2 near "Post-Money Valuation Cap" or "Valuation Cap" → field_name: "post_money_valuation_cap"
     * Occurrence 3 near "Pre-Money Valuation Cap" → field_name: "pre_money_valuation_cap"
   - Look at the surrounding text (100 chars before/after) to understand what each occurrence represents
   - Return ONE entry per occurrence with different context, even if placeholder text is identical
   - DO NOT group them together - each unique context needs its own field entry
6. For placeholders with IDENTICAL TEXT and SAME CONTEXT:
   - Normalize whitespace: "Address: " and "Address:\n" are the SAME field → return ONE entry
   - If the same placeholder appears multiple times with the SAME meaning → group as ONE field
7. Provide context-based descriptions to distinguish similar placeholders
8. When returning placeholder_text, use the CLEANEST version (e.g., "Address: " not "Address:\n                        ")
9. MANDATORY: You MUST return an entry for EVERY occurrence of actual form fields, even if they have the same placeholder text. Count how many times each placeholder appears in the list above and ensure you return that many entries (if they have different contexts).

Return ONLY actual fields that need filling, as JSON array. For identical placeholder texts with different contexts, return separate entries:
[
  {{
    "field_name": "company_name",
    "placeholder_text": "[Company Name]",
    "data_type": "string",
    "description": "The name of the company issuing the SAFE",
    "suggested_question": "What is the company name?",
    "example": "Acme Corp",
    "required": false
  }},
  {{
    "field_name": "purchase_amount",
    "placeholder_text": "[_____________]",
    "data_type": "number",
    "description": "The amount paid by the investor (Purchase Amount)",
    "suggested_question": "What is the purchase amount?",
    "example": "100000",
    "required": false
  }},
  {{
    "field_name": "post_money_valuation_cap",
    "placeholder_text": "[_____________]",
    "data_type": "number",
    "description": "The post-money valuation cap amount",
    "suggested_question": "What is the post-money valuation cap?",
    "example": "5000000",
    "required": false
  }}
]

ONLY return placeholders that are actual form fields, NOT legal text or definitions."""
        
        try:
            response = self._call_openrouter(prompt)
            analyses = self._parse_placeholder_analysis_response(response, placeholder_contexts)
            return analyses
        except Exception as e:
            print(f"⚠ Error analyzing placeholders with LLM: {e}")
            # Fallback: create basic analyses from regex placeholders
            return self._create_fallback_analyses(placeholder_contexts)
    
    def _parse_placeholder_analysis_response(self, response: str, placeholder_contexts: List[Dict]) -> List[PlaceholderAnalysis]:
        """Parse LLM response for placeholder analysis"""
        try:
            import re as regex_module
            json_match = regex_module.search(r'\[.*\]', response, regex_module.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response
            
            fields_data = json.loads(json_str)
            analyses = []
            
            # Map each LLM response to a placeholder context by matching placeholder text and order
            placeholder_text_to_contexts = {}
            for ctx in placeholder_contexts:
                text = ctx['text']
                if text not in placeholder_text_to_contexts:
                    placeholder_text_to_contexts[text] = []
                placeholder_text_to_contexts[text].append(ctx)
            
            # Match LLM responses to placeholder contexts
            # For multiple entries with same placeholder_text, match them to different occurrences based on context
            used_contexts = set()
            placeholder_text_entry_count = {}  # Track how many entries we've seen for each placeholder_text
            
            for data in fields_data:
                field_id = data.get('field_name', '').lower().replace(' ', '_')
                placeholder_text = data.get('placeholder_text', '')
                description = data.get('description', '').lower()
                
                # Track entry count for this placeholder text
                if placeholder_text not in placeholder_text_entry_count:
                    placeholder_text_entry_count[placeholder_text] = 0
                placeholder_text_entry_count[placeholder_text] += 1
                
                # Find matching placeholder contexts that haven't been used
                matching_contexts = [ctx for ctx in placeholder_text_to_contexts.get(placeholder_text, []) 
                                   if id(ctx) not in used_contexts]
                
                # If multiple entries for same placeholder_text, try to match by context similarity
                if len(matching_contexts) > 1:
                    # Try to find context that best matches the description
                    best_match = None
                    best_score = 0
                    for ctx in matching_contexts:
                        context_lower = ctx.get('context', '').lower()
                        # Score based on how many words from description appear in context
                        description_words = set(word for word in description.split() if len(word) > 3)
                        context_words = set(word for word in context_lower.split() if len(word) > 3)
                        score = len(description_words & context_words)
                        if score > best_score:
                            best_score = score
                            best_match = ctx
                    
                    if best_match:
                        ctx = best_match
                        used_contexts.add(id(ctx))
                    else:
                        # Use first available
                        ctx = matching_contexts[0]
                        used_contexts.add(id(ctx))
                elif matching_contexts:
                    # Use the first matching context
                    ctx = matching_contexts[0]
                    used_contexts.add(id(ctx))
                else:
                    # Fallback: use first context with matching text
                    ctx = placeholder_text_to_contexts.get(placeholder_text, [{}])[0] if placeholder_text_to_contexts.get(placeholder_text) else {}
                
                analysis = PlaceholderAnalysis(
                    placeholder_text=placeholder_text,
                    placeholder_name=field_id,
                    data_type=data.get('data_type', 'string'),
                    description=data.get('description', ctx.get('context', '')[:100] if ctx else ''),
                    suggested_question=data.get('suggested_question', f"What is the {field_id.replace('_', ' ')}?"),
                    example=data.get('example', ''),
                    required=data.get('required', False),
                    validation_hint=None
                )
                analyses.append(analysis)
            
            # Deduplicate analyses - group similar placeholders (whitespace variations)
            # BUT: Keep separate entries if they have different field_names (same placeholder text, different context)
            def normalize_placeholder(text: str) -> str:
                """Normalize placeholder text for comparison (remove extra whitespace)"""
                # Remove leading/trailing whitespace and normalize internal whitespace
                # Replace all whitespace (spaces, tabs, newlines) with single space
                normalized = ' '.join(text.strip().split())
                # For label fields, normalize to "Label:"
                if ':' in normalized:
                    label_part = normalized.split(':')[0].strip()
                    return label_part + ':'
                return normalized
            
            # Group analyses by (normalized placeholder text, field_name) tuple
            # This allows same placeholder text with different field_names to be kept separate
            key_to_analyses = {}
            for analysis in analyses:
                normalized = normalize_placeholder(analysis.placeholder_text)
                key = (normalized, analysis.placeholder_name)  # Use both text and field_name as key
                if key not in key_to_analyses:
                    key_to_analyses[key] = []
                key_to_analyses[key].append(analysis)
            
            # Keep only one analysis per (normalized placeholder, field_name) combination
            # But keep separate entries for different field_names even if placeholder text is identical
            deduplicated_analyses = []
            regex_detected_texts = {ctx['text'] for ctx in placeholder_contexts}
            
            for (normalized, field_name), analysis_list in key_to_analyses.items():
                if len(analysis_list) > 1:
                    # Multiple variations with same placeholder text AND field_name - deduplicate
                    # Prefer:
                    # 1. One that matches regex-detected text exactly
                    # 2. One with the best description (not fallback)
                    def score_analysis(a):
                        score = 0
                        if a.placeholder_text in regex_detected_texts:
                            score += 1000  # Prefer regex-detected exact matches
                        if a.description and not a.description.startswith("Field found"):
                            score += len(a.description)  # Prefer better descriptions
                        return score
                    
                    best = max(analysis_list, key=score_analysis)
                    deduplicated_analyses.append(best)
                    if len(analysis_list) > 1:
                        variations = [a.placeholder_text[:50] + '...' if len(a.placeholder_text) > 50 else a.placeholder_text for a in analysis_list]
                        print(f"  ℹ Deduplicated {len(analysis_list)} variations of '{normalized}' (field: {field_name}): {variations[:2]}... → keeping '{best.placeholder_text[:50]}...'")
                else:
                    deduplicated_analyses.append(analysis_list[0])
            
            # Check which placeholders were detected by regex but NOT returned by LLM
            regex_placeholder_texts = {ctx['text'] for ctx in placeholder_contexts}
            # Normalize LLM returned texts for comparison
            llm_returned_normalized = {normalize_placeholder(a.placeholder_text) for a in deduplicated_analyses}
            missing_from_llm = []
            for text in regex_placeholder_texts:
                normalized_text = normalize_placeholder(text)
                if normalized_text not in llm_returned_normalized:
                    missing_from_llm.append(text)
            
            if missing_from_llm:
                print(f"\n⚠ LLM did not return {len(missing_from_llm)} placeholder(s) detected by regex:")
                for text in sorted(missing_from_llm):
                    # Check if it's likely an actual field:
                    # - Short bracketed placeholders (1-3 words): [COMPANY], [name], [title]
                    # - NOT long legal text in brackets
                    is_bracketed = text.startswith('[') and text.endswith(']')
                    is_short = len(text.strip('[]').split()) <= 3
                    is_simple_name = text.strip('[]').replace(' ', '').isalnum() or '_' in text.strip('[]')
                    
                    is_likely_field = (
                        (is_bracketed and is_short and is_simple_name) or
                        (text.strip().endswith(':') and len(text.strip().rstrip(':')) < 20)
                    )
                    
                    if is_likely_field:
                        print(f"  - '{text}' (likely an actual field - adding to list)")
                        # Find context for this placeholder
                        matching_contexts = [ctx for ctx in placeholder_contexts if ctx['text'] == text]
                        if matching_contexts:
                            ctx = matching_contexts[0]
                            base_name = ctx['name'].lower().replace(' ', '_')
                            analysis = PlaceholderAnalysis(
                                placeholder_text=text,
                                placeholder_name=base_name,
                                data_type='string',
                                description=f"Field found in document: {ctx.get('context', '')[:100]}...",
                                suggested_question=f"What is the {ctx['name'].lower()}?",
                                example='',
                                required=False,
                                validation_hint=None
                            )
                            deduplicated_analyses.append(analysis)
                    else:
                        print(f"  - '{text}' (likely legal text - correctly filtered)")
            
            # Check if LLM missed any occurrences - ensure all actual fields are detected
            # Group placeholder contexts by text to see if any were missed
            placeholder_text_to_contexts = {}
            for ctx in placeholder_contexts:
                text = ctx['text']
                if text not in placeholder_text_to_contexts:
                    placeholder_text_to_contexts[text] = []
                placeholder_text_to_contexts[text].append(ctx)
            
            # For each placeholder text, check if we have analyses for all occurrences
            for placeholder_text, contexts in placeholder_text_to_contexts.items():
                # Skip legal text placeholders (long parentheses, etc.)
                is_likely_field = (
                    (placeholder_text.startswith('[') and placeholder_text.endswith(']') and len(placeholder_text.strip('[]').split()) <= 3) or
                    (placeholder_text.strip().endswith(':') and len(placeholder_text.strip().rstrip(':')) < 20) or
                    ('_____' in placeholder_text)  # Underscore placeholders
                )
                
                if is_likely_field and len(contexts) > 1:
                    # Check how many analyses we have for this placeholder
                    matching_analyses = [a for a in deduplicated_analyses 
                                       if normalize_placeholder(a.placeholder_text) == normalize_placeholder(placeholder_text)]
                    
                    if len(matching_analyses) < len(contexts):
                        print(f"\n  ⚠ Found {len(contexts)} occurrences of '{placeholder_text}' but only {len(matching_analyses)} analysis entries")
                        print(f"     LLM may have missed some occurrences - they will be handled during replacement")
            
            # FINAL deduplication pass after auto-recovery
            # This ensures auto-recovered placeholders are also deduplicated
            final_normalized_to_analyses = {}
            for analysis in deduplicated_analyses:
                normalized = normalize_placeholder(analysis.placeholder_text)
                key = (normalized, analysis.placeholder_name)  # Use both text and field_name
                if key not in final_normalized_to_analyses:
                    final_normalized_to_analyses[key] = []
                final_normalized_to_analyses[key].append(analysis)
            
            final_deduplicated = []
            for (normalized, field_name), analysis_list in final_normalized_to_analyses.items():
                if len(analysis_list) > 1:
                    # Prefer regex-detected exact matches, then better descriptions
                    def score_analysis(a):
                        score = 0
                        if a.placeholder_text in regex_detected_texts:
                            score += 1000
                        if a.description and not a.description.startswith("Field found"):
                            score += len(a.description)
                        return score
                    best = max(analysis_list, key=score_analysis)
                    final_deduplicated.append(best)
                    if len(analysis_list) > 1:
                        print(f"  ℹ Final deduplication: {len(analysis_list)} variations of '{normalized}' (field: {field_name}) → keeping best match")
                else:
                    final_deduplicated.append(analysis_list[0])
            
            return final_deduplicated
        except Exception as e:
            print(f"Error parsing placeholder analysis response: {e}")
            return self._create_fallback_analyses(placeholder_contexts)
    
    def _create_fallback_analyses(self, placeholder_contexts: List[Dict]) -> List[PlaceholderAnalysis]:
        """Create fallback analyses from placeholder contexts - return ALL unique placeholders"""
        analyses = []
        seen_combinations = set()  # Track (text, occurrence_index) to ensure uniqueness
        
        for ctx in placeholder_contexts:
            # Create unique key: text + occurrence index
            unique_key = (ctx['text'], ctx['occurrence_index'])
            
            if unique_key not in seen_combinations:
                seen_combinations.add(unique_key)
                
                # Create unique field name based on context
                base_name = ctx['name'].lower().replace(' ', '_')
                if ctx['occurrence_index'] > 0:
                    field_name = f"{base_name}_{ctx['occurrence_index'] + 1}"
                else:
                    field_name = base_name
                
                analysis = PlaceholderAnalysis(
                    placeholder_text=ctx['text'],
                    placeholder_name=field_name,
                    data_type='string',
                    description=f"Field found: {ctx['context'][:100]}...",
                    suggested_question=f"What is the {ctx['name'].lower()}?",
                    example="",
                    required=False,
                    validation_hint=None
                )
                analyses.append(analysis)
        
        return analyses
    
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

