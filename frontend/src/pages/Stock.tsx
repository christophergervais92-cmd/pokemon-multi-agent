import { useState, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  Search, Package, MapPin, Store, ShoppingCart, Boxes,
  ExternalLink, Clock, Tag, TrendingUp, AlertCircle,
  CheckCircle, XCircle, RefreshCw, Star,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { RETAILERS } from '@/lib/constants'
import { formatPrice } from '@/lib/utils'

/* ═══════════════════════════════════════════════════════
   Trending Products & MSRP Reference Data
   ═══════════════════════════════════════════════════════ */

interface TrendingProduct {
  name: string
  category: string
  msrp: number
  currentAvg: number
  demand: 'extreme' | 'high' | 'medium' | 'low'
  inStockRate: number
  lastSeen: string
  retailers: string[]
}

const TRENDING_PRODUCTS: TrendingProduct[] = [
  {
    name: 'Prismatic Evolutions ETB',
    category: 'ETB',
    msrp: 59.99,
    currentAvg: 84.99,
    demand: 'extreme',
    inStockRate: 8,
    lastSeen: '2h ago (Target)',
    retailers: ['Target', 'Walmart', 'Pokemon Center'],
  },
  {
    name: 'Prismatic Evolutions Booster Bundle',
    category: 'Bundle',
    msrp: 29.99,
    currentAvg: 44.99,
    demand: 'extreme',
    inStockRate: 12,
    lastSeen: '4h ago (Pokemon Center)',
    retailers: ['Target', 'Best Buy', 'Pokemon Center'],
  },
  {
    name: 'Journey Together Booster Box',
    category: 'Booster Box',
    msrp: 143.64,
    currentAvg: 139.99,
    demand: 'high',
    inStockRate: 45,
    lastSeen: 'In Stock',
    retailers: ['All Retailers'],
  },
  {
    name: 'Journey Together ETB',
    category: 'ETB',
    msrp: 49.99,
    currentAvg: 49.99,
    demand: 'high',
    inStockRate: 62,
    lastSeen: 'In Stock',
    retailers: ['All Retailers'],
  },
  {
    name: 'Surging Sparks Booster Box',
    category: 'Booster Box',
    msrp: 143.64,
    currentAvg: 119.99,
    demand: 'medium',
    inStockRate: 78,
    lastSeen: 'In Stock',
    retailers: ['Walmart', 'Amazon', 'TCGPlayer'],
  },
  {
    name: 'Prismatic Evolutions Mini Tin',
    category: 'Tin',
    msrp: 7.99,
    currentAvg: 12.99,
    demand: 'high',
    inStockRate: 15,
    lastSeen: '6h ago (Walmart)',
    retailers: ['Target', 'Walmart'],
  },
  {
    name: 'Evolving Skies Booster Box',
    category: 'Booster Box',
    msrp: 143.64,
    currentAvg: 389.99,
    demand: 'high',
    inStockRate: 0,
    lastSeen: 'Out of Print',
    retailers: ['TCGPlayer', 'eBay'],
  },
  {
    name: 'Pokemon 151 ETB',
    category: 'ETB',
    msrp: 49.99,
    currentAvg: 62.99,
    demand: 'medium',
    inStockRate: 25,
    lastSeen: '1d ago',
    retailers: ['Walmart', 'GameStop'],
  },
]

/* ── MSRP Reference ── */
interface MSRPProduct {
  type: string
  msrp: number
  packs: number
  costPerPack: number
  notes: string
}

const MSRP_REFERENCE: MSRPProduct[] = [
  { type: 'Booster Box (36 packs)', msrp: 143.64, packs: 36, costPerPack: 3.99, notes: 'Best value per pack' },
  { type: 'Elite Trainer Box', msrp: 49.99, packs: 9, costPerPack: 5.55, notes: 'Includes sleeves, dice, storage' },
  { type: 'Booster Bundle (6 packs)', msrp: 29.99, packs: 6, costPerPack: 5.00, notes: 'Good entry point' },
  { type: '3-Pack Blister', msrp: 14.99, packs: 3, costPerPack: 5.00, notes: 'Includes promo card' },
  { type: 'Single Booster Pack', msrp: 4.49, packs: 1, costPerPack: 4.49, notes: 'Retail singles' },
  { type: 'Collection Box', msrp: 24.99, packs: 4, costPerPack: 6.25, notes: 'Includes promo + packs' },
  { type: 'Ultra Premium Collection', msrp: 119.99, packs: 16, costPerPack: 7.50, notes: 'Premium extras included' },
  { type: 'Build & Battle Box', msrp: 14.99, packs: 4, costPerPack: 3.75, notes: 'Pre-release kit' },
]

/* ── Retailer Stock Tips ── */
interface RetailerTip {
  retailer: string
  color: string
  restockDays: string
  tipText: string
  dpci?: string
  onlineUrl?: string
}

const RETAILER_TIPS: RetailerTip[] = [
  { retailer: 'Target', color: '#cc0000', restockDays: 'Tue/Fri', tipText: 'Check DPCI for specific products. Restocks usually at open. Use Popfindr or BrickSeek for inventory checks.', dpci: '087-35-XXXX' },
  { retailer: 'Walmart', color: '#0071dc', restockDays: 'Mon/Thu', tipText: 'Third-party vendor stocked. Check clearance endcaps. Online restocks typically happen late evening EST.' },
  { retailer: 'Best Buy', color: '#0046be', restockDays: 'Variable', tipText: 'Online drops with occasional in-store. Sign up for restock alerts. Good for exclusives.' },
  { retailer: 'GameStop', color: '#e21e26', restockDays: 'Varies', tipText: 'Pre-orders available early. PowerUp Rewards members get early access to some products.' },
  { retailer: 'Pokemon Center', color: '#ffcb05', restockDays: 'Random', tipText: 'Best for exclusives. Often releases at 9AM PT. Use auto-checkout tools (at your own risk).' },
  { retailer: 'Costco', color: '#e31837', restockDays: 'Weekly', tipText: 'Bulk bundles at great per-pack prices. Membership required. Check warehouse inventory online.' },
]

/* ═══════════════════════════════════════════════════════ */

function getDemandBadge(demand: TrendingProduct['demand']) {
  switch (demand) {
    case 'extreme': return { variant: 'danger' as const, label: 'Extreme Demand' }
    case 'high': return { variant: 'warning' as const, label: 'High Demand' }
    case 'medium': return { variant: 'success' as const, label: 'Available' }
    case 'low': return { variant: 'default' as const, label: 'Easy to Find' }
  }
}

export default function Stock() {
  const [zip, setZip] = useState('')
  const [productQuery, setProductQuery] = useState('')
  const [activeRetailer, setActiveRetailer] = useState('all')
  const [isSearching, setIsSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const filteredProducts = useMemo(() => {
    if (!productQuery.trim() && !hasSearched) return TRENDING_PRODUCTS
    const q = productQuery.toLowerCase()
    return TRENDING_PRODUCTS.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q)
    ).filter(
      (p) =>
        activeRetailer === 'all' ||
        p.retailers.some((r) => r.toLowerCase().includes(activeRetailer))
    )
  }, [productQuery, activeRetailer, hasSearched])

  const handleSearch = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault()
      if (!productQuery.trim()) return
      setIsSearching(true)
      setHasSearched(true)
      setTimeout(() => setIsSearching(false), 800)
    },
    [productQuery]
  )

  return (
    <PageTransition>
      <div className="space-y-8 pb-8">
        {/* Header */}
        <div className="page-header">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">
            Stock Finder
          </h1>
          <p className="mt-1 text-muted-foreground/60 text-sm">
            Find Pokemon products in stock — MSRP tracker &amp; retailer intel
          </p>
        </div>

        {/* Search Form */}
        <Card>
          <CardContent>
            <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
              <Input
                placeholder="ZIP code"
                value={zip}
                onChange={(e) => setZip(e.target.value)}
                icon={<MapPin className="h-4 w-4" />}
                className="w-full sm:w-32"
              />
              <div className="flex-1">
                <Input
                  placeholder="Search products (e.g. Prismatic Evolutions ETB)"
                  value={productQuery}
                  onChange={(e) => setProductQuery(e.target.value)}
                  icon={<Search className="h-4 w-4" />}
                />
              </div>
              <Button type="submit" isLoading={isSearching} className="shrink-0">
                <Search className="h-4 w-4" /> Search
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Retailer Quick Filters */}
        <div className="flex flex-wrap gap-2">
          {RETAILERS.map((r) => (
            <button
              key={r.id}
              onClick={() => setActiveRetailer(r.id)}
              className="transition-all"
            >
              <Badge
                variant={activeRetailer === r.id ? 'accent' : 'default'}
                className={
                  activeRetailer === r.id
                    ? 'ring-1 ring-accent/40 cursor-pointer'
                    : 'cursor-pointer hover:bg-surface-hover'
                }
              >
                <span
                  className="inline-block h-2 w-2 rounded-full mr-1.5 shrink-0"
                  style={{ backgroundColor: r.color }}
                />
                {r.name}
              </Badge>
            </button>
          ))}
        </div>

        {/* Trending / Search Results */}
        <div>
          <h2 className="text-lg font-semibold mb-4">
            {hasSearched ? `Results for "${productQuery}"` : 'Trending Products'}
          </h2>

          {isSearching ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : filteredProducts.length > 0 ? (
            <motion.div
              className="grid grid-cols-1 md:grid-cols-2 gap-4"
              variants={staggerContainer}
              initial="initial"
              animate="animate"
            >
              {filteredProducts.map((product) => {
                const demandBadge = getDemandBadge(product.demand)
                const isPremium = product.currentAvg > product.msrp * 1.1
                const isBelow = product.currentAvg < product.msrp * 0.95
                return (
                  <motion.div key={product.name} variants={staggerItem}>
                    <Card hover>
                      <CardContent className="p-4 space-y-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="font-semibold">{product.name}</h3>
                            <p className="text-xs text-muted mt-0.5">{product.category}</p>
                          </div>
                          <Badge variant={demandBadge.variant} className="text-[10px] shrink-0">
                            {demandBadge.label}
                          </Badge>
                        </div>

                        <div className="grid grid-cols-3 gap-3 text-center">
                          <div>
                            <p className="text-[10px] text-muted uppercase">MSRP</p>
                            <p className="font-mono-numbers font-bold text-sm">${product.msrp.toFixed(2)}</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-muted uppercase">Market Avg</p>
                            <p className={`font-mono-numbers font-bold text-sm ${
                              isPremium ? 'text-danger' : isBelow ? 'text-success' : 'text-foreground'
                            }`}>
                              ${product.currentAvg.toFixed(2)}
                            </p>
                          </div>
                          <div>
                            <p className="text-[10px] text-muted uppercase">In-Stock</p>
                            <p className={`font-mono-numbers font-bold text-sm ${
                              product.inStockRate >= 50 ? 'text-success' : product.inStockRate > 0 ? 'text-warning' : 'text-danger'
                            }`}>
                              {product.inStockRate}%
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center justify-between text-xs text-muted">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            <span>{product.lastSeen}</span>
                          </div>
                          <div className="flex gap-1">
                            {product.retailers.slice(0, 3).map((r) => (
                              <span key={r} className="px-1.5 py-0.5 bg-surface rounded text-[10px]">{r}</span>
                            ))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )
              })}
            </motion.div>
          ) : (
            <EmptyState
              icon={<Package />}
              title="No products found"
              description="Try adjusting your search terms or retailer filters."
              action={
                <Button variant="outline" onClick={() => { setProductQuery(''); setHasSearched(false) }}>
                  Clear Search
                </Button>
              }
            />
          )}
        </div>

        {/* MSRP Reference */}
        <Card variant="elevated">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Tag className="h-4 w-4 text-accent" /> MSRP Reference Guide
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted uppercase">
                    <th className="pb-3 font-medium">Product Type</th>
                    <th className="pb-3 font-medium text-right">MSRP</th>
                    <th className="pb-3 font-medium text-right">Packs</th>
                    <th className="pb-3 font-medium text-right">$/Pack</th>
                    <th className="pb-3 font-medium hidden sm:table-cell">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {MSRP_REFERENCE.map((p) => (
                    <tr key={p.type} className="border-b border-border/50 hover:bg-surface-hover/50 transition">
                      <td className="py-2.5 font-medium">{p.type}</td>
                      <td className="py-2.5 text-right font-mono-numbers">${p.msrp.toFixed(2)}</td>
                      <td className="py-2.5 text-right font-mono-numbers text-muted">{p.packs}</td>
                      <td className="py-2.5 text-right font-mono-numbers text-accent">${p.costPerPack.toFixed(2)}</td>
                      <td className="py-2.5 text-xs text-muted hidden sm:table-cell">{p.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Retailer Restock Tips */}
        <Card variant="elevated">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Store className="h-4 w-4 text-accent" /> Retailer Restock Intel
            </CardTitle>
          </CardHeader>
          <CardContent>
            <motion.div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
              variants={staggerContainer}
              initial="initial"
              animate="animate"
            >
              {RETAILER_TIPS.map((tip) => (
                <motion.div key={tip.retailer} variants={staggerItem}>
                  <div className="p-4 rounded-xl border border-border hover:border-border-light transition space-y-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-3 h-3 rounded-full shrink-0"
                        style={{ backgroundColor: tip.color }}
                      />
                      <h4 className="font-semibold text-sm">{tip.retailer}</h4>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-accent">
                      <RefreshCw className="h-3 w-3" />
                      <span>Typical restock: {tip.restockDays}</span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed">{tip.tipText}</p>
                    {tip.dpci && (
                      <p className="text-[10px] text-muted font-mono">DPCI: {tip.dpci}</p>
                    )}
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  )
}
