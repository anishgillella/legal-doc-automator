import type { Metadata } from 'next';
import { FormProvider } from '@/context/FormContext';
import './globals.css';

export const metadata: Metadata = {
  title: 'Lexsy Document AI - Legal Document Automation',
  description:
    'AI-powered legal document template automation. Upload, extract, and fill document placeholders with intelligent suggestions.',
  keywords: ['legal documents', 'AI', 'automation', 'templates', 'document processing'],
  authors: [{ name: 'Lexsy' }],
  viewport: 'width=device-width, initial-scale=1.0',
  robots: 'index, follow',
  openGraph: {
    title: 'Lexsy Document AI',
    description: 'AI-powered legal document automation',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <FormProvider>
          <div className="min-h-screen bg-gradient-to-br from-secondary-50 to-primary-50 flex flex-col">
            {children}
          </div>
        </FormProvider>
      </body>
    </html>
  );
}
