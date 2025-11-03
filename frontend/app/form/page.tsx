'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Header } from '@/components/Header';
import { FormField } from '@/components/FormField';
import { ProgressBar } from '@/components/ProgressBar';
import { useFormContext } from '@/context/FormContext';
import { apiService } from '@/services/api';
import { PlaceholderAnalysis } from '@/types/index';

interface BatchValidationResult {
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

interface FieldState {
  validationResult: BatchValidationResult | null;
  awaitingConfirmation: boolean;
  retryCount: number;
  lastErrorMessage: string | null;
}

interface FormState {
  isValidating: boolean;
  validationResults: Record<string, BatchValidationResult>;
  fieldStates: Record<string, FieldState>;
  hasIssues: boolean;
}

export default function FormPage() {
  const router = useRouter();
  const { state, setValue } = useFormContext();
  const [formState, setFormState] = useState<FormState>({
    isValidating: false,
    validationResults: {},
    fieldStates: {},
    hasIssues: false,
  });

  // Redirect if no placeholders
  useEffect(() => {
    if (state.placeholders.length === 0) {
      router.push('/');
    }
  }, [state.placeholders, router]);

  const handleFieldChange = (fieldId: string, value: string) => {
    setValue(fieldId, value);
    // Clear validation for this field when user edits it
        setFormState(prev => ({ 
          ...prev, 
      fieldStates: {
        ...prev.fieldStates,
        [fieldId]: {
          validationResult: null,
          awaitingConfirmation: false,
          retryCount: 0,
          lastErrorMessage: null,
        },
      },
    }));
  };

  const handleAcceptFormatted = (fieldId: string) => {
    const fieldState = formState.fieldStates[fieldId];
    if (fieldState?.validationResult?.formatted_value) {
      setValue(fieldId, fieldState.validationResult.formatted_value);
        setFormState(prev => ({ 
          ...prev, 
        fieldStates: {
          ...prev.fieldStates,
          [fieldId]: {
            validationResult: fieldState.validationResult,
            awaitingConfirmation: false,
            retryCount: 0,
            lastErrorMessage: null,
          },
        },
      }));
    }
  };

  const handleRejectFormatted = (fieldId: string) => {
    setFormState(prev => ({ 
      ...prev, 
      fieldStates: {
        ...prev.fieldStates,
        [fieldId]: {
          validationResult: null,
          awaitingConfirmation: false,
          retryCount: 0,
          lastErrorMessage: null,
        },
      },
    }));
  };

  const handleValidateAndSubmit = async () => {
    // Check for required empty fields first
    const missingRequired = state.placeholders.filter(
      field => field.required && !state.values[field.placeholder_id || field.placeholder_text]?.trim()
    );

    if (missingRequired.length > 0) {
    setFormState(prev => ({ 
      ...prev, 
        hasIssues: true,
      }));
      return;
    }

    // Prepare batch validation request - ONLY validate fields that have values
    // Skip optional empty fields
    const validationsToRun = state.placeholders
      .filter(field => {
        const fieldValue = state.values[field.placeholder_id || field.placeholder_text]?.trim();
        // Include if: has a value, OR is required (even if empty)
        return fieldValue || field.required;
      })
      .map(field => ({
        field: field.placeholder_id || field.placeholder_text,
        value: state.values[field.placeholder_id || field.placeholder_text] || '',
        type: field.data_type,
        name: field.placeholder_name,
      }));

    setFormState(prev => ({ 
      ...prev, 
      isValidating: true,
      fieldStates: {},
      hasIssues: false,
    }));

    try {
      const results = await apiService.validateBatch(validationsToRun);

      // Organize results by field and update field states
      const resultsByField: Record<string, BatchValidationResult> = {};
      const fieldStates: Record<string, FieldState> = {};
      let hasIssues = false;

      results.forEach(result => {
        resultsByField[result.field] = result;
        
        if (!result.is_valid) {
          hasIssues = true;
          
          // Get previous state for this field
          const prevFieldState = formState.fieldStates[result.field];
          const isSameError = prevFieldState?.lastErrorMessage === result.message;
          const updatedRetryCount = isSameError ? (prevFieldState?.retryCount || 0) + 1 : 1;
          
          // Check if user has seen this error 3+ times - auto-accept
          if (updatedRetryCount >= 3) {
            // Auto-accept: treat as valid after 3 identical errors
            fieldStates[result.field] = {
              validationResult: {
                ...result,
                is_valid: true, // Force valid after 3 retries
              },
              awaitingConfirmation: false,
              retryCount: updatedRetryCount,
              lastErrorMessage: result.message,
            };
            hasIssues = false; // Remove from issues count
          } else {
            // Check if we should show formatted value confirmation
            const shouldConfirm = !!(result.formatted_value && 
                                 result.formatted_value !== state.values[result.field] &&
                                 result.confidence >= 0.6);
            
            fieldStates[result.field] = {
              validationResult: result,
              awaitingConfirmation: shouldConfirm,
              retryCount: updatedRetryCount,
              lastErrorMessage: result.message,
            };
          }
        } else {
          fieldStates[result.field] = {
            validationResult: result,
            awaitingConfirmation: false,
      retryCount: 0,
            lastErrorMessage: null,
          };
        }
      });

      setFormState(prev => ({
        ...prev,
        isValidating: false,
        validationResults: resultsByField,
        fieldStates: fieldStates,
        hasIssues: hasIssues,
      }));

      // If all valid, proceed
      if (!hasIssues) {
        results.forEach(result => {
          if (result.formatted_value !== state.values[result.field]) {
            setValue(result.field, result.formatted_value);
          }
        });
        // Navigate to review page after a short delay
        setTimeout(() => {
      router.push('/review');
        }, 500);
      }
    } catch (error) {
      setFormState(prev => ({
        ...prev,
      isValidating: false,
        hasIssues: true,
      }));
      console.error('Batch validation failed:', error);
    }
  };

  const filledCount = Object.keys(state.values).filter(k => state.values[k]?.trim()).length;
  const progressPercent = Math.round((filledCount / state.placeholders.length) * 100);

  // Count issues (invalid fields)
  const issueCount = Object.values(formState.fieldStates).filter(fs => 
    fs.validationResult && !fs.validationResult.is_valid
  ).length;

  return (
    <>
      <Header title="LexAI" />

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-4xl space-y-8">
          {/* Progress Section */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-secondary-900">
                Complete the Form
              </h2>
              <span className="text-sm font-semibold text-primary-600">{progressPercent}% Complete</span>
            </div>
            <ProgressBar
              current={filledCount}
              total={state.placeholders.length}
              label="Overall Progress"
            />
          </div>

          {/* Status Alert */}
          {formState.hasIssues && issueCount > 0 && !formState.isValidating && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="p-4 bg-amber-50 border-2 border-amber-200 rounded-lg"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl flex-shrink-0">⚡</span>
                <div className="flex-1">
                  <p className="font-semibold text-amber-900">
                    {issueCount} {issueCount === 1 ? 'field needs attention' : 'fields need attention'}
                    </p>
                  <p className="text-sm text-amber-800 mt-1">
                    Review the highlighted fields below to fix any issues
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Form Fields Grid */}
          <div className="bg-white rounded-xl border border-secondary-200 shadow-md p-8 space-y-6">
            {state.placeholders.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {state.placeholders.map((field, idx) => {
                  const fieldId = field.placeholder_id || field.placeholder_text;
                  const value = state.values[fieldId] || '';
                  const fieldState = formState.fieldStates[fieldId];
                  const validationResult = fieldState?.validationResult;
                  const isAwaitingConfirmation = fieldState?.awaitingConfirmation;
                  const isValid = validationResult?.is_valid;
                  const hasError = validationResult && !validationResult.is_valid;

                  return (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, delay: idx * 0.05 }}
                      className="space-y-3"
                    >
                      {/* Field Input */}
                      <motion.div
                        className={`space-y-2 p-4 rounded-lg border-2 transition-all ${
                          hasError && !isAwaitingConfirmation
                            ? 'border-red-300 bg-red-50'
                            : isAwaitingConfirmation
                            ? 'border-blue-300 bg-blue-50'
                            : isValid
                            ? 'border-green-300 bg-green-50'
                            : 'border-secondary-200 bg-white'
                        }`}
                        animate={{
                          borderColor: hasError && !isAwaitingConfirmation
                            ? '#fca5a5'
                            : isAwaitingConfirmation
                            ? '#93c5fd'
                            : isValid
                            ? '#86efac'
                            : '#e5e7eb',
                        }}
                        transition={{ duration: 0.3 }}
                      >
                        <FormField
                          field={field}
                          value={value}
                          onChange={(newValue) => handleFieldChange(fieldId, newValue)}
                          error={undefined}
                          isLoading={false}
                          onSubmit={() => {}}
                        />
                      </motion.div>

                      {/* Validation Feedback */}
                      {validationResult && !isAwaitingConfirmation && (
                        <motion.div
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          transition={{ duration: 0.3 }}
                          className={`p-3 rounded-lg border space-y-2 text-sm ${
                            isValid
                              ? 'bg-green-50 border-green-200'
                              : 'bg-red-50 border-red-200'
                          }`}
                        >
                          {/* Status line */}
                          <div className="flex items-start gap-2">
                            <motion.span
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              transition={{ duration: 0.3, type: 'spring' }}
                              className="text-lg flex-shrink-0"
                            >
                              {isValid ? '✓' : '⚠️'}
                            </motion.span>
                            <div className="flex-1">
                              <p className={`font-medium ${
                                isValid ? 'text-green-900' : 'text-red-900'
                              }`}>
                                {validationResult.message}
                              </p>
                              {fieldState?.retryCount && fieldState.retryCount >= 3 && isValid && (
                                <p className="text-xs text-green-700 mt-1 italic">
                                  ✓ You've confirmed this entry. Moving forward with your input.
                                </p>
                              )}
              </div>
            </div>

                          {/* Details for invalid fields */}
                          {hasError && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              transition={{ duration: 0.3 }}
                              className="space-y-2 ml-6 border-l-2 border-red-200 pl-3"
                            >
                              {validationResult.what_expected && (
                                <div className="text-xs text-red-800">
                                  <span className="font-medium">We need:</span> {validationResult.what_expected}
                                </div>
                              )}
                              {validationResult.suggestion && (
                                <div className="text-xs text-red-800">
                                  <span className="font-medium">💡 Suggestion:</span> {validationResult.suggestion}
                                </div>
                              )}
                              {fieldState?.retryCount && fieldState.retryCount < 3 && (
                                <div className="text-xs text-red-700 mt-2 pt-2 border-t border-red-200">
                                  <span className="font-medium">Attempt {fieldState.retryCount}/3</span> - 
                                  {fieldState.retryCount < 3 ? ' Try again or it will auto-accept' : ' Auto-accepting your entry'}
                                </div>
                              )}
                            </motion.div>
                          )}
                        </motion.div>
                      )}

                      {/* Formatted Value Confirmation */}
                      {isAwaitingConfirmation && validationResult && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.95 }}
                          transition={{ duration: 0.3, type: 'spring', stiffness: 300 }}
                          className="p-3 bg-blue-50 border-2 border-blue-300 rounded-lg space-y-3"
                        >
                          <div className="flex items-start gap-2">
                            <motion.span
                              animate={{ rotate: [0, 5, -5, 0] }}
                              transition={{ duration: 2, repeat: Infinity }}
                              className="text-lg flex-shrink-0"
                            >
                              ✏️
                            </motion.span>
                            <div className="flex-1">
                              <p className="font-medium text-blue-900 text-sm">We can auto-format this</p>
                              <p className="text-xs text-blue-800 mt-1">{validationResult.message}</p>
                            </div>
                          </div>

                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.4, delay: 0.1 }}
                            className="space-y-2 ml-6 border-l-2 border-blue-300 pl-3 text-xs"
                          >
                            <div className="text-blue-800">
                              <span className="font-medium">You entered:</span>
                              <br />
                              <code className="bg-blue-100 px-2 py-1 rounded inline-block mt-1">
                                {validationResult.what_was_entered}
                              </code>
                            </div>
                            <div className="text-blue-800">
                              <span className="font-medium">Format it as:</span>
                              <br />
                              <code className="bg-green-100 px-2 py-1 rounded inline-block mt-1 font-semibold">
                                {validationResult.formatted_value}
                              </code>
                            </div>
                            {validationResult.suggestion && (
                              <div className="text-blue-800">
                                <span className="font-medium">💡</span> {validationResult.suggestion}
                              </div>
                            )}
                          </motion.div>

                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.4, delay: 0.2 }}
                            className="flex gap-2 pt-2"
                          >
                            <motion.button
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              onClick={() => handleAcceptFormatted(fieldId)}
                              className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded transition-colors"
                            >
                              ✓ Accept
                            </motion.button>
                            <motion.button
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              onClick={() => handleRejectFormatted(fieldId)}
                              className="flex-1 px-3 py-2 border border-blue-300 hover:bg-blue-100 text-blue-700 text-xs font-medium rounded transition-colors"
                >
                              ✎ Edit
                            </motion.button>
                          </motion.div>
                        </motion.div>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            ) : (
              <p className="text-center text-secondary-600">Loading fields...</p>
            )}
            </div>

          {/* Action Buttons */}
          <div className="flex gap-4 justify-between">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push('/')}
              disabled={formState.isValidating}
              className={`
                px-6 py-3 border-2 font-medium rounded-lg transition-all
                ${
                  formState.isValidating
                    ? 'border-secondary-200 text-secondary-400 cursor-not-allowed'
                    : 'border-secondary-300 text-secondary-700 hover:border-primary-500 hover:text-primary-600'
                }
              `}
            >
              ← Back to Upload
            </motion.button>

            <motion.button
              whileHover={{ scale: formState.isValidating || state.placeholders.length === 0 ? 1 : 1.02 }}
              whileTap={{ scale: formState.isValidating || state.placeholders.length === 0 ? 1 : 0.98 }}
              onClick={handleValidateAndSubmit}
              disabled={formState.isValidating || state.placeholders.length === 0}
              className={`
                px-8 py-3 font-medium rounded-lg transition-all flex items-center gap-2
                ${
                  formState.isValidating || state.placeholders.length === 0
                    ? 'bg-primary-300 text-white cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800'
                }
              `}
            >
              {formState.isValidating ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                  />
                  Validating {state.placeholders.length} fields...
                </>
              ) : (
                <>
                  Review & Download →
                </>
              )}
            </motion.button>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-4 text-sm text-secondary-600">
            <div className="bg-primary-50 rounded-lg p-3 border border-primary-200">
              <p className="font-medium text-primary-900">Total Fields</p>
              <p className="text-lg font-bold text-primary-600">{state.placeholders.length}</p>
            </div>
            <div className="bg-secondary-100 rounded-lg p-3 border border-secondary-200">
              <p className="font-medium text-secondary-900">Filled</p>
              <p className="text-lg font-bold text-secondary-700">{filledCount}</p>
            </div>
            <div className="bg-warning bg-opacity-10 rounded-lg p-3 border border-warning">
              <p className="font-medium text-warning">Remaining</p>
              <p className="text-lg font-bold text-warning">{state.placeholders.length - filledCount}</p>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
