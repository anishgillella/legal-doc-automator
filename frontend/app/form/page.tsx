'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import { FormField } from '@/components/FormField';
import { ProgressBar } from '@/components/ProgressBar';
import { useFormContext } from '@/context/FormContext';

export default function FormPage() {
  const router = useRouter();
  const { state, setValue, nextField, previousField, getCurrentField } = useFormContext();
  const [error, setError] = useState<string | undefined>(undefined);

  // Redirect if no placeholders
  useEffect(() => {
    if (state.placeholders.length === 0) {
      router.push('/');
    }
  }, [state.placeholders, router]);

  const currentField = getCurrentField();
  const currentValue = currentField ? state.values[currentField.placeholder_id || currentField.placeholder_text] || '' : '';

  const handleNext = () => {
    if (!currentField) return;

    // Validate that field is filled if required
    if (currentField.required && !currentValue.trim()) {
      setError('This field is required');
      return;
    }

    setError(undefined);

    if (state.currentFieldIndex < state.placeholders.length - 1) {
      nextField();
    } else {
      // All fields filled, go to review
      router.push('/review');
    }
  };

  const handlePrevious = () => {
    setError(undefined);
    previousField();
  };

  const handleChange = (value: string) => {
    if (!currentField) return;
    setValue(currentField.placeholder_id || currentField.placeholder_text, value);
    setError(undefined);
  };

  const progressPercent = Math.round(
    ((state.currentFieldIndex + 1) / state.placeholders.length) * 100
  );

  return (
    <>
      <Header title="Fill Your Document" showHome />

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl space-y-8">
          {/* Progress Section */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-secondary-900">
                Question {state.currentFieldIndex + 1} of {state.placeholders.length}
              </h2>
              <span className="text-sm font-semibold text-primary-600">{progressPercent}% Complete</span>
            </div>
            <ProgressBar
              current={state.currentFieldIndex + 1}
              total={state.placeholders.length}
              label="Overall Progress"
            />
          </div>

          {/* Form Field */}
          <div className="bg-white rounded-xl border border-secondary-200 shadow-md p-8 space-y-6">
            {currentField ? (
              <>
                <FormField
                  field={currentField}
                  value={currentValue}
                  onChange={handleChange}
                  error={error}
                  isLoading={state.isLoading}
                  onSubmit={handleNext}
                />
              </>
            ) : (
              <p className="text-center text-secondary-600">Loading question...</p>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex gap-4 justify-between">
            <button
              onClick={handlePrevious}
              disabled={state.currentFieldIndex === 0 || state.isLoading}
              className={`
                px-6 py-3 border-2 font-medium rounded-lg transition-all
                ${
                  state.currentFieldIndex === 0 || state.isLoading
                    ? 'border-secondary-200 text-secondary-400 cursor-not-allowed'
                    : 'border-secondary-300 text-secondary-700 hover:border-primary-500 hover:text-primary-600'
                }
              `}
            >
              ← Previous
            </button>

            <button
              onClick={handleNext}
              disabled={state.isLoading}
              className={`
                px-8 py-3 font-medium rounded-lg transition-all flex items-center gap-2
                ${
                  state.isLoading
                    ? 'bg-primary-300 text-white cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800'
                }
              `}
            >
              {state.currentFieldIndex === state.placeholders.length - 1 ? (
                <>
                  Review & Download →
                </>
              ) : (
                <>
                  Next →
                </>
              )}
            </button>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4 text-sm text-secondary-600">
            <div className="bg-primary-50 rounded-lg p-3 border border-primary-200">
              <p className="font-medium text-primary-900">Filled Fields</p>
              <p className="text-lg font-bold text-primary-600">
                {Object.keys(state.values).length} / {state.placeholders.length}
              </p>
            </div>
            <div className="bg-secondary-100 rounded-lg p-3 border border-secondary-200">
              <p className="font-medium text-secondary-900">Current Field Type</p>
              <p className="text-lg font-bold text-secondary-700 capitalize">
                {currentField?.data_type || '—'}
              </p>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
