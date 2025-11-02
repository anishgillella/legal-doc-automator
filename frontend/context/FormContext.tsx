'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { FormState, PlaceholderAnalysis } from '@/types/index';

interface FormContextType {
  state: FormState;
  setFile: (file: File | null) => void;
  setPlaceholders: (placeholders: PlaceholderAnalysis[]) => void;
  setValue: (fieldName: string, value: string) => void;
  nextField: () => void;
  previousField: () => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
  getCurrentField: () => PlaceholderAnalysis | null;
  isAllFieldsFilled: () => boolean;
}

const FormContext = createContext<FormContextType | undefined>(undefined);

export function FormProvider({ children }: { children: React.ReactNode }) {
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

  const setValue = useCallback((fieldId: string, value: string) => {
    setState(prev => ({
      ...prev,
      values: { ...prev.values, [fieldId]: value }
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
    return state.placeholders.every(p => state.values[p.placeholder_id || p.placeholder_text]);
  }, [state.placeholders, state.values]);

  const value: FormContextType = {
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

  return (
    <FormContext.Provider value={value}>
      {children}
    </FormContext.Provider>
  );
}

export function useFormContext() {
  const context = useContext(FormContext);
  if (!context) {
    throw new Error('useFormContext must be used within FormProvider');
  }
  return context;
}
