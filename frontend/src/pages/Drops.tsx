import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Calendar, AlertTriangle, CheckCircle,
  MessageSquare, Tag, Package, TrendingUp, Star, Sparkles,
  MapPin, Loader2,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from '@/components/ui/Tabs'
import RetailerBadge from '@/components/shared/RetailerBadge'
import { EmptyState } from '@/components/ui/EmptyState'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { useDrops, useDropsRumors, useDropsLiveIntel, useDropsCalendar } from '@/hooks/useApi'
import type { Drop } from '@/lib/api'

const TIME_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'this_week', label: 'This Week' },
  { value: 'this_month', label: 'This Month' },
  { value: 'next_month', label: 'Next Month' },
  { value: 'q2_2026', label: 'Q2 2026' },
] as const

const PRODUCT_ICONS: Record<string, string> = {
  etb: 'ETB',
  booster_box: 'BB',
  booster_bundle: 'Bundle',
  blister: 'Blister',
  tin: 'Tin',
  collection_box: 'Box',
  ultra_premium: 'UPC',
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
    default: return { variant: 'default' as const, label: 'Drop', icon: Tag }
  }
}

function LoadingBlock({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-muted text-sm gap-2">
      <Loader2 className="w-4 h-4 animate-spin" /> Loading {label}…
    </div>
  )
}

export default function Drops() {
  const [timeFilter, setTimeFilter] = useState<string>('all')

  const dropsQ = useDrops(timeFilter)
  const rumorsQ = useDropsRumors()
  const liveQ = useDropsLiveIntel()
  const calQ = useDropsCalendar()

  const drops = dropsQ.data?.data ?? []
  const summary = dropsQ.data?.summary
  const rumors = rumorsQ.data?.data ?? []
  const liveIntel = liveQ.data?.data ?? []
  const calendarEvents = calQ.data?.data ?? []

  return (
    <PageTransition>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="font-display text-4xl sm:text-5xl leading-none tracking-tight-er text-foreground">Drops Intel</h1>
          <p className="mt-1 text-muted-foreground/60 text-sm">
            Upcoming releases, restocks, live intel &amp; community sightings
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold font-mono-numbers text-accent">
                {summary?.total_drops ?? '—'}
              </p>
              <p className="text-xs text-muted">Upcoming Drops</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold font-mono-numbers text-success">
                {summary?.new_sets ?? '—'}
              </p>
              <p className="text-xs text-muted">New Sets</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold font-mono-numbers text-warning">
                {summary?.verified_sightings ?? '—'}
              </p>
              <p className="text-xs text-muted">Verified Sightings</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold font-mono-numbers text-foreground">
                {summary?.days_until_next != null ? `${summary.days_until_next}d` : '—'}
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
                    key={filter.value}
                    variant={timeFilter === filter.value ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setTimeFilter(filter.value)}
                  >
                    {filter.label}
                  </Button>
                ))}
              </div>

              {dropsQ.isPending ? (
                <LoadingBlock label="drops" />
              ) : dropsQ.isError ? (
                <EmptyState
                  icon={<AlertTriangle />}
                  title="Failed to load drops"
                  description={dropsQ.error instanceof Error ? dropsQ.error.message : 'Unknown error'}
                />
              ) : drops.length === 0 ? (
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
                  {drops.map((drop) => {
                    const typeBadge = getTypeBadge(drop.type)
                    const TypeIcon = typeBadge.icon
                    return (
                      <motion.div key={drop.id} variants={staggerItem}>
                        <Card hover className={`border-l-4 ${drop.border_color}`}>
                          <CardContent className="p-5 space-y-4">
                            {/* Title Row */}
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <h3 className="text-lg font-semibold text-foreground">{drop.title}</h3>
                                <div className="flex items-center gap-3 mt-1.5 text-sm text-muted">
                                  <div className="flex items-center gap-1">
                                    <Calendar className="h-3.5 w-3.5" />
                                    <span>{drop.date_label}</span>
                                  </div>
                                  <span className="text-xs">
                                    {drop.days_until === 0 ? 'Today!' : `in ${drop.days_until} days`}
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
                                    <span className="text-right font-mono-numbers text-muted">{p.packs ?? '—'}</span>
                                    <span className="text-right font-mono-numbers text-muted hidden sm:block">
                                      {p.packs ? `$${(p.msrp / p.packs).toFixed(2)}` : '—'}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Chase Cards */}
                            {drop.top_chase_cards && drop.top_chase_cards.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-muted mb-1.5 flex items-center gap-1">
                                  <Star className="h-3 w-3 text-yellow-400" /> Top Chase Cards
                                </p>
                                <div className="flex gap-1.5 flex-wrap">
                                  {drop.top_chase_cards.map((card) => (
                                    <Badge key={card} variant="default" className="text-[10px]">{card}</Badge>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Pull Rates */}
                            {drop.estimated_pull_rates && drop.estimated_pull_rates.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-muted mb-1.5 flex items-center gap-1">
                                  <TrendingUp className="h-3 w-3 text-accent" /> Estimated Pull Rates
                                </p>
                                <div className="flex gap-3 flex-wrap text-xs">
                                  {drop.estimated_pull_rates.map((pr) => (
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
                    <Calendar className="h-4 w-4 text-accent" /> Release Calendar
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {calQ.isPending ? (
                    <LoadingBlock label="calendar" />
                  ) : calendarEvents.length === 0 ? (
                    <div className="text-center py-8 text-muted text-sm">No calendar events</div>
                  ) : (
                    <div className="space-y-3">
                      {calendarEvents.map((event) => {
                        const dropDate = new Date(event.date)
                        const isPast = dropDate.getTime() < Date.now()
                        const daysUntil = Math.max(0, Math.ceil((dropDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
                        return (
                          <div
                            key={event.drop_id}
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
                                {dropDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
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
                              {isPast ? 'Past' : daysUntil === 0 ? 'Today' : `${daysUntil}d`}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabPanel>

            {/* ── Rumors ── */}
            <TabPanel value="rumors">
              {rumorsQ.isPending ? (
                <LoadingBlock label="rumors" />
              ) : rumors.length === 0 ? (
                <div className="text-center py-8 text-muted text-sm">No rumors tracked</div>
              ) : (
                <motion.div
                  className="space-y-4"
                  variants={staggerContainer}
                  initial="initial"
                  animate="animate"
                >
                  {rumors.map((rumor) => {
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
              )}
            </TabPanel>

            {/* ── Live Intel ── */}
            <TabPanel value="live">
              {liveQ.isPending ? (
                <LoadingBlock label="live intel" />
              ) : liveIntel.length === 0 ? (
                <div className="text-center py-8 text-muted text-sm">No live intel yet</div>
              ) : (
                <motion.div
                  className="space-y-3"
                  variants={staggerContainer}
                  initial="initial"
                  animate="animate"
                >
                  {liveIntel.map((item) => (
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
              )}
            </TabPanel>
          </TabPanels>
        </TabGroup>
      </div>
    </PageTransition>
  )
}
