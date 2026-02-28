import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  TrendingUp, Package, DollarSign, BarChart3,
  ChevronDown, Sparkles, Zap, Target, ArrowUpRight,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Select } from '@/components/ui/Select'
import { Progress } from '@/components/ui/Progress'
import { Skeleton } from '@/components/ui/Skeleton'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { PRODUCT_MSRP, CHART_COLORS } from '@/lib/constants'
import { useSets, useChaseCards, usePullRates } from '@/hooks/useApi'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

/* ═══════════════════════════════════════════════════════
   Pack EV Calculator — Expected Value per pack/product
   ═══════════════════════════════════════════════════════ */

interface RarityTier {
  rarity: string
  cardCount: number
  avgPrice: number
  pullRate: number
  evContribution: number
}

const PRODUCT_TYPES = [
  { key: 'pack', label: 'Single Pack', packs: 1, msrp: PRODUCT_MSRP.pack },
  { key: 'boosterBox', label: 'Booster Box (36)', packs: 36, msrp: PRODUCT_MSRP.boosterBox },
  { key: 'etb', label: 'ETB (9 packs)', packs: 9, msrp: PRODUCT_MSRP.etb },
  { key: 'boosterBundle', label: 'Bundle (6 packs)', packs: 6, msrp: PRODUCT_MSRP.boosterBundle },
]

/* Fallback pull rate estimates when API doesn't return data */
const FALLBACK_PULL_RATES: Record<string, number> = {
  'Special Art Rare': 0.018,
  'Illustration Rare': 0.05,
  'Ultra Rare': 0.11,
  'Hyper Rare': 0.02,
  'Full Art': 0.06,
  'ACE SPEC Rare': 0.04,
  'Double Rare': 0.12,
  'Rare Holo': 0.33,
  'Rare': 0.33,
  'Uncommon': 1.0,
  'Common': 3.0,
}

function getRarityCategory(rarity: string): string {
  const r = rarity.toLowerCase()
  if (r.includes('special art') || r.includes('sar')) return 'Special Art Rare'
  if (r.includes('illustration') || r.includes('ir')) return 'Illustration Rare'
  if (r.includes('hyper') || r.includes('gold') || r.includes('secret')) return 'Hyper Rare'
  if (r.includes('full art')) return 'Full Art'
  if (r.includes('ultra') || r.includes('ex') || r.includes('v ') || r.includes('vmax') || r.includes('vstar')) return 'Ultra Rare'
  if (r.includes('ace spec')) return 'ACE SPEC Rare'
  if (r.includes('double')) return 'Double Rare'
  if (r.includes('holo') && r.includes('rare')) return 'Rare Holo'
  if (r.includes('rare')) return 'Rare'
  if (r.includes('uncommon')) return 'Uncommon'
  return 'Common'
}

function getRarityColor(rarity: string): string {
  if (rarity.includes('Special Art')) return '#f43f5e'
  if (rarity.includes('Illustration')) return '#a855f7'
  if (rarity.includes('Hyper') || rarity.includes('Gold')) return '#eab308'
  if (rarity.includes('Full Art')) return '#f97316'
  if (rarity.includes('Ultra')) return '#3b82f6'
  if (rarity.includes('ACE')) return '#22d3ee'
  if (rarity.includes('Double')) return '#818cf8'
  if (rarity.includes('Holo')) return '#60a5fa'
  if (rarity.includes('Rare')) return '#34d399'
  if (rarity.includes('Uncommon')) return '#94a3b8'
  return '#64748b'
}

export default function PackEV() {
  const [selectedSet, setSelectedSet] = useState('')
  const [productType, setProductType] = useState('pack')

  const { data: setsData, isLoading: setsLoading } = useSets()
  const { data: cardsData, isLoading: cardsLoading } = useChaseCards(selectedSet, undefined, 500)
  const { data: pullRateData } = usePullRates(selectedSet)

  const sets = setsData?.data || []
  const cards = cardsData?.data || []

  // Build pull rate map from API or fallback
  const pullRateMap = useMemo(() => {
    const map: Record<string, number> = { ...FALLBACK_PULL_RATES }
    if (pullRateData?.data) {
      for (const pr of pullRateData.data) {
        const key = pr.rarity || (pr as Record<string, unknown>).label as string || (pr as Record<string, unknown>).category as string
        if (key && pr.rate) {
          map[key] = pr.rate
        }
      }
    }
    return map
  }, [pullRateData])

  // Calculate EV breakdown by rarity
  const { tiers, totalEV } = useMemo(() => {
    if (cards.length === 0) return { tiers: [] as RarityTier[], totalEV: 0 }

    const grouped: Record<string, { prices: number[]; count: number }> = {}
    for (const card of cards) {
      const rarity = getRarityCategory(card.rarity || 'Common')
      if (!grouped[rarity]) grouped[rarity] = { prices: [], count: 0 }
      const price = card.price || (card as Record<string, unknown>).tcgplayer_market as number || 0
      grouped[rarity].prices.push(price)
      grouped[rarity].count++
    }

    let ev = 0
    const tierList: RarityTier[] = Object.entries(grouped)
      .map(([rarity, data]) => {
        const avgPrice = data.prices.reduce((s, p) => s + p, 0) / data.prices.length
        const pullRate = pullRateMap[rarity] || 0.01
        const evContribution = avgPrice * pullRate
        ev += evContribution
        return {
          rarity,
          cardCount: data.count,
          avgPrice,
          pullRate,
          evContribution,
        }
      })
      .sort((a, b) => b.evContribution - a.evContribution)

    return { tiers: tierList, totalEV: ev }
  }, [cards, pullRateMap])

  const product = PRODUCT_TYPES.find((p) => p.key === productType) || PRODUCT_TYPES[0]
  const productEV = totalEV * product.packs
  const productMSRP = product.msrp
  const evRatio = productMSRP > 0 ? (productEV / productMSRP) * 100 : 0
  const evProfit = productEV - productMSRP

  // Chart data for rarity breakdown
  const chartData = tiers.map((t) => ({
    rarity: t.rarity.replace(' Rare', '').replace('Special Art', 'SAR'),
    ev: parseFloat(t.evContribution.toFixed(2)),
    color: getRarityColor(t.rarity),
  }))

  // Set options
  const setOptions = sets.map((s) => ({ value: s.id, label: `${s.name} (${s.series})` }))

  const isLoading = cardsLoading && !!selectedSet

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <motion.h1
            className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            Pack EV Calculator
          </motion.h1>
          <motion.p
            className="text-muted-foreground/60 text-sm mt-1"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            Calculate expected value per pack — find the most profitable sets to open
          </motion.p>
        </div>

        {/* Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
        >
          <Card variant="elevated">
            <CardContent className="p-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select
                  label="Select Set"
                  value={selectedSet}
                  onChange={(e) => setSelectedSet(e.target.value)}
                  options={[{ value: '', label: 'Choose a set...' }, ...setOptions]}
                />
                <Select
                  label="Product Type"
                  value={productType}
                  onChange={(e) => setProductType(e.target.value)}
                  options={PRODUCT_TYPES.map((p) => ({
                    value: p.key,
                    label: `${p.label} — $${p.msrp.toFixed(2)}`,
                  }))}
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Loading */}
        {isLoading && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} variant="elevated">
                <CardContent className="p-4">
                  <Skeleton className="h-4 w-20 mb-2" />
                  <Skeleton className="h-8 w-24" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Results */}
        <AnimatePresence>
          {selectedSet && cards.length > 0 && !isLoading && (
            <motion.div
              key={selectedSet}
              initial={{ opacity: 0, y: 30, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5, type: 'spring', bounce: 0.2 }}
              className="space-y-6"
            >
              {/* Summary KPIs */}
              <motion.div
                className="grid grid-cols-2 md:grid-cols-5 gap-4"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
              >
                <motion.div variants={staggerItem}>
                  <Card variant="elevated" className="overflow-hidden relative">
                    <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent" />
                    <CardContent className="p-4 text-center relative">
                      <p className="text-xs text-muted mb-1">EV / Pack</p>
                      <p className="text-2xl font-mono-numbers font-bold text-accent">
                        ${formatPrice(totalEV)}
                      </p>
                      <p className="text-[10px] text-muted mt-1">Expected value</p>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={staggerItem}>
                  <Card variant="elevated">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-muted mb-1">Pack MSRP</p>
                      <p className="text-2xl font-mono-numbers font-bold">${PRODUCT_MSRP.pack}</p>
                      <p className="text-[10px] text-muted mt-1">Retail price</p>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={staggerItem}>
                  <Card variant={evRatio >= 100 ? 'accent' : 'default'}>
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-muted mb-1">EV Ratio</p>
                      <p className={`text-2xl font-mono-numbers font-bold ${evRatio >= 100 ? 'text-success' : 'text-warning'}`}>
                        {evRatio.toFixed(0)}%
                      </p>
                      <p className="text-[10px] text-muted mt-1">{evRatio >= 100 ? 'Positive EV!' : 'Negative EV'}</p>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={staggerItem}>
                  <Card variant="elevated">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-muted mb-1">{product.label} EV</p>
                      <p className="text-2xl font-mono-numbers font-bold text-accent">
                        ${formatPrice(productEV)}
                      </p>
                      <p className="text-[10px] text-muted mt-1">vs ${product.msrp} MSRP</p>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={staggerItem}>
                  <Card variant={evProfit >= 0 ? 'accent' : 'danger'}>
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-muted mb-1">Profit/Loss</p>
                      <p className={`text-2xl font-mono-numbers font-bold ${evProfit >= 0 ? 'text-success' : 'text-danger'}`}>
                        {evProfit >= 0 ? '+' : ''}${formatPrice(evProfit)}
                      </p>
                      <p className="text-[10px] text-muted mt-1">per {product.label.toLowerCase()}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>

              {/* EV Breakdown Chart + Table */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Bar Chart */}
                <motion.div
                  initial={{ opacity: 0, x: -30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.2 }}
                >
                  <Card variant="elevated">
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <BarChart3 className="h-4 w-4 text-accent" /> EV Contribution by Rarity
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[280px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
                            <XAxis
                              type="number"
                              tick={{ fill: CHART_COLORS.text, fontSize: 11 }}
                              tickFormatter={(v) => `$${v.toFixed(2)}`}
                              axisLine={false}
                              tickLine={false}
                            />
                            <YAxis
                              type="category"
                              dataKey="rarity"
                              tick={{ fill: CHART_COLORS.text, fontSize: 11 }}
                              axisLine={false}
                              tickLine={false}
                              width={75}
                            />
                            <Tooltip
                              contentStyle={{
                                background: CHART_COLORS.tooltip,
                                border: `1px solid ${CHART_COLORS.grid}`,
                                borderRadius: 12,
                                fontSize: 12,
                              }}
                              formatter={(value: number) => [`$${value.toFixed(3)}`, 'EV Contribution']}
                              cursor={{ fill: 'rgba(96, 165, 250, 0.05)' }}
                            />
                            <Bar dataKey="ev" radius={[0, 6, 6, 0]}>
                              {chartData.map((entry, i) => (
                                <Cell key={i} fill={entry.color} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Breakdown Table */}
                <motion.div
                  initial={{ opacity: 0, x: 30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.3 }}
                >
                  <Card variant="elevated">
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-accent" /> Rarity Breakdown
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {tiers.map((tier, i) => (
                          <motion.div
                            key={tier.rarity}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.1 * i, duration: 0.4 }}
                            className="space-y-1.5"
                          >
                            <div className="flex items-center justify-between text-sm">
                              <div className="flex items-center gap-2">
                                <span
                                  className="w-2.5 h-2.5 rounded-full shrink-0"
                                  style={{ backgroundColor: getRarityColor(tier.rarity) }}
                                />
                                <span className="font-medium">{tier.rarity}</span>
                                <span className="text-xs text-muted">({tier.cardCount} cards)</span>
                              </div>
                              <div className="flex items-center gap-3 text-xs font-mono-numbers">
                                <span className="text-muted">Avg ${formatPrice(tier.avgPrice)}</span>
                                <span className="text-accent font-bold">+${tier.evContribution.toFixed(3)}</span>
                              </div>
                            </div>
                            <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                              <motion.div
                                className="h-full rounded-full"
                                style={{ backgroundColor: getRarityColor(tier.rarity) }}
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.min(100, (tier.evContribution / (totalEV || 1)) * 100)}%` }}
                                transition={{ duration: 0.8, delay: 0.15 * i, ease: 'easeOut' }}
                              />
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </div>

              {/* Product Comparison */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4 }}
              >
                <Card variant="elevated">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Package className="h-4 w-4 text-accent" /> Product Comparison
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      {PRODUCT_TYPES.map((p, i) => {
                        const pEV = totalEV * p.packs
                        const pProfit = pEV - p.msrp
                        const pRatio = (pEV / p.msrp) * 100
                        const isSelected = p.key === productType
                        return (
                          <motion.button
                            key={p.key}
                            onClick={() => setProductType(p.key)}
                            className={`text-left p-4 rounded-xl border transition-all ${
                              isSelected
                                ? 'border-accent/40 bg-accent/5 ring-1 ring-accent/20'
                                : 'border-border hover:border-border-light hover:bg-surface-hover'
                            }`}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 * i }}
                          >
                            <p className="font-semibold text-sm mb-2">{p.label}</p>
                            <div className="space-y-1 text-xs">
                              <div className="flex justify-between">
                                <span className="text-muted">MSRP</span>
                                <span className="font-mono-numbers">${p.msrp.toFixed(2)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted">EV</span>
                                <span className="font-mono-numbers text-accent">${formatPrice(pEV)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted">Profit</span>
                                <span className={`font-mono-numbers font-bold ${pProfit >= 0 ? 'text-success' : 'text-danger'}`}>
                                  {pProfit >= 0 ? '+' : ''}${formatPrice(pProfit)}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted">$/Pack</span>
                                <span className="font-mono-numbers">${(p.msrp / p.packs).toFixed(2)}</span>
                              </div>
                            </div>
                          </motion.button>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Verdict */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: 0.5, type: 'spring' }}
              >
                <Card variant={evRatio >= 100 ? 'accent' : evRatio >= 75 ? 'default' : 'danger'}>
                  <CardContent className="p-6 flex items-center gap-4">
                    <div className={`p-3 rounded-2xl ${evRatio >= 100 ? 'bg-success/10' : evRatio >= 75 ? 'bg-warning/10' : 'bg-danger/10'}`}>
                      {evRatio >= 100 ? (
                        <Zap className="w-8 h-8 text-success" />
                      ) : evRatio >= 75 ? (
                        <Target className="w-8 h-8 text-warning" />
                      ) : (
                        <TrendingUp className="w-8 h-8 text-danger" />
                      )}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold">
                        {evRatio >= 100 ? 'Positive EV — Rip It!' : evRatio >= 75 ? 'Close to Break-Even' : 'Negative EV — Buy Singles'}
                      </h3>
                      <p className="text-sm text-muted mt-1">
                        {evRatio >= 100
                          ? `This set has a ${evRatio.toFixed(0)}% EV ratio. On average, you get $${formatPrice(totalEV)} of value per $${PRODUCT_MSRP.pack} pack. Best product: ${PRODUCT_TYPES.reduce((best, p) => (totalEV * p.packs - p.msrp > totalEV * best.packs - best.msrp ? p : best)).label}.`
                          : evRatio >= 75
                          ? `This set has a ${evRatio.toFixed(0)}% EV ratio. You're close to break-even but chase card hits make the variance high. Consider buying singles for specific cards.`
                          : `This set has a ${evRatio.toFixed(0)}% EV ratio — you'll lose money on average opening packs. Buy the singles you want instead.`
                        }
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty State */}
        {!selectedSet && (
          <motion.div
            className="flex flex-col items-center justify-center py-20 text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <motion.div
              className="flex h-20 w-20 items-center justify-center rounded-2xl bg-accent-muted mb-6"
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            >
              <TrendingUp className="h-10 w-10 text-accent" />
            </motion.div>
            <h3 className="text-xl font-semibold text-foreground">Select a Set</h3>
            <p className="mt-2 max-w-md text-sm text-muted">
              Choose a Pokemon TCG set above to calculate the expected value per pack and compare across product types.
            </p>
          </motion.div>
        )}
      </div>
    </PageTransition>
  )
}
