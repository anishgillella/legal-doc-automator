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
