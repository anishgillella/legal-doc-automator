'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import { useFormContext } from '@/context/FormContext';
import { apiService } from '@/services/api';

export default function ReviewPage() {
  const router = useRouter();
  const { state, reset } = useFormContext();
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  // Redirect if no file
  useEffect(() => {
    if (!state.file || state.placeholders.length === 0) {
      router.push('/');
    }
  }, [state.file, state.placeholders, router]);

  const handleDownload = async () => {
    if (!state.file) return;

    try {
      setIsDownloading(true);
      setDownloadError(null);

      // Map values - send both ID-based and text-based for flexibility
      const valuesForBackend: Record<string, string> = {};
      state.placeholders.forEach((p, idx) => {
        const key = p.placeholder_id || p.placeholder_text;
        const value = state.values[key];
        if (value) {
          // Send with placeholder_text as key (original format)
          valuesForBackend[p.placeholder_text] = value;
          // Also send with position-based key for duplicates
          valuesForBackend[`${p.placeholder_text}__pos_${idx}`] = value;
        }
      });

      // Call backend to fill document
      const blob = await apiService.fillDocument(state.file, valuesForBackend);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${state.file.name.replace('.docx', '')}_filled.docx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to download document';
      setDownloadError(errorMessage);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleStartOver = () => {
    reset();
    router.push('/');
  };

  const filledCount = Object.keys(state.values).length;
  const totalCount = state.placeholders.length;

  return (
    <>
      <Header title="Review & Download" showHome />

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl space-y-8">
          {/* Success Header */}
          <div className="text-center space-y-3">
            <div className="text-6xl animate-bounce">✨</div>
            <h1 className="text-4xl font-bold text-secondary-900">All Set!</h1>
            <p className="text-lg text-secondary-600">
              Your document is ready to download with all fields filled in.
            </p>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-lg border border-secondary-200 shadow-md p-4 text-center">
              <p className="text-3xl font-bold text-primary-600">{totalCount}</p>
              <p className="text-sm text-secondary-600 mt-1">Total Fields</p>
            </div>
            <div className="bg-white rounded-lg border border-secondary-200 shadow-md p-4 text-center">
              <p className="text-3xl font-bold text-success">{filledCount}</p>
              <p className="text-sm text-secondary-600 mt-1">Completed</p>
            </div>
            <div className="bg-white rounded-lg border border-secondary-200 shadow-md p-4 text-center">
              <p className="text-3xl font-bold text-primary-600">
                {Math.round((filledCount / totalCount) * 100)}%
              </p>
              <p className="text-sm text-secondary-600 mt-1">Complete</p>
            </div>
          </div>

          {/* Filled Values Summary */}
          <div className="bg-white rounded-lg border border-secondary-200 shadow-md p-8 space-y-4">
            <h2 className="text-xl font-bold text-secondary-900">Filled Information</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {state.placeholders.map((placeholder) => (
                <div key={placeholder.placeholder_id || placeholder.placeholder_text} className="flex items-start justify-between py-2 border-b border-secondary-100 last:border-b-0">
                  <div>
                    <p className="font-medium text-secondary-900">{placeholder.suggested_question}</p>
                    <p className="text-xs text-secondary-500 mt-1">{placeholder.placeholder_name}</p>
                  </div>
                  <p className="text-secondary-700 font-medium text-right max-w-xs break-words">
                    {state.values[placeholder.placeholder_id || placeholder.placeholder_text] || '—'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Error Message */}
          {downloadError && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-error rounded-lg">
              <span className="text-error text-xl flex-shrink-0">✕</span>
              <div>
                <p className="text-sm font-medium text-error">Download Error</p>
                <p className="text-sm text-secondary-700 mt-1">{downloadError}</p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              onClick={handleDownload}
              disabled={isDownloading}
              className={`
                flex-1 px-6 py-4 font-bold rounded-lg transition-all text-lg
                flex items-center justify-center gap-2
                ${
                  isDownloading
                    ? 'bg-primary-300 text-white cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800'
                }
              `}
            >
              {isDownloading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Preparing...
                </>
              ) : (
                <>
                  📥 Download Document
                </>
              )}
            </button>

            <button
              onClick={handleStartOver}
              disabled={isDownloading}
              className="px-6 py-4 border-2 border-secondary-300 text-secondary-700 font-bold rounded-lg hover:border-primary-500 hover:text-primary-600 transition-all disabled:opacity-50"
            >
              Start Over
            </button>
          </div>

          {/* Info Box */}
          <div className="bg-primary-50 border border-primary-200 rounded-lg p-6 text-center">
            <p className="text-sm text-secondary-700">
              <span className="font-semibold">File Name:</span> {state.file?.name}
            </p>
            <p className="text-sm text-secondary-600 mt-2">
              Your completed document will download with all placeholders replaced.
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
