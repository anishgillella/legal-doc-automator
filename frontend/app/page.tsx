'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Header } from '@/components/Header';
import { UploadZone } from '@/components/UploadZone';
import { ThreeDBackground } from '@/components/ThreeDBackground';
import { apiService } from '@/services/api';
import { useFormContext } from '@/context/FormContext';

export default function Home() {
  const router = useRouter();
  const { setFile, setPlaceholders, setLoading, reset, state } = useFormContext();
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
      <ThreeDBackground />
      <Header title="LexAI" />

      <main className="flex-1 flex items-center justify-center px-6 py-12 relative z-10">
        <div className="w-full max-w-3xl space-y-12">
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
            className="bg-gradient-to-r from-primary-50 to-primary-100 border border-primary-200 rounded-xl p-8 text-center"
          >
            <h2 className="text-2xl font-bold text-secondary-900 mb-4">Why Choose LexAI?</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
              {[
                { number: '10x', label: 'Faster' },
                { number: '99%', label: 'Accurate' },
                { number: '∞', label: 'Scalable' },
                { number: '24/7', label: 'Available' },
              ].map((stat, idx) => (
                <div key={idx} className="space-y-1">
                  <p className="text-3xl font-bold text-primary-600">{stat.number}</p>
                  <p className="text-secondary-600 font-medium">{stat.label}</p>
                </div>
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
        </div>
      </main>
    </>
  );
}
