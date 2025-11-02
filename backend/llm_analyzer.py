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
        
        prompt = f"""You are analyzing placeholders in a legal document. For each placeholder, determine:
1. What type of data is expected (string, email, currency, date, number, etc.)
2. What this field represents (description)
3. How to ask the user for this information in a natural way
4. An example value
5. Whether it's required
6. Any validation hints

Document Context:
{context}

Placeholders to analyze:
{placeholders_str}

Respond in JSON format with an array of objects, each with:
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
            "temperature": 0.3,  # Lower temperature for consistent analysis
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
