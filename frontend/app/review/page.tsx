'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
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
    if (!state.file) {
      setDownloadError('No file found. Please start over.');
      return;
    }

    try {
      setIsDownloading(true);
      setDownloadError(null);

      console.log('Starting download with file:', state.file.name);
      console.log('Total values to fill:', Object.keys(state.values).length);

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

      console.log('Values being sent to backend:', Object.keys(valuesForBackend).length);

      // Call backend to fill document
      const blob = await apiService.fillDocument(state.file, valuesForBackend);
      
      console.log('Received blob:', blob.size, 'bytes');

      if (!blob || blob.size === 0) {
        throw new Error('Downloaded file is empty');
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${state.file.name.replace('.docx', '')}_filled.docx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      console.log('Download completed successfully');
    } catch (error) {
      console.error('Download error:', error);
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

  const filledCount = Object.keys(state.values).filter(k => state.values[k]?.trim()).length;
  const totalCount = state.placeholders.length;

  return (
    <>
      <Header title="LexAI" />

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl space-y-8">
          {/* Success Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center space-y-3"
          >
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-6xl"
            >
              ✨
            </motion.div>
            <h1 className="text-4xl font-bold text-secondary-900">All Set!</h1>
            <p className="text-lg text-secondary-600">
              Your document is ready to download with all fields filled in.
            </p>
          </motion.div>

          {/* Summary Stats */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="grid grid-cols-3 gap-4"
          >
            {[
              { value: totalCount, label: 'Total Fields', color: 'primary' },
              { value: filledCount, label: 'Completed', color: 'success' },
              { value: `${Math.round((filledCount / totalCount) * 100)}%`, label: 'Complete', color: 'primary' },
            ].map((stat, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: 0.2 + idx * 0.1 }}
                className="bg-white rounded-lg border border-secondary-200 shadow-md p-4 text-center"
              >
                <p className={`text-3xl font-bold ${stat.color === 'primary' ? 'text-primary-600' : 'text-success'}`}>
                  {stat.value}
                </p>
                <p className="text-sm text-secondary-600 mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </motion.div>

          {/* Filled Values Summary */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="bg-white rounded-lg border border-secondary-200 shadow-md p-8 space-y-4"
          >
            <h2 className="text-xl font-bold text-secondary-900">Filled Information</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {state.placeholders.map((placeholder, idx) => (
                <motion.div
                  key={placeholder.placeholder_id || placeholder.placeholder_text}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.35 + idx * 0.02 }}
                  className="flex items-start justify-between py-2 border-b border-secondary-100 last:border-b-0"
                >
                  <div>
                    <p className="font-medium text-secondary-900">{placeholder.suggested_question}</p>
                    <p className="text-xs text-secondary-500 mt-1">{placeholder.placeholder_name}</p>
                  </div>
                  <p className="text-secondary-700 font-medium text-right max-w-xs break-words">
                    {state.values[placeholder.placeholder_id || placeholder.placeholder_text] || '—'}
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Error Message */}
          {downloadError && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-3 p-4 bg-red-50 border border-error rounded-lg"
            >
              <span className="text-error text-xl flex-shrink-0">✕</span>
              <div>
                <p className="text-sm font-medium text-error">Download Error</p>
                <p className="text-sm text-secondary-700 mt-1">{downloadError}</p>
              </div>
            </motion.div>
          )}

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="flex gap-4"
          >
            <motion.button
              whileHover={{ scale: isDownloading ? 1 : 1.02 }}
              whileTap={{ scale: isDownloading ? 1 : 0.98 }}
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
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                  />
                  Preparing...
                </>
              ) : (
                <>
                  📥 Download Document
                </>
              )}
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleStartOver}
              disabled={isDownloading}
              className="px-6 py-4 border-2 border-secondary-300 text-secondary-700 font-bold rounded-lg hover:border-primary-500 hover:text-primary-600 transition-all disabled:opacity-50"
            >
              Start Over
            </motion.button>
          </motion.div>

          {/* Info Box */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="bg-primary-50 border border-primary-200 rounded-lg p-6 text-center"
          >
            <p className="text-sm text-secondary-700">
              <span className="font-semibold">File Name:</span> {state.file?.name}
            </p>
            <p className="text-sm text-secondary-600 mt-2">
              Your completed document will download with all placeholders replaced.
            </p>
          </motion.div>
        </div>
      </main>
    </>
  );
}
