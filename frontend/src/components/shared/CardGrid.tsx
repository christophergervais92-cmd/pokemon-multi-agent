import { motion } from 'framer-motion'
import { cn, formatPrice } from '@/lib/utils'
import { staggerContainer, staggerItem, cardHover } from '@/lib/animations'
import type { PokemonCard } from '@/types/card'

interface CardGridProps {
  cards: PokemonCard[]
  onCardClick?: (card: PokemonCard) => void
  isLoading?: boolean
  className?: string
}

function getMarketPrice(card: PokemonCard): number | null {
  if (!card.tcgplayer?.prices) return null
  const priceTypes = Object.values(card.tcgplayer.prices)
  for (const pt of priceTypes) {
    if (pt.market) return pt.market
    if (pt.mid) return pt.mid
  }
  return null
}

function CardSkeleton() {
  return (
    <div className="bg-surface rounded-xl border border-border overflow-hidden animate-pulse">
      <div className="aspect-[2.5/3.5] bg-surface-hover" />
      <div className="p-3 space-y-2">
        <div className="h-4 bg-surface-hover rounded w-3/4" />
        <div className="h-3 bg-surface-hover rounded w-1/2" />
        <div className="h-4 bg-surface-hover rounded w-1/3 mt-2" />
      </div>
    </div>
  )
}

export default function CardGrid({
  cards,
  onCardClick,
  isLoading = false,
  className,
}: CardGridProps) {
  if (isLoading) {
    return (
      <div
        className={cn(
          'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4',
          className
        )}
      >
        {Array.from({ length: 12 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (cards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted">
        <p className="text-sm">No cards found</p>
      </div>
    )
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className={cn(
        'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4',
        className
      )}
    >
      {cards.map((card) => {
        const price = getMarketPrice(card)
        return (
          <motion.div
            key={card.id}
            variants={staggerItem}
            whileHover={cardHover}
            onClick={() => onCardClick?.(card)}
            className={cn(
              'bg-surface rounded-xl border border-border overflow-hidden transition-shadow',
              'hover:shadow-lg hover:shadow-black/20 hover:border-border/80',
              onCardClick && 'cursor-pointer'
            )}
          >
            {/* Card image */}
            <div className="aspect-[2.5/3.5] bg-surface-hover relative overflow-hidden">
              <img
                src={card.images.small}
                alt={card.name}
                loading="lazy"
                className="w-full h-full object-cover"
              />
            </div>

            {/* Card info */}
            <div className="p-3 space-y-1">
              <h3 className="text-sm font-medium text-foreground truncate">
                {card.name}
              </h3>
              <p className="text-xs text-muted truncate">
                {card.set.name} &middot; {card.number}/{card.set.printedTotal}
              </p>
              {price !== null && (
                <p className="text-sm font-semibold font-mono tabular-nums text-accent pt-1">
                  ${formatPrice(price)}
                </p>
              )}
            </div>
          </motion.div>
        )
      })}
    </motion.div>
  )
}
