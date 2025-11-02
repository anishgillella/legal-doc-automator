/**
 * UploadZone Component - Drag & drop file upload
 */

'use client';

import { useRef, useState } from 'react';

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
}

export function UploadZone({ onFileSelect, isLoading = false }: UploadZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const validateFile = (file: File): boolean => {
    if (!file.name.endsWith('.docx')) {
      alert('Please upload a .docx file');
      return false;
    }
    if (file.size > 50 * 1024 * 1024) {
      alert('File size must be less than 50MB');
      return false;
    }
    return true;
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (validateFile(file)) {
        setSelectedFileName(file.name);
        onFileSelect(file);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (validateFile(file)) {
        setSelectedFileName(file.name);
        onFileSelect(file);
      }
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full">
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
          transition-all duration-200 ease-in-out
          ${isDragActive 
            ? 'border-primary-500 bg-primary-50' 
            : 'border-secondary-200 bg-secondary-50 hover:border-primary-400'
          }
          ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".docx"
          onChange={handleChange}
          className="hidden"
          disabled={isLoading}
        />

        <div className="flex flex-col items-center gap-4">
          {/* Icon */}
          <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-primary-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
              />
            </svg>
          </div>

          {/* Text */}
          <div>
            <h3 className="text-xl font-semibold text-secondary-900 mb-1">
              {selectedFileName ? '✓ File Selected' : 'Drag & Drop Your Document'}
            </h3>
            {selectedFileName ? (
              <p className="text-secondary-600 text-sm font-medium">{selectedFileName}</p>
            ) : (
              <>
                <p className="text-secondary-600 text-sm mb-2">or click to browse</p>
                <p className="text-xs text-secondary-500">Supported: .docx files • Max 50MB</p>
              </>
            )}
          </div>

          {/* Loading state */}
          {isLoading && (
            <div className="flex items-center gap-2 text-primary-600">
              <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-medium">Processing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
