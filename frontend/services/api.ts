/**
 * API Service - Handles all backend communication
 * Production-ready with error handling and type safety
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { ProcessResponse, FillResponse } from '@/types/index';

class APIService {
  private api: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';

    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: 120000, // 2 minutes for large document processing
    });

    // Error interceptor
    this.api.interceptors.response.use(
      response => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message);
        throw new Error(
          (error.response?.data as any)?.error || 
          error.message || 
          'An error occurred'
        );
      }
    );
  }

  /**
   * Upload and process document
   * Detects placeholders and analyzes with LLM
   */
  async processDocument(file: File): Promise<ProcessResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await this.api.post<ProcessResponse>(
        '/api/process',
        formData
      );
      return response.data;
    } catch (error) {
      console.error('Failed to process document:', error);
      throw error;
    }
  }

  /**
   * Get placeholders only (fast, no LLM analysis)
   */
  async getPlaceholders(file: File): Promise<ProcessResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await this.api.post<ProcessResponse>(
        '/api/placeholders',
        formData
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get placeholders:', error);
      throw error;
    }
  }

  /**
   * Fill placeholders and generate completed document
   */
  async fillDocument(
    file: File,
    values: Record<string, string>
  ): Promise<Blob> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('values', JSON.stringify(values));

    try {
      const response = await this.api.post(
        '/api/fill',
        formData,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fill document:', error);
      throw error;
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.api.get('/api/health');
      return true;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  /**
   * Validate user input using LLM
   */
  async validateInput(
    userInput: string,
    fieldType: string,
    fieldName: string,
    placeholderName?: string
  ): Promise<ValidationResponse> {
    try {
      const response = await this.api.post<ValidationResponse>(
        '/api/validate',
        {
          user_input: userInput,
          field_type: fieldType,
          field_name: fieldName,
          placeholder_name: placeholderName || fieldName
        }
      );
      return response.data;
    } catch (error) {
      console.error('Validation failed:', error);
      throw error;
    }
  }

  /**
   * Validate multiple fields in parallel (batch)
   */
  async validateBatch(
    validations: Array<{
      field: string;
      value: string;
      type: string;
      name: string;
    }>
  ): Promise<ValidationResponse[]> {
    try {
      const response = await this.api.post<{ results: ValidationResponse[] }>(
        '/api/validate-batch',
        { validations }
      );
      return response.data.results;
    } catch (error) {
      console.error('Batch validation failed:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const apiService = new APIService();
