import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  Calendar, Clock, ExternalLink, AlertTriangle, CheckCircle,
  MessageSquare, Tag, Package, TrendingUp, Star, Sparkles,
  MapPin, ShoppingCart, ArrowUpRight, Filter,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from '@/components/ui/Tabs'
import RetailerBadge from '@/components/shared/RetailerBadge'
import { staggerContainer, staggerItem, fadeInUp } from '@/lib/animations'

/* ═══════════════════════════════════════════════════════
   Comprehensive Drop Data
   ═══════════════════════════════════════════════════════ */

const TIME_FILTERS = ['All', 'This Week', 'This Month', 'Next Month', 'Q2 2026'] as const

interface Drop {
  id: string
  title: string
  date: string
  dateLabel: string
  retailers: string[]
  products: Product[]
  borderColor: string
  setId?: string
  type: 'new_set' | 'restock' | 'exclusive' | 'special'
  msrp?: Record<string, number>
  topChaseCards?: string[]
  estimatedPullRates?: { rarity: string; rate: string }[]
}

interface Product {
  name: string
  msrp: number
  packs?: number
  type: 'etb' | 'booster_box' | 'booster_bundle' | 'blister' | 'tin' | 'collection_box' | 'ultra_premium'
}

const PRODUCT_ICONS: Record<string, string> = {
  etb: 'ETB',
  booster_box: 'BB',
  booster_bundle: 'Bundle',
  blister: 'Blister',
  tin: 'Tin',
  collection_box: 'Box',
  ultra_premium: 'UPC',
}

const CONFIRMED_DROPS: Drop[] = [
  {
    id: '1',
    title: 'Prismatic Evolutions Wave 3',
    date: '2026-03-14',
    dateLabel: 'Mar 14, 2026',
    retailers: ['Target', 'Walmart', 'Pokemon Center', 'Best Buy', 'GameStop'],
    type: 'restock',
    products: [
      { name: 'Elite Trainer Box', msrp: 59.99, packs: 9, type: 'etb' },
      { name: 'Booster Bundle', msrp: 29.99, packs: 6, type: 'booster_bundle' },
      { name: 'Mini Tin (Random)', msrp: 7.99, packs: 2, type: 'tin' },
      { name: '3-Pack Blister', msrp: 14.99, packs: 3, type: 'blister' },
    ],
    borderColor: 'border-l-accent',
    topChaseCards: ['Umbreon ex SAR', 'Pikachu ex SAR', 'Eevee Illustration Rare', 'Sylveon ex SAR'],
    estimatedPullRates: [
      { rarity: 'Special Art Rare', rate: '1 in 60 packs' },
      { rarity: 'Illustration Rare', rate: '1 in 18 packs' },
      { rarity: 'Holo Rare', rate: '1 in 3 packs' },
    ],
  },
  {
    id: '2',
    title: 'Journey Together',
    date: '2026-03-28',
    dateLabel: 'Mar 28, 2026',
    retailers: ['All Retailers'],
    type: 'new_set',
    products: [
      { name: 'Booster Box', msrp: 143.64, packs: 36, type: 'booster_box' },
      { name: 'Elite Trainer Box', msrp: 49.99, packs: 9, type: 'etb' },
      { name: 'Booster Bundle', msrp: 29.99, packs: 6, type: 'booster_bundle' },
      { name: 'Build & Battle Box', msrp: 14.99, packs: 4, type: 'collection_box' },
      { name: '3-Pack Blister', msrp: 14.99, packs: 3, type: 'blister' },
    ],
    borderColor: 'border-l-success',
    topChaseCards: ['Ash & Pikachu SAR', 'Red & Charizard SAR', 'N & Reshiram SAR', 'Cynthia & Garchomp SAR'],
    estimatedPullRates: [
      { rarity: 'Special Art Rare', rate: '1 in 55 packs' },
      { rarity: 'Illustration Rare', rate: '1 in 20 packs' },
      { rarity: 'Ultra Rare', rate: '1 in 9 packs' },
      { rarity: 'Holo Rare', rate: '1 in 3 packs' },
    ],
  },
  {
    id: '3',
    title: 'Pokemon Center Exclusive: Eeveelution Collection',
    date: '2026-04-05',
    dateLabel: 'Apr 5, 2026',
    retailers: ['Pokemon Center'],
    type: 'exclusive',
    products: [
      { name: 'Premium Collection Box', msrp: 79.99, packs: 10, type: 'collection_box' },
    ],
    borderColor: 'border-l-[#ffcb05]',
    topChaseCards: ['Exclusive Eeveelution Promo Cards (8 total)'],
  },
  {
    id: '4',
    title: 'Surging Sparks Reprint Wave',
    date: '2026-03-07',
    dateLabel: 'Mar 7, 2026',
    retailers: ['Target', 'Walmart'],
    type: 'restock',
    products: [
      { name: 'Elite Trainer Box', msrp: 49.99, packs: 9, type: 'etb' },
      { name: 'Booster Box', msrp: 143.64, packs: 36, type: 'booster_box' },
    ],
    borderColor: 'border-l-info',
    topChaseCards: ['Charizard ex SAR', 'Pikachu ex IR', 'Arceus VSTAR'],
  },
  {
    id: '5',
    title: 'SV09: Astral Crown',
    date: '2026-05-23',
    dateLabel: 'May 23, 2026',
    retailers: ['All Retailers'],
    type: 'new_set',
    products: [
      { name: 'Booster Box', msrp: 143.64, packs: 36, type: 'booster_box' },
      { name: 'Elite Trainer Box', msrp: 49.99, packs: 9, type: 'etb' },
      { name: 'Booster Bundle', msrp: 29.99, packs: 6, type: 'booster_bundle' },
      { name: 'Ultra Premium Collection', msrp: 119.99, packs: 16, type: 'ultra_premium' },
    ],
    borderColor: 'border-l-warning',
    topChaseCards: ['TBD — set list not yet revealed'],
    estimatedPullRates: [
      { rarity: 'Special Art Rare', rate: 'TBD' },
      { rarity: 'Illustration Rare', rate: 'TBD' },
    ],
  },
  {
    id: '6',
    title: 'Prismatic Evolutions Blisters & Tins',
    date: '2026-03-01',
    dateLabel: 'Mar 1, 2026',
    retailers: ['Target', 'Walmart', 'Best Buy'],
    type: 'restock',
    products: [
      { name: '3-Pack Blister', msrp: 14.99, packs: 3, type: 'blister' },
      { name: 'Collector Tin', msrp: 29.99, packs: 5, type: 'tin' },
    ],
    borderColor: 'border-l-accent',
  },
  {
    id: '7',
    title: 'Destined Rivals',
    date: '2026-06-13',
    dateLabel: 'Jun 13, 2026',
    retailers: ['All Retailers'],
    type: 'new_set',
    products: [
      { name: 'Booster Box', msrp: 143.64, packs: 36, type: 'booster_box' },
      { name: 'Elite Trainer Box', msrp: 49.99, packs: 9, type: 'etb' },
      { name: 'Booster Bundle', msrp: 29.99, packs: 6, type: 'booster_bundle' },
    ],
    borderColor: 'border-l-purple-400',
    topChaseCards: ['TBD — expected to feature rival trainers'],
  },
  {
    id: '8',
    title: 'Journey Together Build & Battle Stadium',
    date: '2026-03-21',
    dateLabel: 'Mar 21, 2026',
    retailers: ['Game Stores', 'Pokemon Center'],
    type: 'special',
    products: [
      { name: 'Build & Battle Stadium', msrp: 44.99, packs: 12, type: 'collection_box' },
    ],
    borderColor: 'border-l-success',
  },
]

const RUMORS = [
  {
    id: '1',
    title: 'SV10 to feature Mega Evolutions',
    source: 'PokeBeach',
    reliability: 'high' as const,
    description: 'Reliable sources suggest SV10 may reintroduce Mega Evolution mechanics with a new card type. Expected announcement in Q3 2026.',
    date: 'Q3 2026',
    impact: 'Major hype — Mega Charizard X/Y would drive massive demand',
  },
  {
    id: '2',
    title: 'Gold Star reprints in special collection',
    source: 'Reddit r/PokemonTCG',
    reliability: 'medium' as const,
    description: 'Multiple leakers hint at a premium collection featuring reprints of classic Gold Star cards from the EX era.',
    date: 'Summer 2026',
    impact: 'Collectors would pay premium — Gold Star Rayquaza is iconic',
  },
  {
    id: '3',
    title: 'Target exclusive Pikachu promo wave',
    source: 'Twitter @PokeLeaks',
    reliability: 'medium' as const,
    description: 'A Target-exclusive Pikachu promo card may be included with ETB purchases during a spring promotional event.',
    date: 'Spring 2026',
    impact: 'Moderate — exclusive promos always drive foot traffic',
  },
  {
    id: '4',
    title: '25th Anniversary Part 2 celebration set',
    source: 'PokeBeach',
    reliability: 'low' as const,
    description: 'Speculation about a second 25th anniversary-style celebration set with reprints of iconic cards from every generation.',
    date: 'Late 2026',
    impact: 'Would be massive if true — original Celebrations was a phenomenon',
  },
  {
    id: '5',
    title: 'Pokemon Center to launch grading service',
    source: 'Industry Insider',
    reliability: 'low' as const,
    description: 'Rumors of TPC partnering with a grading company for an official Pokemon Card Grading service, potentially disrupting PSA/BGS/CGC market.',
    date: 'Unknown',
    impact: 'Could significantly shift the grading market dynamics',
  },
]

const LIVE_INTEL = [
  {
    id: '1',
    source: 'Reddit',
    content: 'Prismatic Evolutions ETBs spotted at Target in Dallas, TX. Full shelves reported — DPCI 087-35-0214.',
    timestamp: '12m ago',
    verified: true,
    location: 'Dallas, TX',
    product: 'Prismatic Evolutions ETB',
  },
  {
    id: '2',
    source: 'PokeBeach',
    content: 'Journey Together official set list leaked — 198 cards including 15 Illustration Rares and 6 Special Art Rares.',
    timestamp: '1h ago',
    verified: true,
  },
  {
    id: '3',
    source: 'Twitter',
    content: 'Pokemon Center just added Prismatic Evolutions booster bundles back in stock. Limited quantities!',
    timestamp: '2h ago',
    verified: false,
    product: 'Prismatic Evolutions Booster Bundle',
  },
  {
    id: '4',
    source: 'Discord',
    content: 'Multiple Costco warehouses in SoCal region restocked Pokemon tins and booster bundles at clearance prices.',
    timestamp: '3h ago',
    verified: true,
    location: 'Southern California',
  },
  {
    id: '5',
    source: 'Reddit',
    content: 'Walmart online restocked Surging Sparks booster boxes at MSRP $143.64. Ships free with Walmart+.',
    timestamp: '5h ago',
    verified: true,
    product: 'Surging Sparks BB',
  },
  {
    id: '6',
    source: 'Instagram',
    content: 'Local card shop showing off Journey Together pre-release kits. Product looks clean — new trainer cards confirmed.',
    timestamp: '6h ago',
    verified: false,
  },
  {
    id: '7',
    source: 'Twitter',
    content: 'Best Buy added Prismatic Evolutions 3-pack blisters online. $14.99 MSRP — limit 2 per customer.',
    timestamp: '8h ago',
    verified: true,
    product: 'Prismatic Evolutions Blister',
  },
]

/* ── Release Calendar Data ── */
interface CalendarEvent {
  date: string
  title: string
  type: 'new_set' | 'restock' | 'exclusive' | 'special' | 'prerelease'
  color: string
}

const CALENDAR_EVENTS: CalendarEvent[] = [
  { date: '2026-03-01', title: 'PE Blisters & Tins', type: 'restock', color: '#60a5fa' },
  { date: '2026-03-07', title: 'Surging Sparks Reprint', type: 'restock', color: '#3b82f6' },
  { date: '2026-03-14', title: 'Prismatic Evolutions Wave 3', type: 'restock', color: '#60a5fa' },
  { date: '2026-03-21', title: 'Journey Together Pre-release', type: 'prerelease', color: '#22c55e' },
  { date: '2026-03-28', title: 'Journey Together Release', type: 'new_set', color: '#22c55e' },
  { date: '2026-04-05', title: 'Eeveelution Collection (PC)', type: 'exclusive', color: '#ffcb05' },
  { date: '2026-05-23', title: 'SV09: Astral Crown', type: 'new_set', color: '#f97316' },
  { date: '2026-06-13', title: 'Destined Rivals', type: 'new_set', color: '#a855f7' },
]

/* ═══════════════════════════════════════════════════════ */

function getDaysUntil(dateStr: string): number {
  const target = new Date(dateStr)
  const now = new Date()
  return Math.max(0, Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))
}

function getSourceColor(source: string) {
  switch (source) {
    case 'Reddit': return 'bg-[#ff4500]/20 text-[#ff4500]'
    case 'PokeBeach': return 'bg-blue-500/20 text-blue-400'
    case 'Twitter': return 'bg-sky-500/20 text-sky-400'
    case 'Instagram': return 'bg-pink-500/20 text-pink-400'
    case 'Discord': return 'bg-indigo-500/20 text-indigo-400'
    default: return 'bg-surface-elevated text-muted'
  }
}

function getReliabilityBadge(r: string) {
  switch (r) {
    case 'high': return { variant: 'success' as const, label: 'Reliable' }
    case 'medium': return { variant: 'warning' as const, label: 'Unconfirmed' }
    default: return { variant: 'danger' as const, label: 'Speculation' }
  }
}

function getTypeBadge(type: Drop['type']) {
  switch (type) {
    case 'new_set': return { variant: 'accent' as const, label: 'New Set', icon: Sparkles }
    case 'restock': return { variant: 'success' as const, label: 'Restock', icon: Package }
    case 'exclusive': return { variant: 'warning' as const, label: 'Exclusive', icon: Star }
    case 'special': return { variant: 'info' as const, label: 'Special', icon: Tag }
  }
}

export default function Drops() {
  const [timeFilter, setTimeFilter] = useState<string>('All')

  const filteredDrops = useMemo(() => {
    const now = new Date()
    return CONFIRMED_DROPS.filter((drop) => {
      const dropDate = new Date(drop.date)
      switch (timeFilter) {
        case 'This Week': {
          const weekEnd = new Date(now)
          weekEnd.setDate(weekEnd.getDate() + 7)
          return dropDate >= now && dropDate <= weekEnd
        }
        case 'This Month': {
          return dropDate.getMonth() === now.getMonth() && dropDate.getFullYear() === now.getFullYear()
        }
        case 'Next Month': {
          const next = new Date(now.getFullYear(), now.getMonth() + 1)
          return dropDate.getMonth() === next.getMonth() && dropDate.getFullYear() === next.getFullYear()
        }
        case 'Q2 2026': {
          return dropDate >= new Date('2026-04-01') && dropDate < new Date('2026-07-01')
        }
        default: return true
      }
    }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  }, [timeFilter])

  return (
    <PageTransition>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Drops Intel</h1>
          <p className="mt-1 text-muted-foreground/60 text-sm">
            Upcoming releases, restocks, live intel &amp; community sightings
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold font-mono-numbers text-accent">{CONFIRMED_DROPS.length}</p>
              <p className="text-xs text-muted">Upcoming Drops</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold font-mono-numbers text-success">
                {CONFIRMED_DROPS.filter(d => d.type === 'new_set').length}
              </p>
              <p className="text-xs text-muted">New Sets</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold font-mono-numbers text-warning">
                {LIVE_INTEL.filter(i => i.verified).length}
              </p>
              <p className="text-xs text-muted">Verified Sightings</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold font-mono-numbers text-foreground">
                {getDaysUntil(CONFIRMED_DROPS.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())[0]?.date || '')}d
              </p>
              <p className="text-xs text-muted">Next Drop</p>
            </CardContent>
          </Card>
        </div>

        <TabGroup defaultValue="confirmed">
          <TabList>
            <Tab value="confirmed">Confirmed Drops</Tab>
            <Tab value="calendar">Calendar</Tab>
            <Tab value="rumors">Rumors &amp; Leaks</Tab>
            <Tab value="live">Live Intel</Tab>
          </TabList>

          <TabPanels className="mt-6">
            {/* ── Confirmed Drops ── */}
            <TabPanel value="confirmed">
              <div className="flex gap-2 mb-6 flex-wrap">
                {TIME_FILTERS.map((filter) => (
                  <Button
                    key={filter}
                    variant={timeFilter === filter ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setTimeFilter(filter)}
                  >
                    {filter}
                  </Button>
                ))}
              </div>

              {filteredDrops.length === 0 ? (
                <div className="text-center py-12 text-muted text-sm">
                  No drops scheduled for this time period
                </div>
              ) : (
                <motion.div
                  className="space-y-4"
                  variants={staggerContainer}
                  initial="initial"
                  animate="animate"
                >
                  {filteredDrops.map((drop) => {
                    const daysUntil = getDaysUntil(drop.date)
                    const typeBadge = getTypeBadge(drop.type)
                    const TypeIcon = typeBadge.icon
                    return (
                      <motion.div key={drop.id} variants={staggerItem}>
                        <Card hover className={`border-l-4 ${drop.borderColor}`}>
                          <CardContent className="p-5 space-y-4">
                            {/* Title Row */}
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <h3 className="text-lg font-semibold text-foreground">{drop.title}</h3>
                                <div className="flex items-center gap-3 mt-1.5 text-sm text-muted">
                                  <div className="flex items-center gap-1">
                                    <Calendar className="h-3.5 w-3.5" />
                                    <span>{drop.dateLabel}</span>
                                  </div>
                                  <span className="text-xs">
                                    {daysUntil === 0 ? 'Today!' : `in ${daysUntil} days`}
                                  </span>
                                </div>
                              </div>
                              <Badge variant={typeBadge.variant}>
                                <TypeIcon className="h-3 w-3 mr-1" />
                                {typeBadge.label}
                              </Badge>
                            </div>

                            {/* Retailers */}
                            <div className="flex gap-1.5 flex-wrap">
                              {drop.retailers.map((r) => (
                                <RetailerBadge key={r} retailer={r} />
                              ))}
                            </div>

                            {/* Products Table */}
                            {drop.products.length > 0 && (
                              <div className="bg-surface rounded-lg overflow-hidden">
                                <div className="grid grid-cols-[1fr_80px_60px] sm:grid-cols-[1fr_80px_60px_60px] gap-2 p-2 text-xs text-muted font-medium border-b border-border">
                                  <span>Product</span>
                                  <span className="text-right">MSRP</span>
                                  <span className="text-right">Packs</span>
                                  <span className="text-right hidden sm:block">$/Pack</span>
                                </div>
                                {drop.products.map((p) => (
                                  <div key={p.name} className="grid grid-cols-[1fr_80px_60px] sm:grid-cols-[1fr_80px_60px_60px] gap-2 p-2 text-sm items-center border-b border-border/50 last:border-0">
                                    <div className="flex items-center gap-2">
                                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-mono font-bold shrink-0">
                                        {PRODUCT_ICONS[p.type] || p.type}
                                      </span>
                                      <span className="truncate">{p.name}</span>
                                    </div>
                                    <span className="text-right font-mono-numbers">${p.msrp.toFixed(2)}</span>
                                    <span className="text-right font-mono-numbers text-muted">{p.packs || '—'}</span>
                                    <span className="text-right font-mono-numbers text-muted hidden sm:block">
                                      {p.packs ? `$${(p.msrp / p.packs).toFixed(2)}` : '—'}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Chase Cards */}
                            {drop.topChaseCards && drop.topChaseCards.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-muted mb-1.5 flex items-center gap-1">
                                  <Star className="h-3 w-3 text-yellow-400" /> Top Chase Cards
                                </p>
                                <div className="flex gap-1.5 flex-wrap">
                                  {drop.topChaseCards.map((card) => (
                                    <Badge key={card} variant="default" className="text-[10px]">{card}</Badge>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Pull Rates */}
                            {drop.estimatedPullRates && drop.estimatedPullRates.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-muted mb-1.5 flex items-center gap-1">
                                  <TrendingUp className="h-3 w-3 text-accent" /> Estimated Pull Rates
                                </p>
                                <div className="flex gap-3 flex-wrap text-xs">
                                  {drop.estimatedPullRates.map((pr) => (
                                    <span key={pr.rarity} className="text-muted">
                                      <span className="text-foreground font-medium">{pr.rarity}:</span> {pr.rate}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      </motion.div>
                    )
                  })}
                </motion.div>
              )}
            </TabPanel>

            {/* ── Release Calendar ── */}
            <TabPanel value="calendar">
              <Card variant="elevated">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-accent" /> 2026 Release Calendar
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {CALENDAR_EVENTS.map((event, i) => {
                      const daysUntil = getDaysUntil(event.date)
                      const isPast = daysUntil === 0 && new Date(event.date) < new Date()
                      return (
                        <div
                          key={i}
                          className={`flex items-center gap-4 p-3 rounded-lg border transition-all ${
                            isPast ? 'opacity-50 border-border/30' : 'border-border hover:bg-surface-hover'
                          }`}
                        >
                          <div
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ backgroundColor: event.color }}
                          />
                          <div className="w-28 shrink-0">
                            <p className="text-sm font-mono-numbers font-medium">
                              {new Date(event.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </p>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{event.title}</p>
                          </div>
                          <Badge variant={
                            event.type === 'new_set' ? 'accent' :
                            event.type === 'restock' ? 'success' :
                            event.type === 'exclusive' ? 'warning' :
                            event.type === 'prerelease' ? 'info' : 'default'
                          } className="text-[10px] shrink-0">
                            {event.type.replace('_', ' ')}
                          </Badge>
                          <span className="text-xs text-muted font-mono-numbers shrink-0 w-16 text-right">
                            {daysUntil === 0 ? 'Today' : `${daysUntil}d`}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            </TabPanel>

            {/* ── Rumors ── */}
            <TabPanel value="rumors">
              <motion.div
                className="space-y-4"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
              >
                {RUMORS.map((rumor) => {
                  const badge = getReliabilityBadge(rumor.reliability)
                  return (
                    <motion.div key={rumor.id} variants={staggerItem}>
                      <Card className="border-warning/20">
                        <CardContent className="p-5 space-y-3">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4 text-warning shrink-0" />
                              <h3 className="text-lg font-semibold text-foreground">{rumor.title}</h3>
                            </div>
                            <Badge variant={badge.variant}>{badge.label}</Badge>
                          </div>
                          <p className="text-sm text-muted">{rumor.description}</p>
                          <div className="flex flex-wrap gap-4 text-xs text-muted">
                            <span>Source: <span className="text-foreground">{rumor.source}</span></span>
                            <span>Expected: <span className="text-foreground">{rumor.date}</span></span>
                          </div>
                          <div className="bg-surface rounded-lg p-3 text-xs">
                            <span className="text-muted">Market Impact: </span>
                            <span className="text-foreground">{rumor.impact}</span>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )
                })}
              </motion.div>
            </TabPanel>

            {/* ── Live Intel ── */}
            <TabPanel value="live">
              <motion.div
                className="space-y-3"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
              >
                {LIVE_INTEL.map((item) => (
                  <motion.div key={item.id} variants={staggerItem}>
                    <Card>
                      <CardContent className="p-4 flex items-start gap-4">
                        <span className={`shrink-0 inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-md ${getSourceColor(item.source)}`}>
                          {item.source === 'Reddit' && <MessageSquare className="h-3 w-3 mr-1" />}
                          {item.source}
                        </span>
                        <div className="flex-1 min-w-0 space-y-1.5">
                          <p className="text-sm text-foreground">{item.content}</p>
                          <div className="flex items-center gap-3 flex-wrap">
                            <span className="text-xs text-muted">{item.timestamp}</span>
                            {item.verified && (
                              <span className="flex items-center gap-0.5 text-xs text-success">
                                <CheckCircle className="h-3 w-3" /> Verified
                              </span>
                            )}
                            {item.location && (
                              <span className="flex items-center gap-0.5 text-xs text-muted">
                                <MapPin className="h-3 w-3" /> {item.location}
                              </span>
                            )}
                            {item.product && (
                              <Badge variant="default" className="text-[10px]">{item.product}</Badge>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </motion.div>
            </TabPanel>
          </TabPanels>
        </TabGroup>
      </div>
    </PageTransition>
  )
}
