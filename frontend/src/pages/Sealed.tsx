import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Lock, TrendingUp, TrendingDown, DollarSign, Package,
  Calendar, ArrowUpRight, Star, Filter, BarChart3,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { CHART_COLORS } from '@/lib/constants'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Area, AreaChart,
} from 'recharts'

/* ═══════════════════════════════════════════════════════
   Sealed Product Historical Data
   ═══════════════════════════════════════════════════════ */

interface SealedProduct {
  id: string
  name: string
  set: string
  type: 'Booster Box' | 'ETB' | 'UPC' | 'Collection Box' | 'Tin'
  msrp: number
  releaseDate: string
  currentPrice: number
  priceHistory: { date: string; price: number }[]
  notes?: string
}

const SEALED_PRODUCTS: SealedProduct[] = [
  {
    id: 'es-bb', name: 'Evolving Skies Booster Box', set: 'Evolving Skies', type: 'Booster Box',
    msrp: 143.64, releaseDate: '2021-08-27', currentPrice: 389.99,
    priceHistory: [
      { date: '2021-09', price: 140 }, { date: '2022-01', price: 155 }, { date: '2022-06', price: 185 },
      { date: '2023-01', price: 240 }, { date: '2023-06', price: 280 }, { date: '2024-01', price: 320 },
      { date: '2024-06', price: 350 }, { date: '2025-01', price: 370 }, { date: '2025-06', price: 380 },
      { date: '2026-01', price: 389 },
    ],
    notes: 'Most sought-after SWSH set — Eeveelution alt arts drive demand',
  },
  {
    id: 'es-etb', name: 'Evolving Skies ETB', set: 'Evolving Skies', type: 'ETB',
    msrp: 49.99, releaseDate: '2021-08-27', currentPrice: 89.99,
    priceHistory: [
      { date: '2021-09', price: 50 }, { date: '2022-01', price: 55 }, { date: '2022-06', price: 62 },
      { date: '2023-01', price: 70 }, { date: '2023-06', price: 75 }, { date: '2024-01', price: 80 },
      { date: '2024-06', price: 82 }, { date: '2025-01', price: 85 }, { date: '2026-01', price: 89 },
    ],
  },
  {
    id: '151-bb', name: 'Pokemon 151 Booster Box (JP)', set: 'Pokemon 151', type: 'Booster Box',
    msrp: 55.00, releaseDate: '2023-06-16', currentPrice: 115.00,
    priceHistory: [
      { date: '2023-07', price: 72 }, { date: '2023-10', price: 65 }, { date: '2024-01', price: 75 },
      { date: '2024-06', price: 85 }, { date: '2025-01', price: 100 }, { date: '2026-01', price: 115 },
    ],
    notes: 'Japanese booster box — original 151 nostalgia drives premium',
  },
  {
    id: '151-etb', name: 'Pokemon 151 ETB', set: 'Pokemon 151', type: 'ETB',
    msrp: 49.99, releaseDate: '2023-09-22', currentPrice: 64.99,
    priceHistory: [
      { date: '2023-10', price: 75 }, { date: '2024-01', price: 55 }, { date: '2024-06', price: 52 },
      { date: '2025-01', price: 58 }, { date: '2026-01', price: 64 },
    ],
  },
  {
    id: 'pe-etb', name: 'Prismatic Evolutions ETB', set: 'Prismatic Evolutions', type: 'ETB',
    msrp: 59.99, releaseDate: '2025-01-17', currentPrice: 84.99,
    priceHistory: [
      { date: '2025-02', price: 110 }, { date: '2025-04', price: 95 }, { date: '2025-06', price: 85 },
      { date: '2025-09', price: 80 }, { date: '2026-01', price: 84 },
    ],
    notes: 'Still in print — price stabilized after initial hype',
  },
  {
    id: 'ss-bb', name: 'Surging Sparks Booster Box', set: 'Surging Sparks', type: 'Booster Box',
    msrp: 143.64, releaseDate: '2024-11-08', currentPrice: 119.99,
    priceHistory: [
      { date: '2024-11', price: 140 }, { date: '2025-01', price: 125 }, { date: '2025-06', price: 115 },
      { date: '2026-01', price: 119 },
    ],
    notes: 'Below MSRP — still in heavy print run',
  },
  {
    id: 'op-bb', name: 'Obsidian Flames Booster Box', set: 'Obsidian Flames', type: 'Booster Box',
    msrp: 143.64, releaseDate: '2023-08-11', currentPrice: 135.00,
    priceHistory: [
      { date: '2023-09', price: 138 }, { date: '2024-01', price: 125 }, { date: '2024-06', price: 120 },
      { date: '2025-01', price: 128 }, { date: '2026-01', price: 135 },
    ],
  },
  {
    id: 'cel-etb', name: 'Celebrations ETB', set: 'Celebrations', type: 'ETB',
    msrp: 49.99, releaseDate: '2021-10-08', currentPrice: 125.00,
    priceHistory: [
      { date: '2021-10', price: 80 }, { date: '2022-01', price: 65 }, { date: '2022-06', price: 55 },
      { date: '2023-01', price: 68 }, { date: '2023-06', price: 75 }, { date: '2024-01', price: 90 },
      { date: '2024-06', price: 100 }, { date: '2025-01', price: 115 }, { date: '2026-01', price: 125 },
    ],
    notes: '25th anniversary set — iconic reprints drive collector demand',
  },
  {
    id: 'upc-151', name: 'Pokemon 151 UPC', set: 'Pokemon 151', type: 'UPC',
    msrp: 119.99, releaseDate: '2023-10-06', currentPrice: 210.00,
    priceHistory: [
      { date: '2023-11', price: 180 }, { date: '2024-01', price: 160 }, { date: '2024-06', price: 175 },
      { date: '2025-01', price: 195 }, { date: '2026-01', price: 210 },
    ],
    notes: 'Gold metal Mew card included — very limited print',
  },
  {
    id: 'cr-bb', name: 'Crown Zenith Booster Box', set: 'Crown Zenith', type: 'Booster Box',
    msrp: 143.64, releaseDate: '2023-01-20', currentPrice: 175.00,
    priceHistory: [
      { date: '2023-02', price: 142 }, { date: '2023-06', price: 135 }, { date: '2024-01', price: 145 },
      { date: '2024-06', price: 155 }, { date: '2025-01', price: 165 }, { date: '2026-01', price: 175 },
    ],
    notes: 'Galarian Gallery alt arts — final SWSH era set',
  },
  {
    id: 'ar-bb', name: 'Astral Radiance Booster Box', set: 'Astral Radiance', type: 'Booster Box',
    msrp: 143.64, releaseDate: '2022-05-27', currentPrice: 165.00,
    priceHistory: [
      { date: '2022-06', price: 140 }, { date: '2022-12', price: 130 }, { date: '2023-06', price: 135 },
      { date: '2024-01', price: 145 }, { date: '2024-06', price: 150 }, { date: '2025-06', price: 160 },
      { date: '2026-01', price: 165 },
    ],
  },
  {
    id: 'bs-bb', name: 'Brilliant Stars Booster Box', set: 'Brilliant Stars', type: 'Booster Box',
    msrp: 143.64, releaseDate: '2022-02-25', currentPrice: 180.00,
    priceHistory: [
      { date: '2022-03', price: 142 }, { date: '2022-06', price: 135 }, { date: '2023-01', price: 140 },
      { date: '2023-06', price: 150 }, { date: '2024-01', price: 160 }, { date: '2025-01', price: 172 },
      { date: '2026-01', price: 180 },
    ],
    notes: 'Charizard VSTAR & Trainer Gallery chase cards',
  },
]

const CATEGORY_FILTERS = ['All', 'Booster Box', 'ETB', 'UPC', 'Collection Box'] as const

/* ═══════════════════════════════════════════════════════ */

export default function Sealed() {
  const [selectedProduct, setSelectedProduct] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState<string>('All')
  const [sortBy, setSortBy] = useState<'roi' | 'price' | 'name' | 'date'>('roi')

  const filtered = useMemo(() => {
    let list = [...SEALED_PRODUCTS]
    if (categoryFilter !== 'All') {
      list = list.filter((p) => p.type === categoryFilter)
    }
    switch (sortBy) {
      case 'roi':
        return list.sort((a, b) => ((b.currentPrice - b.msrp) / b.msrp) - ((a.currentPrice - a.msrp) / a.msrp))
      case 'price':
        return list.sort((a, b) => b.currentPrice - a.currentPrice)
      case 'name':
        return list.sort((a, b) => a.name.localeCompare(b.name))
      case 'date':
        return list.sort((a, b) => new Date(b.releaseDate).getTime() - new Date(a.releaseDate).getTime())
    }
  }, [categoryFilter, sortBy])

  const selected = SEALED_PRODUCTS.find((p) => p.id === selectedProduct)

  // Summary stats
  const totalMSRP = SEALED_PRODUCTS.reduce((s, p) => s + p.msrp, 0)
  const totalCurrent = SEALED_PRODUCTS.reduce((s, p) => s + p.currentPrice, 0)
  const bestPerformer = [...SEALED_PRODUCTS].sort((a, b) =>
    ((b.currentPrice - b.msrp) / b.msrp) - ((a.currentPrice - a.msrp) / a.msrp)
  )[0]
  const avgROI = ((totalCurrent - totalMSRP) / totalMSRP) * 100

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <motion.h1
            className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            Sealed Product Tracker
          </motion.h1>
          <motion.p
            className="text-muted-foreground/60 text-sm mt-1"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            Track sealed product appreciation — booster boxes, ETBs &amp; UPCs as investments
          </motion.p>
        </div>

        {/* Summary KPIs */}
        <motion.div
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-1.5 rounded-lg bg-accent-muted"><Package className="w-4 h-4 text-accent" /></div>
                  <span className="text-xs text-muted">Products Tracked</span>
                </div>
                <p className="text-2xl font-mono-numbers font-bold">{SEALED_PRODUCTS.length}</p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-1.5 rounded-lg bg-success-muted"><TrendingUp className="w-4 h-4 text-success" /></div>
                  <span className="text-xs text-muted">Avg ROI</span>
                </div>
                <p className={`text-2xl font-mono-numbers font-bold ${avgROI >= 0 ? 'text-success' : 'text-danger'}`}>
                  {avgROI >= 0 ? '+' : ''}{avgROI.toFixed(1)}%
                </p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-1.5 rounded-lg bg-warning-muted"><Star className="w-4 h-4 text-warning" /></div>
                  <span className="text-xs text-muted">Best Performer</span>
                </div>
                <p className="text-sm font-bold truncate">{bestPerformer?.name.replace(' Booster Box', ' BB').replace(' ETB', '')}</p>
                <p className="text-xs text-success font-mono-numbers">
                  +{(((bestPerformer?.currentPrice || 0) - (bestPerformer?.msrp || 1)) / (bestPerformer?.msrp || 1) * 100).toFixed(0)}%
                </p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-1.5 rounded-lg bg-info-muted"><DollarSign className="w-4 h-4 text-info" /></div>
                  <span className="text-xs text-muted">Total Market Value</span>
                </div>
                <p className="text-2xl font-mono-numbers font-bold">${formatPrice(totalCurrent)}</p>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>

        {/* Selected Product Chart */}
        <AnimatePresence mode="wait">
          {selected && (
            <motion.div
              key={selected.id}
              initial={{ opacity: 0, y: 20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.4, type: 'spring', bounce: 0.15 }}
            >
              <Card variant="elevated">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-accent" />
                      {selected.name}
                    </CardTitle>
                    <div className="flex items-center gap-3 text-sm">
                      <Badge variant="default">{selected.type}</Badge>
                      <span className="text-muted font-mono-numbers">MSRP ${selected.msrp}</span>
                      <span className="text-accent font-mono-numbers font-bold">${formatPrice(selected.currentPrice)}</span>
                      <Badge variant={selected.currentPrice >= selected.msrp ? 'success' : 'danger'}>
                        {selected.currentPrice >= selected.msrp ? '+' : ''}
                        {(((selected.currentPrice - selected.msrp) / selected.msrp) * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={selected.priceHistory}>
                        <defs>
                          <linearGradient id="sealedGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.15} />
                            <stop offset="100%" stopColor="#60a5fa" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                        <XAxis dataKey="date" tick={{ fill: CHART_COLORS.text, fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: CHART_COLORS.text, fontSize: 11 }} tickFormatter={(v) => `$${v}`} axisLine={false} tickLine={false} />
                        <Tooltip
                          contentStyle={{
                            background: CHART_COLORS.tooltip,
                            border: `1px solid ${CHART_COLORS.grid}`,
                            borderRadius: 12,
                          }}
                          formatter={(value: number) => [`$${formatPrice(value)}`, 'Price']}
                        />
                        <Area type="monotone" dataKey="price" stroke="#60a5fa" strokeWidth={2.5} fill="url(#sealedGrad)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  {selected.notes && (
                    <p className="text-xs text-muted mt-3 italic">{selected.notes}</p>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-1.5">
            {CATEGORY_FILTERS.map((cat) => (
              <Button
                key={cat}
                variant={categoryFilter === cat ? 'default' : 'outline'}
                size="sm"
                onClick={() => setCategoryFilter(cat)}
              >
                {cat}
              </Button>
            ))}
          </div>
          <Select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            options={[
              { value: 'roi', label: 'Sort by ROI' },
              { value: 'price', label: 'Sort by Price' },
              { value: 'name', label: 'Sort by Name' },
              { value: 'date', label: 'Sort by Release Date' },
            ]}
          />
        </div>

        {/* Product Grid */}
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {filtered.map((product) => {
            const roi = ((product.currentPrice - product.msrp) / product.msrp) * 100
            const isSelected = product.id === selectedProduct
            const yearsSince = (new Date().getTime() - new Date(product.releaseDate).getTime()) / (365.25 * 24 * 60 * 60 * 1000)
            const annualizedROI = yearsSince > 0 ? roi / yearsSince : roi
            return (
              <motion.div key={product.id} variants={staggerItem}>
                <motion.button
                  onClick={() => setSelectedProduct(isSelected ? '' : product.id)}
                  className={`w-full text-left transition-all ${isSelected ? '' : ''}`}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card hover className={isSelected ? 'ring-2 ring-accent/40 border-accent/30' : ''}>
                    <CardContent className="p-4 space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold text-sm">{product.name}</h3>
                          <p className="text-xs text-muted mt-0.5">{product.set} · {product.type}</p>
                        </div>
                        <Badge variant={roi >= 0 ? 'success' : 'danger'} className="shrink-0">
                          {roi >= 0 ? '+' : ''}{roi.toFixed(0)}%
                        </Badge>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div>
                          <p className="text-[10px] text-muted uppercase">MSRP</p>
                          <p className="font-mono-numbers text-sm">${product.msrp.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted uppercase">Current</p>
                          <p className="font-mono-numbers text-sm font-bold text-accent">${formatPrice(product.currentPrice)}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted uppercase">Annual</p>
                          <p className={`font-mono-numbers text-sm ${annualizedROI >= 0 ? 'text-success' : 'text-danger'}`}>
                            {annualizedROI >= 0 ? '+' : ''}{annualizedROI.toFixed(1)}%/yr
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-xs text-muted">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          <span>{new Date(product.releaseDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</span>
                        </div>
                        <span className={`font-mono-numbers ${roi >= 0 ? 'text-success' : 'text-danger'}`}>
                          {roi >= 0 ? '+' : ''}${formatPrice(product.currentPrice - product.msrp)}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.button>
              </motion.div>
            )
          })}
        </motion.div>

        {/* Investment Tips */}
        <Card>
          <CardContent className="p-5">
            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Lock className="h-4 w-4 text-accent" /> Sealed Product Investment Tips
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-muted">
              <div>
                <p className="font-medium text-foreground mb-1">Best Appreciation</p>
                <p>Booster boxes from out-of-print sets with iconic chase cards appreciate most. Evolving Skies &amp; Celebrations are prime examples.</p>
              </div>
              <div>
                <p className="font-medium text-foreground mb-1">When to Buy</p>
                <p>Buy at MSRP or below during heavy print runs. Products typically dip 3-6 months after release before appreciating once out of print.</p>
              </div>
              <div>
                <p className="font-medium text-foreground mb-1">Storage</p>
                <p>Keep sealed products in a cool, dry environment. Acrylic cases protect from shelf wear. Condition matters for resale value.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  )
}
