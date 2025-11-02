/**
 * useFormState Hook - Manages form state across all pages
 * Stores: file, placeholders, values, current field
 */

import { useState, useCallback } from 'react';
import { FormState, PlaceholderAnalysis } from '@/types/index';

export function useFormState() {
  const [state, setState] = useState<FormState>({
    file: null,
    placeholders: [],
    values: {},
    currentFieldIndex: 0,
    isLoading: false,
    error: null,
  });

  const setFile = useCallback((file: File | null) => {
    setState(prev => ({ ...prev, file }));
  }, []);

  const setPlaceholders = useCallback((placeholders: PlaceholderAnalysis[]) => {
    setState(prev => ({ ...prev, placeholders }));
  }, []);

  const setValue = useCallback((fieldName: string, value: string) => {
    setState(prev => ({
      ...prev,
      values: { ...prev.values, [fieldName]: value }
    }));
  }, []);

  const nextField = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentFieldIndex: Math.min(prev.currentFieldIndex + 1, prev.placeholders.length - 1)
    }));
  }, []);

  const previousField = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentFieldIndex: Math.max(prev.currentFieldIndex - 1, 0)
    }));
  }, []);

  const setLoading = useCallback((isLoading: boolean) => {
    setState(prev => ({ ...prev, isLoading }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error }));
  }, []);

  const reset = useCallback(() => {
    setState({
      file: null,
      placeholders: [],
      values: {},
      currentFieldIndex: 0,
      isLoading: false,
      error: null,
    });
  }, []);

  const getCurrentField = useCallback(() => {
    return state.placeholders[state.currentFieldIndex] || null;
  }, [state.placeholders, state.currentFieldIndex]);

  const isAllFieldsFilled = useCallback(() => {
    return state.placeholders.every(p => state.values[p.placeholder_text]);
  }, [state.placeholders, state.values]);

  return {
    state,
    setFile,
    setPlaceholders,
    setValue,
    nextField,
    previousField,
    setLoading,
    setError,
    reset,
    getCurrentField,
    isAllFieldsFilled,
  };
}
