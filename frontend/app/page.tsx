'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/Header';
import { UploadZone } from '@/components/UploadZone';
import { apiService } from '@/services/api';
import { useFormContext } from '@/context/FormContext';

export default function Home() {
  const router = useRouter();
  const { setFile, setPlaceholders, setLoading, state } = useFormContext();
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    // Check backend health on mount
    checkBackendHealth();
  }, []);

  const checkBackendHealth = async () => {
    try {
      const isHealthy = await apiService.healthCheck();
      if (!isHealthy) {
        setLocalError('Backend service is not available. Please make sure it\'s running.');
      }
    } catch (error) {
      setLocalError('Cannot connect to backend. Please check the server.');
    }
  };

  const handleFileSelect = async (file: File) => {
    try {
      setLocalError(null);
      setLoading(true);
      setFile(file);

      // Process the document
      const response = await apiService.processDocument(file);

      if (!response.success) {
        throw new Error(response.placeholders ? 'Failed to process document' : 'Invalid document');
      }

      // Store placeholders
      setPlaceholders(response.analyses || []);

      // Set loading to false before navigating
      setLoading(false);

      // Redirect to form
      router.push('/form');
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to process document. Please try again.';
      setLocalError(errorMessage);
      setLoading(false);
    }
  };

  return (
    <>
      <Header title="Upload Your Document" />

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl space-y-8">
          {/* Title Section */}
          <div className="text-center space-y-2">
            <h1 className="text-4xl font-bold text-secondary-900">
              Ready to Fill Your Document?
            </h1>
            <p className="text-lg text-secondary-600">
              Upload a .docx file and we'll help you fill in all the fields with AI-powered suggestions.
            </p>
          </div>

          {/* Error Message */}
          {localError && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-error rounded-lg">
              <span className="text-error text-xl flex-shrink-0">✕</span>
              <div>
                <p className="text-sm font-medium text-error">Error</p>
                <p className="text-sm text-secondary-700 mt-1">{localError}</p>
              </div>
            </div>
          )}

          {/* Upload Zone */}
          <UploadZone onFileSelect={handleFileSelect} isLoading={state.isLoading} />

          {/* Info Cards */}
          <div className="grid grid-cols-3 gap-4 mt-12">
            <div className="p-4 bg-white rounded-lg border border-secondary-200 shadow-subtle">
              <div className="text-2xl mb-2">📄</div>
              <h3 className="font-semibold text-secondary-900 mb-1">Smart Detection</h3>
              <p className="text-xs text-secondary-600">
                We automatically find and analyze all placeholders in your document.
              </p>
            </div>

            <div className="p-4 bg-white rounded-lg border border-secondary-200 shadow-subtle">
              <div className="text-2xl mb-2">🤖</div>
              <h3 className="font-semibold text-secondary-900 mb-1">AI Suggestions</h3>
              <p className="text-xs text-secondary-600">
                Get intelligent suggestions tailored to each field's context.
              </p>
            </div>

            <div className="p-4 bg-white rounded-lg border border-secondary-200 shadow-subtle">
              <div className="text-2xl mb-2">⚡</div>
              <h3 className="font-semibold text-secondary-900 mb-1">Quick & Easy</h3>
              <p className="text-xs text-secondary-600">
                Fill all your fields in minutes with our conversational interface.
              </p>
            </div>
          </div>

          {/* Footer Info */}
          <div className="bg-primary-50 border border-primary-200 rounded-lg p-6 text-center">
            <p className="text-sm text-secondary-700">
              <span className="font-semibold">Secure & Private:</span> Your documents are processed locally
              and never stored on our servers.
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
