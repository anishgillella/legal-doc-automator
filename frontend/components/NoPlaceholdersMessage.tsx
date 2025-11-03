'use client';

import { motion } from 'framer-motion';

interface NoPlaceholdersMessageProps {
  message: string;
  fileName: string;
  onUploadAnother: () => void;
  onDownload?: () => void;
}

export function NoPlaceholdersMessage({
  message,
  fileName,
  onUploadAnother,
  onDownload,
}: NoPlaceholdersMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, type: 'spring', stiffness: 300 }}
      className="w-full max-w-2xl mx-auto"
    >
      {/* Success Card */}
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-8 space-y-6 shadow-lg">
        {/* Icon */}
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-6xl text-center"
        >
          ✓
        </motion.div>

        {/* Title */}
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-green-900">
            Document Processed Successfully
          </h2>
          <p className="text-sm text-green-700">
            <span className="font-medium">{fileName}</span>
          </p>
        </div>

        {/* Assessment Message */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="bg-white rounded-lg border border-green-200 p-4"
        >
          <p className="text-sm text-green-800 leading-relaxed">
            <span className="font-medium block mb-2">Document Analysis:</span>
            {message}
          </p>
        </motion.div>

        {/* Info Box */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="bg-blue-50 border border-blue-200 rounded-lg p-4"
        >
          <p className="text-xs text-blue-800">
            <span className="font-semibold">ℹ️ Next Steps:</span>
            <br />
            This document doesn't have placeholder fields that need to be filled. 
            You can download it as-is or upload a different document that contains fields to complete.
          </p>
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex gap-3"
        >
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onUploadAnother}
            className="flex-1 px-4 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 transition-colors"
          >
            ↻ Upload Another Document
          </motion.button>
          {onDownload && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onDownload}
              className="flex-1 px-4 py-3 border-2 border-green-300 text-green-700 font-medium rounded-lg hover:bg-green-50 transition-colors"
            >
              ↓ Download Document
            </motion.button>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}
