import React from 'react'
import { cn } from '@/lib/utils'

const colorStyles = {
  accent: 'bg-accent',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
} as const

export type ProgressColor = keyof typeof colorStyles

export interface ProgressProps {
  value: number
  className?: string
  color?: ProgressColor
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  className,
  color = 'accent',
}) => {
  const clampedValue = Math.min(100, Math.max(0, value))

  return (
    <div
      className={cn(
        'h-2 w-full overflow-hidden rounded-full bg-border',
        className,
      )}
      role="progressbar"
      aria-valuenow={clampedValue}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn(
          'h-full rounded-full transition-all duration-500 ease-out',
          colorStyles[color],
        )}
        style={{ width: `${clampedValue}%` }}
      />
    </div>
  )
}

Progress.displayName = 'Progress'

export default Progress
