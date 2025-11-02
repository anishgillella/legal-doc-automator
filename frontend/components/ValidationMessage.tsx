/**
 * ValidationMessage Component - Shows validation feedback
 */

'use client';

import { ValidationResponse } from '@/types/index';

interface ValidationMessageProps {
  validation: ValidationResponse | null;
  isLoading?: boolean;
  onAccept?: () => void;
  onReject?: () => void;
}

export function ValidationMessage({
  validation,
  isLoading = false,
  onAccept,
  onReject,
}: ValidationMessageProps) {
  if (!validation) return null;

  if (validation.is_valid && !validation.is_ambiguous) {
    // Valid input
    return (
      <div className="flex items-start gap-3 p-4 bg-green-50 border border-success rounded-lg">
        <span className="text-success text-xl flex-shrink-0">✓</span>
        <div className="flex-1">
          <p className="text-sm font-medium text-success">{validation.message}</p>
          {validation.formatted_value && validation.what_was_entered && validation.formatted_value !== validation.what_was_entered && (
            <p className="text-xs text-secondary-600 mt-2">
              Formatted: <span className="font-semibold text-secondary-800">{validation.formatted_value}</span>
            </p>
          )}
        </div>
      </div>
    );
  }

  if (validation.is_ambiguous) {
    // Needs clarification
    return (
      <div className="space-y-3 p-4 bg-warning bg-opacity-10 border border-warning rounded-lg">
        <div className="flex items-start gap-3">
          <span className="text-warning text-xl flex-shrink-0">⚠️</span>
          <div className="flex-1">
            <p className="text-sm font-medium text-secondary-900">{validation.message}</p>
            {validation.clarification_needed && (
              <p className="text-sm text-secondary-700 mt-2">{validation.clarification_needed}</p>
            )}
          </div>
        </div>

        {onAccept && onReject && (
          <div className="flex gap-2 mt-3">
            <button
              onClick={onAccept}
              disabled={isLoading}
              className="px-3 py-2 bg-primary-500 hover:bg-primary-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Continue
            </button>
            <button
              onClick={onReject}
              disabled={isLoading}
              className="px-3 py-2 border border-secondary-300 hover:bg-secondary-50 disabled:opacity-50 text-secondary-700 rounded-lg text-sm font-medium transition-colors"
            >
              Edit
            </button>
          </div>
        )}
      </div>
    );
  }

  // Invalid input - with rich feedback
  return (
    <div className="space-y-3 p-4 bg-red-50 border border-error rounded-lg">
      {/* Main message */}
      <div className="flex items-start gap-3">
        <span className="text-error text-xl flex-shrink-0">✕</span>
        <div className="flex-1">
          <p className="text-sm font-medium text-error">{validation.message}</p>
        </div>
      </div>

      {/* Details section */}
      <div className="space-y-2 ml-8 border-l-2 border-error border-opacity-30 pl-3">
        {/* What was entered */}
        {validation.what_was_entered && (
          <div className="text-xs">
            <span className="text-secondary-600">You entered:</span>{' '}
            <code className="bg-red-100 text-red-900 px-2 py-1 rounded font-medium">
              {validation.what_was_entered}
            </code>
          </div>
        )}

        {/* What's expected */}
        {validation.what_expected && (
          <div className="text-xs">
            <span className="text-secondary-600">We need:</span>{' '}
            <span className="text-secondary-800">{validation.what_expected}</span>
          </div>
        )}

        {/* Suggestion for correction */}
        {validation.suggestion && (
          <div className="text-xs">
            <span className="text-secondary-600 font-medium">💡 Suggestion:</span>{' '}
            <span className="text-secondary-800 italic">{validation.suggestion}</span>
          </div>
        )}

        {/* Example of correct format */}
        {validation.example && (
          <div className="text-xs">
            <span className="text-secondary-600">Example:</span>{' '}
            <code className="bg-green-50 text-green-900 px-2 py-1 rounded font-medium">
              {validation.example}
            </code>
          </div>
        )}
      </div>

      {/* Confidence indicator for debugging */}
      <div className="text-xs text-secondary-500 text-right">
        Confidence: {(validation.confidence * 100).toFixed(0)}%
      </div>
    </div>
  );
}
