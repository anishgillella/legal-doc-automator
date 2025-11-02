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
          {validation.formatted_value !== validation.formatted_value && (
            <p className="text-xs text-secondary-600 mt-1">
              Formatted to: <span className="font-semibold">{validation.formatted_value}</span>
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

  // Invalid input
  return (
    <div className="flex items-start gap-3 p-4 bg-red-50 border border-error rounded-lg">
      <span className="text-error text-xl flex-shrink-0">✕</span>
      <div className="flex-1">
        <p className="text-sm font-medium text-error">{validation.message}</p>
        <p className="text-xs text-secondary-600 mt-1">Confidence: {(validation.confidence * 100).toFixed(0)}%</p>
      </div>
    </div>
  );
}
