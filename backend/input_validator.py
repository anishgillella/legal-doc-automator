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
    what_was_entered: Optional[str] = None  # Echo what user entered
    what_expected: Optional[str] = None  # What the field expects
    suggestion: Optional[str] = None  # Suggestion for correction
    example: Optional[str] = None  # Example of correct format


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
        
        prompt = f"""You are an intelligent form validation assistant. Your job is to validate user input and provide HELPFUL, DETAILED feedback.

FIELD INFORMATION:
- Field Name: {field_name}
- Expected Type: {data_type}
- Question Asked: {suggested_question}

USER INPUT: "{user_input}"

YOUR TASKS:
1. Determine if this is valid for the field
2. If invalid, explain what's wrong in a friendly way
3. If there's a typo, suggest the correction
4. Provide examples of correct input if needed
5. Check for ambiguity (e.g., date formats)
6. Provide a formatted/corrected version if applicable

VALIDATION RULES BY TYPE:
- For names (string): Should be alphabetic with proper capitalization. Examples: "John Smith", "Jane Doe"
- For email: Must contain @ and valid domain. Examples: "john@example.com"
- For currency: Numbers only, 2 decimal places. Examples: "1500.00", "250.99"
- For date: Accept multiple formats (MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD, Month DD YYYY, etc.) and convert to YYYY-MM-DD. Examples: "2024-12-25", "12/25/2024", "December 25, 2024"
- For phone: (XXX) XXX-XXXX or XXX-XXX-XXXX. Examples: "(555) 123-4567" or "555-123-4567"
- For number: Only digits. Examples: "42", "1000"
- For address: Street number and name. Examples: "123 Main Street", "456 Oak Avenue"

FEEDBACK STYLE:
- Be conversational and friendly
- If wrong, explain what they entered and what we need instead
- Offer specific suggestions
- Provide good examples
- Don't just say "invalid" - be helpful!

Respond ONLY with valid JSON (no other text):
{{
    "is_valid": true/false,
    "is_ambiguous": true/false,
    "formatted_value": "the formatted/corrected value or original if unchanged",
    "confidence": 0.0-1.0,
    "message": "friendly message about the validation result",
    "clarification": "clarification question if ambiguous (null if none)",
    "what_was_entered": "echo back what they typed",
    "what_expected": "description of what this field should contain",
    "suggestion": "specific suggestion if there's an error (null if valid)",
    "example": "example of correct input for this field"
}}

EXAMPLES:
- Input "11/11/2025" for date field
  → is_valid: true
  → formatted_value: "2025-11-11"
  → message: "Perfect! Converting to standard format."
  → example: "2025-11-11"

- Input "jhn smith" for name field
  → message: "I think you meant 'John Smith' - let me fix that!"
  → what_was_entered: "jhn smith"
  → formatted_value: "John Smith"
  → suggestion: "Maybe 'John Smith'? (j-o-h-n)"
  → is_valid: true
  → confidence: 0.85"""
        
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
            "max_tokens": 800
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
        what_was_entered = validation_data.get('what_was_entered', user_input)
        what_expected = validation_data.get('what_expected', '')
        suggestion = validation_data.get('suggestion')
        example = validation_data.get('example', '')
        
        # Check confidence threshold
        if confidence < self.min_confidence and is_valid:
            return ValidationResult(
                is_valid=False,
                is_ambiguous=True,
                formatted_value=formatted_value,
                confidence=confidence,
                message=f"I'm not quite sure about this. Could you verify?",
                clarification_needed=f"Is '{formatted_value}' the correct {field_name}?",
                what_was_entered=what_was_entered,
                what_expected=what_expected,
                suggestion=suggestion,
                example=example
            )
        
        return ValidationResult(
            is_valid=is_valid and confidence >= self.min_confidence,
            is_ambiguous=is_ambiguous,
            formatted_value=formatted_value,
            confidence=confidence,
            message=message,
            clarification_needed=clarification,
            what_was_entered=what_was_entered,
            what_expected=what_expected,
            suggestion=suggestion,
            example=example
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
