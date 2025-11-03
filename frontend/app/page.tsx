'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Header } from '@/components/Header';
import { UploadZone } from '@/components/UploadZone';
import { ThreeDBackground } from '@/components/ThreeDBackground';
import { ParsingLoader } from '@/components/ParsingLoader';
import { apiService } from '@/services/api';
import { useFormContext } from '@/context/FormContext';

export default function Home() {
  const router = useRouter();
  const { setFile, setPlaceholders, setLoading, reset, state } = useFormContext();
  const [localError, setLocalError] = useState<string | null>(null);
  const [parsingFileName, setParsingFileName] = useState<string | null>(null);
  const [noPlaceholders, setNoPlaceholders] = useState<{ message: string; file: File } | null>(null);

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
      setParsingFileName(file.name);
      
      // Reset form context to clear old values from previous upload
      reset();
      
      // Set new file
      setFile(file);

      // Process the document
      const response = await apiService.processDocument(file);

      if (!response.success) {
        throw new Error(response.placeholders ? 'Failed to process document' : 'Invalid document');
      }

      // Store placeholders
      const hasPlaceholders = response.analyses && response.analyses.length > 0;
      setPlaceholders(response.analyses || []);

      // Set loading to false
      setLoading(false);
      setParsingFileName(null);

      // Route based on placeholders
      if (hasPlaceholders) {
        setNoPlaceholders(null);
        router.push('/form');
      } else {
        // No placeholders - show message on home
        setNoPlaceholders({
          message: response.message || "Document processed - no fields to fill found.",
          file: file
        });
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to process document. Please try again.';
      setLocalError(errorMessage);
      setLoading(false);
      setParsingFileName(null);
    }
  };

  const handleUploadAnother = () => {
    setNoPlaceholders(null);
    reset();
  };

  const handleDownloadDocument = async () => {
    if (!noPlaceholders?.file) return;
    
    try {
      // For documents with no placeholders, we can still download them
      // (they're already complete as-is, or user can get original)
      const blob = new Blob([await noPlaceholders.file.arrayBuffer()], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = noPlaceholders.file.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download error:', error);
      setLocalError('Failed to download document. Please try again.');
    }
  };

  const NoPlaceholdersMessage = ({ 
    message, 
    fileName, 
    onUploadAnother,
    onDownload 
  }: {
    message: string;
    fileName: string;
    onUploadAnother: () => void;
    onDownload: () => void;
  }) => (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="w-full max-w-2xl mx-auto space-y-6"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl p-8 text-center"
      >
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-6xl mb-4"
        >
          ℹ️
        </motion.div>
        
        <h2 className="text-2xl font-bold text-blue-900 mb-3">
          Document Ready
        </h2>
        
        <p className="text-lg text-blue-800 mb-4">
          {message}
        </p>
        
        <div className="bg-white bg-opacity-60 rounded-lg p-4 mb-6 border border-blue-100">
          <p className="text-sm text-blue-700">
            <span className="font-semibold">File:</span> {fileName}
          </p>
        </div>

        <div className="space-y-3">
          <p className="text-sm text-blue-700 mb-4">
            Your document doesn't have any placeholder fields to fill. You can download the original document or upload another one to fill.
          </p>
        </div>
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="flex gap-4 justify-center"
      >
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onDownload}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-all flex items-center gap-2"
        >
          📥 Download Document
        </motion.button>
        
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onUploadAnother}
          className="px-6 py-3 border-2 border-blue-600 text-blue-600 hover:bg-blue-50 font-medium rounded-lg transition-all"
        >
          📤 Upload Another
        </motion.button>
      </motion.div>
    </motion.div>
  );

  return (
    <>
      <ThreeDBackground />
      <Header title="LexAI" />
      
      {/* Show loader while parsing */}
      {parsingFileName && <ParsingLoader fileName={parsingFileName} />}

      <main className="flex-1 flex items-center justify-center px-6 py-12 relative z-10">
        <div className="w-full max-w-3xl space-y-12">
          {/* Show no-placeholders message if applicable */}
          {noPlaceholders && (
            <NoPlaceholdersMessage
              message={noPlaceholders.message}
              fileName={noPlaceholders.file.name}
              onUploadAnother={handleUploadAnother}
              onDownload={handleDownloadDocument}
            />
          )}

          {!noPlaceholders && (
          <>
          {/* Hero Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center space-y-6"
          >
            <div className="space-y-2">
              <motion.h1
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-primary-700"
              >
                LexAI
              </motion.h1>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.3 }}
                className="text-2xl font-semibold text-secondary-900"
              >
                Intelligent Document Completion
              </motion.p>
          </div>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="text-lg text-secondary-600 max-w-2xl mx-auto leading-relaxed"
            >
              Transform your document workflows. Upload any legal or rental agreement, and let our AI-powered system intelligently fill in all required fields with smart suggestions and validation.
            </motion.p>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.5 }}
              className="flex flex-wrap gap-3 justify-center text-sm"
            >
              {['⚡ Instant Analysis', '🎯 Smart Suggestions', '✓ Accuracy Verified'].map((feature, idx) => (
                <div key={idx} className="px-4 py-2 bg-white rounded-full border border-primary-200 text-secondary-700 font-medium">
                  {feature}
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Error Message */}
          {localError && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-3 p-4 bg-red-50 border border-error rounded-lg"
            >
              <span className="text-error text-xl flex-shrink-0">✕</span>
              <div>
                <p className="text-sm font-medium text-error">Error</p>
                <p className="text-sm text-secondary-700 mt-1">{localError}</p>
              </div>
            </motion.div>
          )}

          {/* Upload Zone */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
          <UploadZone onFileSelect={handleFileSelect} isLoading={state.isLoading} />
          </motion.div>

          {/* Features Grid */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.8 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {[
              {
                icon: '📄',
                title: 'Smart Detection',
                description: 'Automatically identifies and analyzes all placeholders and required fields in your document.',
              },
              {
                icon: '🤖',
                title: 'AI-Powered Validation',
                description: 'Get intelligent suggestions with real-time validation using advanced language models.',
              },
              {
                icon: '⚡',
                title: 'Fast & Secure',
                description: 'Process documents instantly with end-to-end encryption. Your data stays private.',
              },
            ].map((feature, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.9 + idx * 0.1 }}
                className="p-6 bg-white rounded-xl border border-secondary-200 shadow-md hover:shadow-lg hover:border-primary-300 transition-all"
              >
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="font-bold text-secondary-900 mb-2">{feature.title}</h3>
                <p className="text-sm text-secondary-600 leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </motion.div>

          {/* Benefits Section */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 1.1 }}
            className="bg-gradient-to-r from-primary-50 to-primary-100 border border-primary-200 rounded-xl p-8"
          >
            <h2 className="text-2xl font-bold text-secondary-900 mb-8 text-center">Why Choose LexAI?</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
              {[
                { 
                  icon: '🤖', 
                  label: 'AI Powered', 
                  description: 'Advanced LLMs for intelligent analysis' 
                },
                { 
                  icon: '⚡', 
                  label: 'GPU-Accelerated', 
                  description: 'Lightning-fast processing' 
                },
                { 
                  icon: '🔍', 
                  label: 'Semantic Analysis', 
                  description: 'Understands context, not just text' 
                },
                { 
                  icon: '✓', 
                  label: 'AI Augmented', 
                  description: 'Enhances human decision-making' 
                },
                { 
                  icon: '🔒', 
                  label: 'End-to-End Encrypted', 
                  description: 'Military-grade security' 
                },
                { 
                  icon: '🗑️', 
                  label: 'Zero Data Retention', 
                  description: 'Your data is never stored' 
                },
              ].map((feature, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 1.2 + idx * 0.05 }}
                  className="space-y-2 text-center"
                >
                  <p className="text-3xl">{feature.icon}</p>
                  <p className="font-bold text-secondary-900">{feature.label}</p>
                  <p className="text-xs text-secondary-600">{feature.description}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* CTA Section */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 1.2 }}
            className="text-center space-y-4"
          >
            <p className="text-secondary-600">
              Start automating your document workflows today. <span className="font-semibold text-secondary-900">No credit card required.</span>
            </p>
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-2xl"
            >
              ↓
            </motion.div>
          </motion.div>
          </>
          )}
        </div>
      </main>
    </>
  );
}
