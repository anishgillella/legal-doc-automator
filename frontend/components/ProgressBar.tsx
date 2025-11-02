/**
 * ProgressBar Component - Shows form completion progress
 */

'use client';

interface ProgressBarProps {
  current: number;
  total: number;
  label?: string;
}

export function ProgressBar({ current, total, label }: ProgressBarProps) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between items-center mb-2">
          <p className="text-sm font-medium text-secondary-700">{label}</p>
          <p className="text-sm font-semibold text-primary-600">{current} of {total}</p>
        </div>
      )}
      
      <div className="w-full bg-secondary-200 rounded-full h-2 overflow-hidden">
        <div
          className="bg-gradient-to-r from-primary-500 to-primary-600 h-full rounded-full transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <p className="text-xs text-secondary-500 mt-2">{percentage}% complete</p>
    </div>
  );
}
