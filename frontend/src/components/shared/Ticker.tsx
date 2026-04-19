/**
 * Live price ticker — continuous scroll of trending cards.
 * Pauses on hover. Click-through to card detail.
 */
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useTrendingCards } from '@/hooks/useApi'
import { formatPrice } from '@/lib/utils'

export default function Ticker() {
  const navigate = useNavigate()
  const { data } = useTrendingCards(18)

  const items = useMemo(() => {
    const raw = data?.data ?? []
    // Prefer non-null prices, interleave if possible
    const priced = raw.filter(c => c.price != null || c.tcgplayer_market != null)
    return priced.length > 0 ? priced : raw
  }, [data])

  if (items.length === 0) {
    return (
      <div className="h-8 border-b border-border bg-surface flex items-center px-4 text-[11px] text-muted font-mono uppercase tracking-widest">
        <span className="live-dot mr-2" /> Loading market data…
      </div>
    )
  }

  // Duplicate list so scroll is seamless
  const tickerItems = [...items, ...items]

  return (
    <div className="h-8 border-b border-border bg-surface/80 backdrop-blur-sm flex items-center overflow-hidden relative">
      <div className="shrink-0 px-3 h-full flex items-center gap-2 border-r border-border bg-surface-2 z-10">
        <span className="live-dot" />
        <span className="text-[10px] text-muted font-mono uppercase tracking-[0.18em]">LIVE</span>
      </div>
      <div className="ticker-wrap flex-1 h-full flex items-center">
        <div className="ticker-track py-1">
          {tickerItems.map((card, i) => {
            const price = card.price ?? card.tcgplayer_market ?? null
            const change = card.change_7d ?? card.change_30d ?? null
            const isUp = change != null && change > 0
            const isDown = change != null && change < 0
            const Icon = isUp ? TrendingUp : isDown ? TrendingDown : Minus
            return (
              <button
                key={`${card.id}-${i}`}
                onClick={() => navigate(`/cards/${card.id}`)}
                className="shrink-0 flex items-center gap-2 text-[11px] px-1 hover:text-accent transition-colors group"
              >
                <span className="text-foreground-dim font-medium truncate max-w-[14ch]">
                  {card.name}
                </span>
                <span className="font-mono-numbers text-foreground">
                  ${price != null ? formatPrice(price) : '—'}
                </span>
                {change != null && (
                  <span className={`font-mono-numbers flex items-center gap-0.5 ${
                    isUp ? 'delta-up' : isDown ? 'delta-down' : 'delta-flat'
                  }`}>
                    <Icon className="w-2.5 h-2.5" />
                    {isUp ? '+' : ''}{change.toFixed(1)}%
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
