/**
 * CardGradeModal — click any card in the Database grid to see
 * a bar chart of Raw / PSA 9 / PSA 10 / BGS 10 / CGC 10 prices.
 */
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ExternalLink } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import { useGradedPricesStructured } from '@/hooks/useApi'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatPrice } from '@/lib/utils'
import type { SetCardItem } from '@/lib/api'

/* ── Grade multipliers (fallback when no live data) ── */
const MULT: Record<string, number> = {
  raw: 1, psa9: 2.1, psa10: 3.2, cgc10: 2.4, bgs10: 3.8,
}
const BARS = [
  { key: 'raw',   label: 'Raw',    color: '#ef4444' },
  { key: 'psa9',  label: 'PSA 9',  color: '#f97316' },
  { key: 'psa10', label: 'PSA 10', color: '#f43f5e' },
  { key: 'cgc10', label: 'CGC 10', color: '#3b82f6' },
  { key: 'bgs10', label: 'BGS 10', color: '#a855f7' },
]

function getRarityVariant(rarity?: string) {
  const r = (rarity || '').toLowerCase()
  if (r.includes('special art') || r.includes('hyper')) return 'danger' as const
  if (r.includes('illustration') || r.includes('secret')) return 'warning' as const
  if (r.includes('ultra') || r.includes('full art')) return 'accent' as const
  if (r.includes('holo') || r.includes('rare')) return 'success' as const
  return 'default' as const
}

interface Props {
  card: SetCardItem | null
  onClose: () => void
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: { label: string; color: string } }>
}

function GradeTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null
  const item = payload[0]
  return (
    <div className="bg-[#0a1228] border border-white/[0.08] rounded-xl px-3 py-2 shadow-2xl">
      <p className="text-xs text-muted-foreground/60 mb-1">{item.payload.label}</p>
      <p className="text-sm font-mono font-bold" style={{ color: item.payload.color }}>
        ${formatPrice(item.value)}
      </p>
    </div>
  )
}

export default function CardGradeModal({ card, onClose }: Props) {
  const navigate = useNavigate()
  const { data: gradedData, isLoading } = useGradedPricesStructured(card?.id)
  const rawPrice = card?.tcgplayer_market ?? null

  /* Build bar data — prefer live graded prices, fall back to multipliers */
  const barData = BARS.map(({ key, label, color }) => {
    let price: number | null = null

    if (key === 'raw') {
      price = rawPrice
    } else if (gradedData) {
      // gradedData is { PSA: [{grade, market, ...}], CGC: [...], BGS: [...] }
      for (const [company, entries] of Object.entries(gradedData)) {
        const co = company.toLowerCase()
        for (const entry of entries as Array<{ grade: string; market: number | null }>) {
          const g = String(entry.grade).replace(/\s+/g, '')
          if (key === 'psa10' && co === 'psa' && g === '10') price = entry.market
          if (key === 'psa9'  && co === 'psa' && g === '9')  price = entry.market
          if (key === 'cgc10' && co === 'cgc')               price = entry.market
          if (key === 'bgs10' && co === 'bgs')               price = entry.market
        }
      }
    }

    // Fall back to multiplier estimate
    if (price == null && rawPrice) {
      price = +(rawPrice * MULT[key]).toFixed(2)
    }

    return { key, label, color, price: price ?? 0, estimated: price == null || (key !== 'raw' && !gradedData) }
  }).filter((b) => b.price > 0)

  if (!card) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="relative bg-[#0a1228] border border-white/[0.08] rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close */}
          <button
            onClick={onClose}
            className="absolute top-3 right-3 z-10 h-8 w-8 flex items-center justify-center rounded-lg text-muted-foreground/60 hover:text-foreground hover:bg-white/[0.06] transition-colors"
          >
            <X className="h-4 w-4" />
          </button>

          <div className="flex gap-4 p-5">
            {/* Card image */}
            <div className="shrink-0 w-28">
              <div className="aspect-[3/4] rounded-xl overflow-hidden bg-white/[0.04] border border-white/[0.06]">
                {card.image_url || card.small_image_url ? (
                  <img
                    src={card.small_image_url ?? card.image_url}
                    alt={card.name}
                    className="w-full h-full object-contain"
                  />
                ) : null}
              </div>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0 space-y-1.5">
              <p className="text-base font-semibold text-foreground truncate pr-8">{card.name}</p>
              {card.rarity && (
                <Badge variant={getRarityVariant(card.rarity)} className="text-[10px]">
                  {card.rarity}
                </Badge>
              )}
              {rawPrice != null && (
                <div className="flex items-baseline gap-1.5 pt-1">
                  <span className="text-xs text-muted-foreground/50 uppercase tracking-wide">Raw</span>
                  <span className="text-2xl font-mono font-bold text-accent">${formatPrice(rawPrice)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Chart */}
          <div className="px-5 pb-2">
            <p className="text-xs text-muted-foreground/50 uppercase tracking-wider mb-3 font-medium">
              Price by Grade
            </p>
            {isLoading ? (
              <div className="flex gap-2 h-32 items-end">
                {BARS.map((b) => (
                  <Skeleton key={b.key} className="flex-1 rounded-lg" style={{ height: `${40 + Math.random() * 60}%` }} />
                ))}
              </div>
            ) : (
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData} margin={{ top: 20, right: 4, left: 4, bottom: 4 }} barCategoryGap="20%">
                    <XAxis
                      dataKey="label"
                      stroke="#7e92b8"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="#7e92b8"
                      fontSize={9}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}`}
                      width={42}
                    />
                    <Tooltip content={<GradeTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                    <Bar dataKey="price" radius={[4, 4, 0, 0]}>
                      <LabelList
                        dataKey="price"
                        position="top"
                        formatter={(v: number) => `$${formatPrice(v)}`}
                        style={{ fill: '#7e92b8', fontSize: 9, fontFamily: 'monospace' }}
                      />
                      {barData.map((entry) => (
                        <Cell key={entry.key} fill={entry.color} fillOpacity={entry.estimated ? 0.45 : 0.85} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <p className="text-[9px] text-muted-foreground/30 mt-1">
              Faded bars = estimated via multipliers. Live data shown at full opacity.
            </p>
          </div>

          {/* Footer */}
          <div className="px-5 py-4 border-t border-white/[0.05] flex items-center justify-between">
            <button
              onClick={() => { onClose(); navigate(`/cards/${card.id}`) }}
              className="flex items-center gap-1.5 text-xs text-accent hover:text-accent/80 font-medium transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              View Full Details + Price History
            </button>
            <button
              onClick={onClose}
              className="text-xs text-muted-foreground/50 hover:text-foreground transition-colors"
            >
              Close
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
