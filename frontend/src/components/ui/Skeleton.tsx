import React from 'react'
import { cn } from '@/lib/utils'

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  circle?: boolean
}

export const Skeleton: React.FC<SkeletonProps> = ({
  circle = false,
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        'animate-shimmer bg-surface-elevated',
        circle ? 'rounded-full' : 'rounded-lg',
        className,
      )}
      {...props}
    />
  )
}

Skeleton.displayName = 'Skeleton'

export interface SkeletonTextProps {
  lines?: number
  className?: string
}

export const SkeletonText: React.FC<SkeletonTextProps> = ({
  lines = 3,
  className,
}) => {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            i === lines - 1 ? 'w-3/4' : 'w-full',
          )}
        />
      ))}
    </div>
  )
}

SkeletonText.displayName = 'SkeletonText'

export const SkeletonCard: React.FC<{ className?: string }> = ({
  className,
}) => {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-surface p-6 space-y-4',
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <Skeleton circle className="h-10 w-10" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
      <SkeletonText lines={3} />
    </div>
  )
}

SkeletonCard.displayName = 'SkeletonCard'

export default Skeleton
