"""
Placeholder Detector for backend2
Detects both explicit (bracketed) and implicit (blank field) placeholders
"""

import re
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class Placeholder:
    """Represents a detected placeholder"""
    text: str  # Full placeholder text as it appears
    name: str  # The name/key extracted from placeholder
    format_type: str  # Format: 'bracket', 'curly_bracket', 'parenthesis', 'blank_field', etc.
    position: int  # Starting position in text
    end_position: int  # Ending position in text
    detected_by: str = 'regex'  # 'regex' or 'heuristic'


class PlaceholderDetector:
    def __init__(self):
        """Initialize placeholder detector with regex patterns"""
        # Define patterns for different placeholder formats
        self.patterns = [
            # Square brackets: [placeholder]
            (r'\[([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)\]', 'bracket'),
            # Curly brackets: {placeholder}
            (r'\{([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)\}', 'curly_bracket'),
            # Parentheses: (placeholder)
            (r'\(([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)\)', 'parenthesis'),
            # Double curly brackets: {{placeholder}}
            (r'\{\{([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)\}\}', 'double_curly_bracket'),
            # Angle brackets: <placeholder>
            (r'<([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)>', 'angle_bracket'),
            # Underscores: __placeholder__ or _placeholder_
            (r'__([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)__', 'double_underscore'),
            (r'_([a-zA-Z0-9_\s,.\-/():\;&\'@#%+\?!=]+)_', 'underscore'),
        ]
    
    def detect_placeholders(self, text: str) -> List[Placeholder]:
        """
        Detect placeholders using regex for explicit placeholders
        and heuristics for blank fields
        
        Args:
            text: The text to search for placeholders
        
        Returns:
            List of Placeholder objects found
        """
        # Regex-based detection for explicit placeholders
        regex_placeholders = self._detect_with_regex(text)
        
        # Heuristic detection for blank fields (Label: ____ patterns)
        blank_field_placeholders = self._detect_blank_fields(text)
        
        # Combine both
        all_placeholders = regex_placeholders + blank_field_placeholders
        
        # Sort by position
        all_placeholders.sort(key=lambda p: p.position)
        
        return all_placeholders
    
    def _detect_with_regex(self, text: str) -> List[Placeholder]:
        """Detect explicit placeholders using regex patterns"""
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
    
    def _detect_blank_fields(self, text: str) -> List[Placeholder]:
        """
        Detect blank fields formatted as "Label: " or "Label:____" patterns.
        These are implicit placeholders that need to be filled.
        """
        placeholders = []
        
        # Pattern 1: "Label: " (with colon and space, followed by empty or whitespace)
        # This matches fields like "Name: ", "Address: ", "Email: "
        pattern1 = r'^(\s*)([A-Z][a-zA-Z\s]*?):\s*$'
        for match in re.finditer(pattern1, text, re.MULTILINE):
            label_text = match.group(2).strip()
            
            # Skip very short labels that are likely not field names
            if len(label_text) < 2:
                continue
            
            placeholder = Placeholder(
                text=match.group(0),  # Full line including label and colon
                name=label_text.lower().replace(' ', '_'),
                format_type='blank_field',
                position=match.start(),
                end_position=match.end(),
                detected_by='heuristic'
            )
            
            if not self._duplicate_exists(placeholder, placeholders):
                placeholders.append(placeholder)
        
        # Pattern 2: "Label: ____" (with underscores or spaces after colon)
        pattern2 = r'^(\s*)([A-Z][a-zA-Z\s]*?):\s+(_{2,}|\s{2,}).*$'
        for match in re.finditer(pattern2, text, re.MULTILINE):
            label_text = match.group(2).strip()
            
            if len(label_text) < 2:
                continue
            
            placeholder = Placeholder(
                text=match.group(0),  # Full line
                name=label_text.lower().replace(' ', '_'),
                format_type='blank_field',
                position=match.start(),
                end_position=match.end(),
                detected_by='heuristic'
            )
            
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
        placeholders = self.detect_placeholders(text)
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
    placeholders = detector.detect_placeholders(text)
    
    return [
        {
            'text': p.text,
            'name': p.name,
            'format': p.format_type,
            'position': p.position,
            'end_position': p.end_position,
            'detected_by': p.detected_by
        }
        for p in placeholders
    ]

