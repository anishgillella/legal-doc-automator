'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

const facts = [
  {
    type: 'fact',
    text: '⚡ Did you know? LexAI can analyze 100+ page documents in seconds.',
  },
  {
    type: 'fact',
    text: '🤖 Fun fact: Our AI has been trained on thousands of legal documents.',
  },
  {
    type: 'fact',
    text: '💡 Pro tip: You can fill multiple documents in one session.',
  },
  {
    type: 'riddle',
    question: '🧩 Riddle: I have cities but no houses, forests but no trees. What am I?',
    answer: 'A map!',
  },
  {
    type: 'fact',
    text: '✨ LexAI saves an average of 15 minutes per document.',
  },
  {
    type: 'fact',
    text: '🎯 99% accuracy rate - your documents are in good hands.',
  },
  {
    type: 'riddle',
    question: '🧩 Riddle: What gets wet while drying?',
    answer: 'A towel!',
  },
  {
    type: 'fact',
    text: '🔒 All your documents are processed securely and never stored.',
  },
];

export function ParsingLoader({ fileName }: { fileName: string }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % facts.length);
      setShowAnswer(false);
    }, 4000);

    return () => clearInterval(timer);
  }, []);

  const current = facts[currentIndex];

  return (
    <div className="fixed inset-0 z-50 bg-gradient-to-br from-primary-50 to-white flex items-center justify-center px-6">
      <div className="w-full max-w-2xl space-y-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center space-y-2"
        >
          <h1 className="text-4xl font-bold text-secondary-900">Analyzing Your Document</h1>
          <p className="text-lg text-secondary-600">{fileName}</p>
        </motion.div>

        {/* Animated Cube Loader */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="flex justify-center"
        >
          <div className="relative w-24 h-24">
            {/* Outer rotating ring */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
              className="absolute inset-0 border-4 border-transparent border-t-primary-600 border-r-primary-400 rounded-full"
            />
            
            {/* Inner rotating ring (opposite direction) */}
            <motion.div
              animate={{ rotate: -360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="absolute inset-2 border-4 border-transparent border-b-primary-500 border-l-primary-300 rounded-full"
            />

            {/* Center dot */}
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
              className="absolute inset-8 bg-gradient-to-r from-primary-600 to-primary-500 rounded-full"
            />
          </div>
        </motion.div>

        {/* Progress text */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-center"
        >
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="text-sm font-semibold text-primary-600 inline-block"
          >
            Processing your file...
          </motion.div>
        </motion.div>

        {/* Fun Facts / Riddles */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.6 }}
          key={currentIndex}
          className="bg-white rounded-xl border-2 border-primary-200 p-8 space-y-4"
        >
          {current.type === 'fact' ? (
            <p className="text-center text-lg text-secondary-800 font-medium">
              {current.text}
            </p>
          ) : (
            <>
              <p className="text-center text-lg text-secondary-800 font-medium">
                {current.question}
              </p>
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                onClick={() => setShowAnswer(!showAnswer)}
                className="w-full py-2 px-4 bg-primary-100 hover:bg-primary-200 text-primary-700 font-semibold rounded-lg transition-colors"
              >
                {showAnswer ? '🙈 Hide Answer' : '👀 Reveal Answer'}
              </motion.button>
              {showAnswer && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center text-primary-700 font-bold text-lg bg-primary-50 py-3 rounded-lg"
                >
                  {current.answer}
                </motion.div>
              )}
            </>
          )}
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="grid grid-cols-3 gap-4 text-center"
        >
          {[
            { icon: '⚡', label: 'Fast', value: '< 5s' },
            { icon: '🎯', label: 'Accurate', value: '99%' },
            { icon: '🔒', label: 'Secure', value: 'Private' },
          ].map((stat, idx) => (
            <div key={idx} className="space-y-1">
              <p className="text-3xl">{stat.icon}</p>
              <p className="text-xs font-semibold text-secondary-600">{stat.label}</p>
              <p className="text-sm font-bold text-primary-600">{stat.value}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
