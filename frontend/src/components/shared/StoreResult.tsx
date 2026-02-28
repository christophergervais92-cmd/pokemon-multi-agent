import { MapPin, ExternalLink } from 'lucide-react'
import { cn, formatPrice } from '@/lib/utils'
import RetailerBadge from './RetailerBadge'
import type { StoreResult as StoreResultType } from '@/types/stock'

interface StoreResultProps {
  store: StoreResultType
  onBuyClick?: (url: string) => void
  className?: string
}

export default function StoreResult({
  store,
  onBuyClick,
  className,
}: StoreResultProps) {
  const address = [store.address, store.city, store.state, store.zip]
    .filter(Boolean)
    .join(', ')

  return (
    <div
      className={cn(
        'bg-surface rounded-xl border border-border p-4 space-y-3',
        className
      )}
    >
      {/* Header: store name + retailer badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-foreground truncate">
            {store.store}
          </h3>
          {address && (
            <div className="flex items-center gap-1 mt-1 text-xs text-muted">
              <MapPin className="h-3 w-3 shrink-0" />
              <span className="truncate">{address}</span>
              {store.distance !== undefined && (
                <span className="shrink-0 ml-1">
                  ({store.distance.toFixed(1)} mi)
                </span>
              )}
            </div>
          )}
        </div>
        <RetailerBadge retailer={store.retailer} size="sm" />
      </div>

      {/* Products */}
      {store.products.length > 0 && (
        <div className="space-y-2">
          {store.products.map((product, i) => (
            <div
              key={i}
              className="flex items-center justify-between gap-3 py-2 border-t border-border first:border-t-0 first:pt-0"
            >
              <div className="flex items-center gap-2 min-w-0">
                {/* Stock indicator */}
                <span
                  className={cn(
                    'h-2 w-2 rounded-full shrink-0',
                    product.inStock ? 'bg-emerald-400' : 'bg-red-400'
                  )}
                />
                <div className="min-w-0">
                  <p className="text-sm text-foreground truncate">
                    {product.name}
                  </p>
                  <p className="text-xs text-muted">
                    {product.inStock ? 'In Stock' : 'Out of Stock'}
                    {product.quantity !== undefined &&
                      product.quantity > 0 &&
                      ` (${product.quantity})`}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {product.price !== undefined && product.price > 0 && (
                  <span className="text-sm font-semibold font-mono tabular-nums text-foreground">
                    ${formatPrice(product.price)}
                  </span>
                )}
                {product.url && (
                  <button
                    onClick={() => onBuyClick?.(product.url!)}
                    className={cn(
                      'inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
                      product.inStock
                        ? 'bg-accent text-accent-foreground hover:bg-accent/90'
                        : 'bg-surface-hover text-muted cursor-not-allowed'
                    )}
                    disabled={!product.inStock}
                  >
                    Buy
                    <ExternalLink className="h-3 w-3" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Store-level buy link */}
      {store.url && store.products.length === 0 && (
        <button
          onClick={() => onBuyClick?.(store.url!)}
          className={cn(
            'w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            store.inStock
              ? 'bg-accent text-accent-foreground hover:bg-accent/90'
              : 'bg-surface-hover text-muted cursor-not-allowed'
          )}
          disabled={!store.inStock}
        >
          {store.inStock ? 'View in Store' : 'Out of Stock'}
          <ExternalLink className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Last checked */}
      {store.lastChecked && (
        <p className="text-xs text-muted pt-1">
          Last checked: {new Date(store.lastChecked).toLocaleString()}
        </p>
      )}
    </div>
  )
}
