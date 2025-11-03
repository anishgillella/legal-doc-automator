/**
 * Type definitions for Lexsy Document AI Frontend
 */

export interface PlaceholderAnalysis {
  placeholder_text: string;
  placeholder_name: string;
  placeholder_id?: string; // Unique identifier (position-based)
  data_type: 'string' | 'email' | 'currency' | 'date' | 'phone' | 'number' | 'address' | 'url';
  description: string;
  suggested_question: string;
  example: string;
  required: boolean;
  validation_hint?: string;
}

export interface ProcessResponse {
  success: boolean;
  document_path: string;
  text_length: number;
  placeholder_count: number;
  placeholders: Array<{
    text: string;
    name: string;
    format: string;
    position: number;
  }>;
  analyses: PlaceholderAnalysis[];
  analyzed: boolean;
  status?: 'success' | 'no_placeholders' | 'success_no_llm';
  message?: string;
}

export interface FormState {
  file: File | null;
  placeholders: PlaceholderAnalysis[];
  values: Record<string, string>;
  currentFieldIndex: number;
  isLoading: boolean;
  error: string | null;
  documentStatus?: 'idle' | 'success' | 'no_placeholders' | 'success_no_llm';
  documentMessage?: string;
}

export interface ValidationResponse {
  field: string;
  is_valid: boolean;
  is_ambiguous: boolean;
  formatted_value: string;
  confidence: number;
  message: string;
  clarification_needed: string | null;
  what_was_entered: string | null;
  what_expected: string | null;
  suggestion: string | null;
  example: string | null;
}

export interface FillResponse {
  success: boolean;
  message: string;
  download_url?: string;
}
