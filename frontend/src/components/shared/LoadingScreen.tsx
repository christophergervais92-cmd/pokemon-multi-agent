import { cn } from '@/lib/utils'

interface LoadingScreenProps {
  message?: string
  className?: string
}

export default function LoadingScreen({
  message = 'Loading...',
  className,
}: LoadingScreenProps) {
  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex flex-col items-center justify-center bg-background',
        className
      )}
    >
      {/* Pokeball SVG */}
      <svg
        viewBox="0 0 100 100"
        className="h-16 w-16 animate-spin"
        style={{ animationDuration: '1.2s' }}
      >
        {/* Outer circle */}
        <circle
          cx="50"
          cy="50"
          r="46"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-border"
        />
        {/* Top half (red) */}
        <path
          d="M 4 50 A 46 46 0 0 1 96 50"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-accent"
        />
        {/* Center line */}
        <line
          x1="4"
          y1="50"
          x2="96"
          y2="50"
          stroke="currentColor"
          strokeWidth="4"
          className="text-border"
        />
        {/* Center circle outer */}
        <circle
          cx="50"
          cy="50"
          r="14"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-border"
        />
        {/* Center circle inner */}
        <circle
          cx="50"
          cy="50"
          r="6"
          fill="currentColor"
          className="text-accent"
        />
      </svg>

      {/* Loading text */}
      <p className="mt-6 text-sm text-muted animate-pulse">{message}</p>
    </div>
  )
}
