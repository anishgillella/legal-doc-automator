import re
import json
import requests
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Placeholder:
    """Represents a detected placeholder"""
    text: str  # Full placeholder text as it appears
    name: str  # The name/key extracted from placeholder
    format_type: str  # Format: 'underscore', 'bracket', 'curly_bracket', etc.
    position: int  # Starting position in text
    end_position: int  # Ending position in text
    detected_by: str = 'regex'  # 'regex' or 'llm'


class PlaceholderDetector:
    def __init__(self):
        """Initialize placeholder detector with regex patterns"""
        # Define patterns for different placeholder formats
        # Comprehensive character set for placeholder names
        self.patterns = [
            # Double underscore: __placeholder__
            (r'__([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)__', 'double_underscore'),
            # Single underscore: _placeholder_
            (r'_([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)_', 'underscore'),
            # Square brackets: [placeholder]
            (r'\[([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)\]', 'bracket'),
            # Curly brackets: {placeholder}
            (r'\{([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)\}', 'curly_bracket'),
            # Double curly brackets: {{placeholder}}
            (r'\{\{([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)\}\}', 'double_curly_bracket'),
            # Angle brackets: <placeholder>
            (r'<([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)>', 'angle_bracket'),
        ]
        
        # Initialize LLM for second pass (optional)
        load_dotenv()
        self.llm_api_key = os.getenv('OPENROUTER_API_KEY')
    
    def detect_placeholders(self, text: str, use_llm: bool = False) -> List[Placeholder]:
        """
        Detect placeholders using regex for complete coverage
        
        Args:
            text: The text to search for placeholders
            use_llm: Unused (kept for backward compatibility)
        
        Returns:
            List of Placeholder objects found
        """
        # Regex-based detection (primary - gets 100% coverage)
        regex_placeholders = self._detect_with_regex(text)
        
        # Also detect blank fields (Label: ____ patterns)
        blank_field_placeholders = self._detect_blank_fields(text)
        
        # Combine both
        all_placeholders = regex_placeholders + blank_field_placeholders
        
        # Sort by position
        all_placeholders.sort(key=lambda p: p.position)
        
        return all_placeholders
    
    def _detect_with_regex(self, text: str) -> List[Placeholder]:
        """Detect placeholders using regex patterns"""
        placeholders = []
        
        for pattern, format_type in self.patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                placeholder_text = match.group(0)
                placeholder_name = match.group(1).strip()
                start_pos = match.start()
                end_pos = match.end()
                
                placeholder = Placeholder(
                    text=placeholder_text,
                    name=placeholder_name,
                    format_type=format_type,
                    position=start_pos,
                    end_position=end_pos,
                    detected_by='regex'
                )
                
                # Check for duplicates
                if not self._duplicate_exists(placeholder, placeholders):
                    placeholders.append(placeholder)
        
        return placeholders
    
    def _detect_with_llm(self, text: str) -> List[Placeholder]:
        """
        Detect placeholders using LLM (primary detection method)
        
        Returns:
            List of placeholders found by LLM
        """
        try:
            prompt = f"""You are analyzing a document to find placeholder fields that need to be filled in.

A placeholder is text that represents a field/value that needs user input. Examples:
- [name], [Company Name], [date]
- {{first_name}}, {{email}}
- _phone_number_, __address__
- <recipient>, <date>

The document text is below. Look for ALL text that appears to be a placeholder field that a user should fill in.
Return ONLY a JSON array of placeholders found, with no other text.

Format: [{{"text": "exact placeholder as it appears", "position": position_in_text}}]

Document text:
{text[:3000]}"""
            
            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "HTTP-Referer": "https://github.com/anishgillella/lexsy-document-ai",
                "X-Title": "Lexsy Document AI",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "qwen/qwen2.5-vl-72b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,  # Deterministic results
                "max_tokens": 2000
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"LLM detection failed with status {response.status_code}")
                return []
            
            result = response.json()
            llm_response = result['choices'][0]['message']['content']
            
            # Parse JSON response
            import re as regex_module
            json_match = regex_module.search(r'\[.*\]', llm_response, regex_module.DOTALL)
            if not json_match:
                return []
            
            llm_results = json.loads(json_match.group(0))
            
            # Convert to Placeholder objects
            placeholders = []
            for item in llm_results:
                placeholder_text = item.get('text', '')
                if placeholder_text:
                    # Find position in text
                    pos = text.find(placeholder_text)
                    placeholder = Placeholder(
                        text=placeholder_text,
                        name=placeholder_text.strip('[]{}()<>_'),
                        format_type='llm_detected',
                        position=pos if pos >= 0 else 0,
                        end_position=pos + len(placeholder_text) if pos >= 0 else len(placeholder_text),
                        detected_by='llm'
                    )
                    placeholders.append(placeholder)
            
            # Sort by position
            placeholders.sort(key=lambda p: p.position)
            return placeholders
        
        except Exception as e:
            print(f"LLM placeholder detection failed: {e}")
            return []
    
    def _detect_with_llm_fallback(self, text: str, regex_results: List[Placeholder]) -> List[Placeholder]:
        """
        Use LLM to detect placeholders missed by regex
        
        Args:
            text: The document text
            regex_results: Placeholders already found by regex
        
        Returns:
            Additional placeholders found by LLM (excluding duplicates)
        """
        try:
            # Get texts of already-found placeholders to avoid exact duplicates
            found_texts = {p.text for p in regex_results}
            
            prompt = f"""You are analyzing a document to find placeholder fields that need to be filled in.

A placeholder is text that represents a field/value that needs user input. Examples:
- [name], [Company Name], [date]
- {{first_name}}, {{email}}
- _phone_number_, __address__
- <recipient>, <date>

The document text is below. Look for ANY text that appears to be a placeholder field that a user should fill in.
Return ONLY a JSON array of placeholders found, with no other text.

Format: [{{"text": "exact placeholder as it appears"}}]

Document text:
{text[:2000]}"""
            
            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "HTTP-Referer": "https://github.com/anishgillella/lexsy-document-ai",
                "X-Title": "Lexsy Document AI",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "qwen/qwen2.5-vl-72b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code != 200:
                return []
            
            result = response.json()
            llm_response = result['choices'][0]['message']['content']
            
            # Parse JSON response
            import re as regex_module
            json_match = regex_module.search(r'\[.*\]', llm_response, regex_module.DOTALL)
            if not json_match:
                return []
            
            llm_results = json.loads(json_match.group(0))
            
            # Convert to Placeholder objects, avoiding duplicates with regex results
            new_placeholders = []
            for item in llm_results:
                placeholder_text = item.get('text', '')
                # Only add if not already found by regex
                if placeholder_text and placeholder_text not in found_texts:
                    # Find position in text
                    pos = text.find(placeholder_text)
                    placeholder = Placeholder(
                        text=placeholder_text,
                        name=placeholder_text.strip('[]{}()<>_'),
                        format_type='llm_detected',
                        position=pos if pos >= 0 else -1,
                        end_position=pos + len(placeholder_text) if pos >= 0 else -1,
                        detected_by='llm'
                    )
                    new_placeholders.append(placeholder)
            
            return new_placeholders
        
        except Exception as e:
            # Silent fail on LLM - regex results are enough
            return []
    
    def _detect_blank_fields(self, text: str) -> List[Placeholder]:
        """
        Detect blank fields formatted as "Label: ____" patterns.
        This is a heuristic and might not be perfect.
        """
        placeholders = []
        # Look for patterns like "Label: ____" on lines
        # Pattern: Start of line, optional whitespace, capitalized word(s), colon, underscores
        for match in re.finditer(r'^(\s*)([A-Z][a-zA-Z\s]*?):\s+(_{2,}).*$', text, re.MULTILINE):
            label_text = match.group(2).strip().lower()
            
            # Skip very short labels that are likely not field names
            if len(label_text) < 2:
                continue
            
            placeholder = Placeholder(
                text=match.group(0),  # Full line
                name=label_text.replace(' ', '_'),
                format_type='blank_field',
                position=match.start(),
                end_position=match.end(),
                detected_by='heuristic'
            )
            
            # Check for duplicates
            if not self._duplicate_exists(placeholder, placeholders):
                placeholders.append(placeholder)
        
        return placeholders
    
    def _duplicate_exists(self, placeholder: Placeholder, existing: List[Placeholder]) -> bool:
        """Check if a placeholder already exists in the list"""
        for existing_p in existing:
            if (existing_p.position == placeholder.position and 
                existing_p.end_position == placeholder.end_position):
                return True
        return False
    
    def extract_placeholder_names(self, text: str) -> List[str]:
        """Extract unique placeholder names"""
        placeholders = self.detect_placeholders(text, use_llm=False)
        names = []
        seen = set()
        
        for p in placeholders:
            if p.name not in seen:
                names.append(p.name)
                seen.add(p.name)
        
        return names


def detect_placeholders_simple(text: str) -> List[Dict]:
    """Convenience function for quick placeholder detection"""
    detector = PlaceholderDetector()
    placeholders = detector.detect_placeholders(text, use_llm=False)
    
    return [
        {
            'text': p.text,
            'name': p.name,
            'format': p.format_type,
            'position': p.position,
            'detected_by': p.detected_by
        }
        for p in placeholders
    ]
