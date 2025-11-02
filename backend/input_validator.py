"""
LLM-Powered Input Validation
Validates, formats, and detects ambiguous user inputs
"""

import json
import requests
import os
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool  # Is the input acceptable?
    is_ambiguous: bool  # Does it need clarification?
    formatted_value: str  # Formatted/corrected value
    confidence: float  # Confidence score (0-1)
    message: str  # Message to show user
    clarification_needed: Optional[str] = None  # What to ask user


class InputValidator:
    def __init__(self):
        """Initialize validator with LLM"""
        load_dotenv()
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = "qwen/qwen2.5-vl-72b-instruct"
        self.base_url = "https://openrouter.ai/api/v1"
        self.min_confidence = 0.75  # High confidence threshold
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env")
    
    def validate_input(
        self, 
        user_input: str, 
        field_name: str, 
        data_type: str, 
        suggested_question: str
    ) -> ValidationResult:
        """
        Validate user input using LLM
        
        Args:
            user_input: What the user entered
            field_name: Name of the field (e.g., "Company Name")
            data_type: Type (string, email, currency, date, phone, etc.)
            suggested_question: The question asked to user
        
        Returns:
            ValidationResult with status, formatted value, and message
        """
        try:
            result = self._call_llm_validation(
                user_input, 
                field_name, 
                data_type, 
                suggested_question
            )
            return result
        except Exception as e:
            # Fallback: accept input as-is if LLM fails
            return ValidationResult(
                is_valid=True,
                is_ambiguous=False,
                formatted_value=user_input,
                confidence=0.5,
                message="(Validated with fallback)"
            )
    
    def _call_llm_validation(
        self, 
        user_input: str, 
        field_name: str, 
        data_type: str, 
        suggested_question: str
    ) -> ValidationResult:
        """Call LLM to validate input"""
        
        prompt = f"""You are validating user input for a form field.

Field Information:
- Field Name: {field_name}
- Expected Type: {data_type}
- Question Asked: {suggested_question}

User Input: "{user_input}"

Your tasks:
1. Validate: Is this a reasonable value for this field?
2. Format: Convert to correct format if needed
3. Ambiguity: Does this need clarification? (e.g., date format ambiguity)
4. Confidence: How confident are you (0-1)?

Rules:
- For dates: Standardize to YYYY-MM-DD
- For phone: Standardize to (XXX) XXX-XXXX or XXX-XXX-XXXX
- For email: Validate email format
- For currency: Remove symbols, ensure 2 decimal places
- For names: Proper capitalization

Respond ONLY with valid JSON (no other text):
{{
    "is_valid": true/false,
    "is_ambiguous": true/false,
    "formatted_value": "the formatted value",
    "confidence": 0.0-1.0,
    "message": "brief message to user",
    "clarification": "clarification needed (null if none)"
}}

Examples:
- Input "john" for name → formatted_value: "John", confidence: 0.95
- Input "12/25/24" for date → is_ambiguous: true, clarification: "Is this MM/DD/YY?"
- Input "invalid@" for email → is_valid: false, message: "Invalid email format"
- Input "$1,000.50" for currency → formatted_value: "1000.50", confidence: 0.95"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/anishgillella/lexsy-document-ai",
            "X-Title": "Lexsy Document AI",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,  # Low temp for consistent validation
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code}")
        
        result = response.json()
        llm_response = result['choices'][0]['message']['content']
        
        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        if not json_match:
            raise Exception("Could not parse LLM response")
        
        validation_data = json.loads(json_match.group(0))
        
        # Extract fields
        is_valid = validation_data.get('is_valid', False)
        is_ambiguous = validation_data.get('is_ambiguous', False)
        formatted_value = validation_data.get('formatted_value', user_input)
        confidence = validation_data.get('confidence', 0.0)
        message = validation_data.get('message', '')
        clarification = validation_data.get('clarification')
        
        # Check confidence threshold
        if confidence < self.min_confidence and is_valid:
            return ValidationResult(
                is_valid=False,
                is_ambiguous=True,
                formatted_value=formatted_value,
                confidence=confidence,
                message=f"Low confidence ({confidence:.0%}). Please verify.",
                clarification_needed=f"Is '{formatted_value}' correct for {field_name}?"
            )
        
        return ValidationResult(
            is_valid=is_valid and confidence >= self.min_confidence,
            is_ambiguous=is_ambiguous,
            formatted_value=formatted_value,
            confidence=confidence,
            message=message,
            clarification_needed=clarification
        )


def validate_user_input(
    user_input: str,
    field_name: str,
    data_type: str,
    suggested_question: str
) -> ValidationResult:
    """Convenience function for input validation"""
    validator = InputValidator()
    return validator.validate_input(user_input, field_name, data_type, suggested_question)
