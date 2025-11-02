/**
 * Header Component - Navigation and branding
 */

'use client';

import Link from 'next/link';

interface HeaderProps {
  title?: string;
  showHome?: boolean;
}

export function Header({ title = 'Lexsy Document AI', showHome = false }: HeaderProps) {
  return (
    <header className="bg-gradient-to-r from-primary-900 to-primary-700 text-white shadow-lg">
      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-500 rounded-lg flex items-center justify-center font-bold text-lg">
              L
            </div>
            <div>
              <h1 className="text-2xl font-bold">{title}</h1>
              <p className="text-primary-100 text-sm">AI-Powered Legal Document Automation</p>
            </div>
          </div>

          {showHome && (
            <Link
              href="/"
              className="px-4 py-2 bg-primary-500 hover:bg-primary-600 rounded-lg transition-colors font-medium text-sm"
            >
              ← Back to Home
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
