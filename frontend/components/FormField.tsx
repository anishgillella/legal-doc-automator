/**
 * FormField Component - Single question input
 */

'use client';

import { PlaceholderAnalysis } from '@/types/index';

interface FormFieldProps {
  field: PlaceholderAnalysis | null;
  value: string;
  onChange: (value: string) => void;
  isLoading?: boolean;
  error?: string;
  onSubmit?: () => void;
}

export function FormField({
  field,
  value,
  onChange,
  isLoading = false,
  error,
  onSubmit,
}: FormFieldProps) {
  if (!field) {
    return null;
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && onSubmit && !isLoading) {
      e.preventDefault();
      onSubmit();
    }
  };

  const getInputType = (): string => {
    switch (field.data_type) {
      case 'email':
        return 'email';
      case 'currency':
        return 'text';
      case 'date':
        return 'date';
      case 'phone':
        return 'tel';
      case 'number':
        return 'number';
      default:
        return 'text';
    }
  };

  const getPlaceholder = (): string => {
    switch (field.data_type) {
      case 'email':
        return 'e.g., john@example.com';
      case 'currency':
        return 'e.g., $5,000.00';
      case 'date':
        return 'e.g., 2024-11-02';
      case 'phone':
        return 'e.g., (555) 123-4567';
      case 'number':
        return `e.g., ${field.example}`;
      default:
        return field.example || `e.g., ${field.placeholder_name}`;
    }
  };

  return (
    <div className="w-full space-y-4">
      {/* Field Label */}
      <div>
        <label className="block text-lg font-semibold text-secondary-900 mb-2">
          {field.suggested_question}
        </label>
        {field.description && (
          <p className="text-sm text-secondary-600 mb-3">{field.description}</p>
        )}
        {field.validation_hint && (
          <p className="text-xs text-secondary-500 italic">💡 {field.validation_hint}</p>
        )}
      </div>

      {/* Input Field */}
      <input
        type={getInputType()}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={getPlaceholder()}
        disabled={isLoading}
        onKeyDown={handleKeyDown}
        className={`
          w-full px-4 py-3 border-2 rounded-lg font-medium text-base
          transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-opacity-50
          ${
            error
              ? 'border-error bg-red-50 focus:border-error'
              : 'border-secondary-200 bg-white hover:border-secondary-300 focus:border-primary-500'
          }
          ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
          ${!value ? 'text-secondary-400' : 'text-secondary-900'}
        `}
      />

      {/* Error Message */}
      {error && (
        <div className="flex items-start gap-2 p-3 bg-red-50 border border-error rounded-lg">
          <span className="text-error text-xl flex-shrink-0">✕</span>
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      {/* Helper Text */}
      <div className="flex items-center gap-2 text-xs text-secondary-500">
        <span className="inline-block w-1 h-1 bg-secondary-400 rounded-full" />
        <span>
          {field.required ? 'Required field' : 'Optional field'}
        </span>
        {field.data_type !== 'string' && (
          <>
            <span className="inline-block w-1 h-1 bg-secondary-400 rounded-full" />
            <span>Format: {field.data_type}</span>
          </>
        )}
      </div>
    </div>
  );
}
