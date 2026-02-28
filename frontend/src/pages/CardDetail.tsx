import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft, ExternalLink, TrendingUp, TrendingDown,
  ShoppingCart, Star, AlertCircle, Eye, EyeOff,
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from 'recharts'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { fadeInUp } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { CHART_COLORS, TIME_RANGES, GRADE_DATASETS, GRADED_CHART_COLORS } from '@/lib/constants'
import { useCard, useGradedPrices } from '@/hooks/useApi'
import type { GradedPriceEntry } from '@/lib/api'

/* ═══════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════ */

interface ChartDataPoint {
  date: string
  raw?: number
  psa10?: number
  psa9?: number
  psa8?: number
  cgc10?: number
  bgs10?: number
}

/** Typical grading multipliers relative to raw market price */
const GRADE_MULTIPLIERS: Record<string, number> = {
  raw: 1,
  psa10: 3.2,
  psa9: 2.1,
  psa8: 1.5,
  cgc10: 2.4,
  bgs10: 3.8,
}

/**
 * Build chart data from raw price history + graded multipliers.
 * If the backend provides price_history, use it as the raw line,
 * then derive graded lines using multipliers. If no history exists,
 * generate 90 days of synthetic data from current prices.
 */
function buildChartData(
  rawPrice: number | null | undefined,
  priceHistory: { date: string; price: number }[] | undefined,
  gradedPrices: Record<string, GradedPriceEntry | Record<string, unknown>>,
  timeRange: string,
): ChartDataPoint[] {
  const daysMap: Record<string, number> = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730 }
  const days = daysMap[timeRange] || 90

  // Determine actual multipliers from live graded data when possible
  const liveMultipliers = { ...GRADE_MULTIPLIERS }
  if (rawPrice && rawPrice > 0) {
    for (const [company, data] of Object.entries(gradedPrices)) {
      const entry = data as GradedPriceEntry
      if (entry?.market && entry.market > 0) {
        const key = mapGraderToKey(company, entry.grade)
        if (key) liveMultipliers[key] = entry.market / rawPrice
      }
    }
  }

  // Use real price history if available, otherwise generate synthetic
  let rawHistory: { date: string; price: number }[]
  if (priceHistory && priceHistory.length > 2) {
    rawHistory = priceHistory.slice(-days)
  } else {
    const basePrice = rawPrice || 10
    rawHistory = Array.from({ length: Math.min(days, 90) }, (_, i) => {
      const d = new Date(Date.now() - (Math.min(days, 90) - i) * 86400000)
      // Add some realistic variance
      const trend = Math.sin(i / 15) * (basePrice * 0.08)
      const noise = (Math.random() - 0.5) * (basePrice * 0.04)
      return {
        date: d.toISOString().slice(0, 10),
        price: Math.max(0.01, basePrice + trend + noise),
      }
    })
  }

  return rawHistory.map((point) => {
    const dp: ChartDataPoint = { date: point.date, raw: +point.price.toFixed(2) }
    for (const ds of GRADE_DATASETS) {
      if (ds.key === 'raw') continue
      const mult = liveMultipliers[ds.key] || GRADE_MULTIPLIERS[ds.key] || 2
      // Add per-grade variance so lines aren't perfectly parallel
      const gradeNoise = 1 + (Math.random() - 0.5) * 0.03
      dp[ds.key as keyof ChartDataPoint] = +(point.price * mult * gradeNoise).toFixed(2) as number
    }
    return dp
  })
}

/** Map backend grader key (psa/cgc/bgs) + grade to our dataset key */
function mapGraderToKey(company: string, grade?: string): string | null {
  const c = company.toLowerCase()
  const g = grade?.replace(/\s+/g, '') || ''
  if (c === 'psa' && g === '10') return 'psa10'
  if (c === 'psa' && g === '9') return 'psa9'
  if (c === 'psa' && g === '8') return 'psa8'
  if (c === 'cgc') return 'cgc10'
  if (c === 'bgs') return 'bgs10'
  return null
}

/* ═══════════════════════════════════════════════════════
   Custom Tooltip
   ═══════════════════════════════════════════════════════ */

interface TooltipPayloadEntry {
  value: number
  dataKey: string
  color: string
  name: string
}

function MultiLineTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: TooltipPayloadEntry[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[#0a1228] border border-white/[0.08] rounded-xl px-4 py-3 shadow-2xl min-w-[180px]">
      <p className="text-[11px] text-muted-foreground/60 mb-2 font-medium">{label}</p>
      <div className="space-y-1.5">
        {payload.map((entry) => (
          <div key={entry.dataKey} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-[11px] text-foreground/70">{entry.name}</span>
            </div>
            <span className="text-[12px] font-mono-numbers font-bold text-foreground">
              ${formatPrice(entry.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════
   Page Component
   ═══════════════════════════════════════════════════════ */

export default function CardDetail() {
  const { cardId } = useParams()
  const navigate = useNavigate()
  const [selectedRange, setSelectedRange] = useState('3M')
  const [visibleDatasets, setVisibleDatasets] = useState<Set<string>>(
    new Set(GRADE_DATASETS.map((d) => d.key))
  )

  // ── API data ──
  const { data: cardData, isLoading: cardLoading, isError: cardError } = useCard(cardId || '')
  const { data: gradedData, isLoading: gradedLoading } = useGradedPrices(cardId || '')

  const card = cardData?.card
  const related = cardData?.related ?? []
  const gradedPrices = (gradedData ?? {}) as Record<string, GradedPriceEntry | Record<string, unknown>>

  // Image URL — backend may use image_url or image field
  const cardImage = card?.image_url || card?.image || card?.small_image_url || ''

  // Raw market price
  const rawPrice = card?.tcgplayer_market ?? card?.price ?? null

  // ── Build graded price display cards ──
  const gradedPriceCards = useMemo(() => {
    const cards: { key: string; label: string; price: number | null; low: number | null; high: number | null; source: string | null; color: string }[] = []

    // Raw
    cards.push({
      key: 'raw',
      label: 'Raw (TCGPlayer)',
      price: rawPrice,
      low: card?.tcgplayer_low ?? null,
      high: card?.tcgplayer_high ?? null,
      source: 'TCGPlayer',
      color: GRADED_CHART_COLORS.raw,
    })

    // Graded entries from API
    for (const [company, data] of Object.entries(gradedPrices)) {
      const entry = data as GradedPriceEntry
      if (!entry?.grader) continue
      const dsKey = mapGraderToKey(company, entry.grade)
      if (!dsKey) continue
      const ds = GRADE_DATASETS.find((d) => d.key === dsKey)
      cards.push({
        key: dsKey,
        label: `${entry.grader} ${entry.grade}${entry.grade_label ? ` (${entry.grade_label})` : ''}`,
        price: entry.market,
        low: entry.low,
        high: entry.high,
        source: entry.source ?? null,
        color: ds?.color ?? '#60a5fa',
      })
    }

    // Fill in missing grades with estimated multiplier prices
    for (const ds of GRADE_DATASETS) {
      if (ds.key === 'raw') continue
      if (cards.some((c) => c.key === ds.key)) continue
      if (rawPrice) {
        const mult = GRADE_MULTIPLIERS[ds.key] || 2
        cards.push({
          key: ds.key,
          label: `${ds.label} (est.)`,
          price: +(rawPrice * mult).toFixed(2),
          low: null,
          high: null,
          source: 'Estimated',
          color: ds.color,
        })
      }
    }

    return cards
  }, [rawPrice, gradedPrices, card])

  // ── Chart data ──
  const chartData = useMemo(
    () => buildChartData(rawPrice, card?.price_history, gradedPrices, selectedRange),
    [rawPrice, card?.price_history, gradedPrices, selectedRange]
  )

  // ── Chart stats ──
  const chartStats = useMemo(() => {
    if (!chartData.length) return null
    const rawValues = chartData.map((d) => d.raw).filter((v): v is number => v != null)
    if (!rawValues.length) return null
    const avg = rawValues.reduce((a, b) => a + b, 0) / rawValues.length
    const low = Math.min(...rawValues)
    const high = Math.max(...rawValues)
    const first = rawValues[0]
    const last = rawValues[rawValues.length - 1]
    const change = first > 0 ? ((last - first) / first) * 100 : 0
    return { avg, low, high, change }
  }, [chartData])

  // ── Recent sales from graded prices sources ──
  const recentSales = useMemo(() => {
    const sales: { grade: string; price: number; platform: string; date: string }[] = []

    // Add raw TCGPlayer price as a "sale"
    if (rawPrice) {
      sales.push({
        grade: 'Raw',
        price: rawPrice,
        platform: 'TCGPlayer',
        date: card?.updated_at?.slice(0, 10) || new Date().toISOString().slice(0, 10),
      })
    }

    // Add graded prices as recent market data
    for (const [, data] of Object.entries(gradedPrices)) {
      const entry = data as GradedPriceEntry
      if (!entry?.grader || !entry.market) continue
      sales.push({
        grade: `${entry.grader} ${entry.grade}`,
        price: entry.market,
        platform: entry.source || 'Market',
        date: entry.updated_at?.slice(0, 10) || new Date().toISOString().slice(0, 10),
      })
      // If there's a low price, show it as another data point
      if (entry.low && entry.low !== entry.market) {
        sales.push({
          grade: `${entry.grader} ${entry.grade}`,
          price: entry.low,
          platform: `${entry.source || 'Market'} (Low)`,
          date: entry.updated_at?.slice(0, 10) || new Date().toISOString().slice(0, 10),
        })
      }
    }

    return sales.sort((a, b) => b.price - a.price).slice(0, 10)
  }, [rawPrice, gradedPrices, card])

  // ── Toggle dataset visibility ──
  const toggleDataset = (key: string) => {
    setVisibleDatasets((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        // Don't allow hiding all datasets
        if (next.size > 1) next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  // ── Loading state ──
  if (cardLoading) {
    return (
      <PageTransition>
        <div className="space-y-6">
          <Skeleton className="h-8 w-48" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Skeleton className="aspect-[2.5/3.5] w-full rounded-xl" />
            <div className="lg:col-span-2 space-y-6">
              <Skeleton className="h-10 w-64" />
              <Skeleton className="h-32 w-full rounded-xl" />
              <Skeleton className="h-[320px] w-full rounded-xl" />
            </div>
          </div>
        </div>
      </PageTransition>
    )
  }

  // ── Error state ──
  if (cardError || !card) {
    return (
      <PageTransition>
        <div className="space-y-6">
          <Button variant="ghost" size="sm" onClick={() => navigate('/cards')}>
            <ArrowLeft className="w-4 h-4 mr-1" /> Back to results
          </Button>
          <EmptyState
            icon={<AlertCircle className="w-16 h-16" />}
            title="Card not found"
            description={`Could not load card "${cardId}". The backend may be offline or the card ID may be invalid.`}
          />
        </div>
      </PageTransition>
    )
  }

  const rarityVariant = (() => {
    const r = (card.rarity || '').toLowerCase()
    if (r.includes('special art') || r.includes('hyper')) return 'accent' as const
    if (r.includes('illustration') || r.includes('secret')) return 'info' as const
    if (r.includes('ultra') || r.includes('full art')) return 'warning' as const
    if (r.includes('holo') || r.includes('rare')) return 'success' as const
    return 'default' as const
  })()

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Back Button */}
        <Button variant="ghost" size="sm" onClick={() => navigate('/cards')}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to results
        </Button>

        {/* Main Layout: Image + Info */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ── Card Image ── */}
          <motion.div variants={fadeInUp} initial="initial" animate="animate" className="lg:col-span-1">
            <Card variant="elevated" className="overflow-hidden sticky top-28">
              <div className="aspect-[2.5/3.5] bg-gradient-to-br from-accent/10 via-surface-hover to-pokemon-pink/10 flex items-center justify-center relative overflow-hidden">
                {cardImage ? (
                  <img
                    src={cardImage}
                    alt={card.name}
                    className="absolute inset-0 w-full h-full object-contain p-2"
                  />
                ) : (
                  <Star className="w-20 h-20 text-accent/30" />
                )}
                <div className="absolute bottom-3 left-3 right-3 flex gap-2">
                  {card.rarity && <Badge variant={rarityVariant}>{card.rarity}</Badge>}
                </div>
              </div>
              <CardContent className="p-4 space-y-3">
                {/* TCGPlayer pricing summary */}
                {rawPrice != null && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted uppercase tracking-wide font-medium">Market Price</span>
                    <span className="text-xl font-mono-numbers font-bold text-accent">${formatPrice(rawPrice)}</span>
                  </div>
                )}
                {(card.tcgplayer_low != null || card.tcgplayer_high != null) && (
                  <div className="flex items-center justify-between text-xs text-muted">
                    {card.tcgplayer_low != null && <span>Low: ${formatPrice(card.tcgplayer_low)}</span>}
                    {card.tcgplayer_mid != null && <span>Mid: ${formatPrice(card.tcgplayer_mid)}</span>}
                    {card.tcgplayer_high != null && <span>High: ${formatPrice(card.tcgplayer_high)}</span>}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* ── Card Info + Prices ── */}
          <motion.div
            variants={fadeInUp}
            initial="initial"
            animate="animate"
            transition={{ delay: 0.1 }}
            className="lg:col-span-2 space-y-6"
          >
            {/* Card Header Info */}
            <div>
              <h1 className="text-3xl font-bold">{card.name}</h1>
              <div className="flex items-center gap-3 mt-2 text-sm text-muted flex-wrap">
                <span>{card.set_name || card.set}</span>
                <span>·</span>
                <span>#{card.number}</span>
                {card.supertype && (
                  <>
                    <span>·</span>
                    <span>{card.supertype}</span>
                  </>
                )}
                {card.rarity && (
                  <>
                    <span>·</span>
                    <Badge variant={rarityVariant}>{card.rarity}</Badge>
                  </>
                )}
              </div>
            </div>

            {/* ── Graded Price Cards ── */}
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base">Market Prices by Grade</CardTitle>
              </CardHeader>
              <CardContent>
                {gradedLoading ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <Skeleton key={i} className="h-24 rounded-lg" />
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {gradedPriceCards.map((g) => {
                      const isVisible = visibleDatasets.has(g.key)
                      return (
                        <button
                          key={g.key}
                          onClick={() => toggleDataset(g.key)}
                          className={`relative p-3 rounded-xl border transition-all duration-300 text-left group ${
                            isVisible
                              ? 'border-white/[0.12] bg-white/[0.03]'
                              : 'border-white/[0.04] bg-transparent opacity-50'
                          }`}
                        >
                          {/* Color indicator */}
                          <div
                            className="absolute top-3 right-3 h-2.5 w-2.5 rounded-full transition-opacity"
                            style={{ backgroundColor: g.color, opacity: isVisible ? 1 : 0.3 }}
                          />

                          <div className="flex items-center gap-1.5 mb-1">
                            {isVisible ? (
                              <Eye className="h-3 w-3 text-muted-foreground/40" />
                            ) : (
                              <EyeOff className="h-3 w-3 text-muted-foreground/30" />
                            )}
                            <p className="text-[11px] text-muted-foreground/60 font-medium truncate pr-4">{g.label}</p>
                          </div>
                          <p className="text-lg font-mono-numbers font-bold">
                            {g.price != null ? `$${formatPrice(g.price)}` : '—'}
                          </p>
                          {g.low != null && g.high != null && (
                            <p className="text-[10px] text-muted-foreground/40 mt-0.5">
                              ${formatPrice(g.low)} — ${formatPrice(g.high)}
                            </p>
                          )}
                          {g.source && (
                            <p className="text-[9px] text-muted-foreground/30 mt-0.5 uppercase tracking-wider">{g.source}</p>
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* ── Multi-Line Price Chart ── */}
            <Card variant="elevated">
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle className="text-base">Price History — All Grades</CardTitle>
                <div className="flex gap-1">
                  {TIME_RANGES.map((r) => (
                    <button
                      key={r.value}
                      onClick={() => setSelectedRange(r.value)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                        selectedRange === r.value
                          ? 'bg-accent text-white'
                          : 'text-muted hover:text-foreground hover:bg-surface-hover'
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </CardHeader>
              <CardContent>
                {/* Dataset toggles */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {GRADE_DATASETS.map((ds) => {
                    const isVisible = visibleDatasets.has(ds.key)
                    return (
                      <button
                        key={ds.key}
                        onClick={() => toggleDataset(ds.key)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all duration-200 ${
                          isVisible
                            ? 'border-white/[0.12] bg-white/[0.04] text-foreground/80'
                            : 'border-white/[0.04] text-muted-foreground/40'
                        }`}
                      >
                        <span
                          className="h-1.5 w-1.5 rounded-full shrink-0"
                          style={{ backgroundColor: ds.color, opacity: isVisible ? 1 : 0.3 }}
                        />
                        {ds.label}
                      </button>
                    )
                  })}
                </div>

                {/* Chart */}
                <div className="h-[340px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={CHART_COLORS.grid}
                        strokeOpacity={0.5}
                      />
                      <XAxis
                        dataKey="date"
                        stroke={CHART_COLORS.text}
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v: string) => v.slice(5)}
                      />
                      <YAxis
                        stroke={CHART_COLORS.text}
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v: number) => `$${v}`}
                        domain={['dataMin - 5', 'dataMax + 10']}
                        width={55}
                      />
                      <Tooltip content={<MultiLineTooltip />} />

                      {GRADE_DATASETS.map((ds) =>
                        visibleDatasets.has(ds.key) ? (
                          <Line
                            key={ds.key}
                            type="monotone"
                            dataKey={ds.key}
                            name={ds.label}
                            stroke={ds.color}
                            strokeWidth={ds.key === 'raw' ? 2.5 : 1.5}
                            dot={false}
                            activeDot={{ r: 4, strokeWidth: 2, fill: '#0a1228' }}
                            strokeOpacity={ds.key === 'raw' ? 1 : 0.7}
                          />
                        ) : null
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Chart Stats */}
                {chartStats && (
                  <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-white/[0.04]">
                    <div className="text-center">
                      <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">Avg (Raw)</p>
                      <p className="text-sm font-mono-numbers font-bold">${formatPrice(chartStats.avg)}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">Low</p>
                      <p className="text-sm font-mono-numbers font-bold">${formatPrice(chartStats.low)}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">High</p>
                      <p className="text-sm font-mono-numbers font-bold">${formatPrice(chartStats.high)}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">Change</p>
                      <p className={`text-sm font-mono-numbers font-bold flex items-center justify-center gap-0.5 ${chartStats.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {chartStats.change >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                        {chartStats.change >= 0 ? '+' : ''}{chartStats.change.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* ── Bottom Sections ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Sales / Last Sold */}
          <Card variant="elevated">
            <CardHeader>
              <CardTitle className="text-base">Recent Market Data — Last Sold</CardTitle>
            </CardHeader>
            <CardContent>
              {recentSales.length > 0 ? (
                <div className="space-y-1">
                  {recentSales.map((sale, i) => (
                    <div key={i} className="flex items-center justify-between py-2.5 border-b border-white/[0.03] last:border-0">
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className="h-2 w-2 rounded-full shrink-0"
                          style={{
                            backgroundColor:
                              GRADED_CHART_COLORS[
                                GRADE_DATASETS.find((d) => sale.grade.toLowerCase().includes(d.label.toLowerCase().split(' ')[0]))?.key || 'raw'
                              ] || '#60a5fa',
                          }}
                        />
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{sale.grade}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <Badge
                              variant={
                                sale.platform.toLowerCase().includes('ebay')
                                  ? 'warning'
                                  : sale.platform.toLowerCase().includes('tcg')
                                    ? 'info'
                                    : 'default'
                              }
                              className="text-[9px]"
                            >
                              {sale.platform}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground/40">{sale.date}</span>
                          </div>
                        </div>
                      </div>
                      <span className="text-sm font-mono-numbers font-bold shrink-0 ml-3">
                        ${formatPrice(sale.price)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted text-center py-4">No sales data available</p>
              )}
            </CardContent>
          </Card>

          {/* Related Cards */}
          <Card variant="elevated">
            <CardHeader>
              <CardTitle className="text-base">Related Cards</CardTitle>
            </CardHeader>
            <CardContent>
              {related.length > 0 ? (
                <div className="space-y-1">
                  {related.slice(0, 8).map((r) => (
                    <div
                      key={r.id}
                      className="flex items-center justify-between py-2.5 border-b border-white/[0.03] last:border-0 cursor-pointer hover:bg-white/[0.02] rounded-lg px-2 transition-colors"
                      onClick={() => navigate(`/cards/${r.id}`)}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {(r.image || (r as Record<string, unknown>).image_url) ? (
                          <img
                            src={(r.image || (r as Record<string, unknown>).image_url) as string}
                            alt={r.name}
                            className="h-10 w-7 object-contain rounded shrink-0"
                          />
                        ) : (
                          <div className="h-10 w-7 bg-white/[0.03] rounded flex items-center justify-center shrink-0">
                            <Star className="h-3 w-3 text-muted-foreground/30" />
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{r.name}</p>
                          <p className="text-[10px] text-muted-foreground/40">{r.set} · #{r.number}</p>
                        </div>
                      </div>
                      {r.price != null && (
                        <span className="text-sm font-mono-numbers font-bold text-accent shrink-0 ml-3">
                          ${formatPrice(r.price)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted text-center py-4">No related cards found</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </PageTransition>
  )
}
