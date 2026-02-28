import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn, formatPrice } from '@/lib/utils'

interface PriceTagProps {
  price: number
  change?: number
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeStyles = {
  sm: {
    price: 'text-sm font-semibold',
    change: 'text-xs',
    icon: 'h-3 w-3',
  },
  md: {
    price: 'text-lg font-bold',
    change: 'text-sm',
    icon: 'h-3.5 w-3.5',
  },
  lg: {
    price: 'text-2xl font-bold',
    change: 'text-sm',
    icon: 'h-4 w-4',
  },
}

export default function PriceTag({
  price,
  change,
  size = 'md',
  className,
}: PriceTagProps) {
  const styles = sizeStyles[size]
  const isPositive = change !== undefined && change > 0
  const isNegative = change !== undefined && change < 0
  const isNeutral = change === undefined || change === 0

  return (
    <div className={cn('flex items-baseline gap-2', className)}>
      {/* Price */}
      <span className={cn('font-mono tabular-nums text-foreground', styles.price)}>
        ${formatPrice(price)}
      </span>

      {/* Change indicator */}
      {change !== undefined && change !== 0 && (
        <span
          className={cn(
            'flex items-center gap-0.5 font-medium',
            styles.change,
            isPositive && 'text-emerald-400',
            isNegative && 'text-red-400',
            isNeutral && 'text-muted'
          )}
        >
          {isPositive && <TrendingUp className={styles.icon} />}
          {isNegative && <TrendingDown className={styles.icon} />}
          {isNeutral && <Minus className={styles.icon} />}
          <span>
            {isPositive ? '+' : ''}
            {change.toFixed(1)}%
          </span>
        </span>
      )}
    </div>
  )
}
