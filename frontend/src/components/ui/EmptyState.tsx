import React from 'react'
import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  icon: React.ReactNode
  title: string
  description: string
  action?: React.ReactNode
  className?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-16',
        className,
      )}
    >
      <div className="text-muted-foreground opacity-50 [&>svg]:h-16 [&>svg]:w-16">
        {icon}
      </div>
      <h3 className="mt-4 text-lg font-semibold text-foreground">
        {title}
      </h3>
      <p className="mt-2 max-w-md text-center text-sm text-muted">
        {description}
      </p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}

EmptyState.displayName = 'EmptyState'

export default EmptyState
