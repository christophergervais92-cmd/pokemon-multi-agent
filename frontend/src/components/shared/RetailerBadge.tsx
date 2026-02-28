import { cn, getRetailerColor, getRetailerBgColor } from '@/lib/utils'

interface RetailerBadgeProps {
  retailer: string
  size?: 'sm' | 'md'
}

export default function RetailerBadge({ retailer, size = 'sm' }: RetailerBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-md',
        getRetailerColor(retailer),
        getRetailerBgColor(retailer),
        size === 'sm' && 'px-2 py-0.5 text-xs',
        size === 'md' && 'px-2.5 py-1 text-sm'
      )}
    >
      {retailer}
    </span>
  )
}
