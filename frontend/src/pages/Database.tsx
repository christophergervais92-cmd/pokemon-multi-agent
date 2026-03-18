import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Database as DatabaseIcon, AlertCircle, ChevronLeft, ChevronRight, Search, X } from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Skeleton } from '@/components/ui/Skeleton'
import { staggerContainer, staggerItem, fadeInUp } from '@/lib/animations'
import { useSets, usePullRates, useChaseCards, useSetCards } from '@/hooks/useApi'
import CardGradeModal from '@/components/shared/CardGradeModal'
import type { SetCardItem } from '@/lib/api'

const SERIES_OPTIONS = [
  { value: '', label: 'All Series' },
  { value: 'Scarlet & Violet', label: 'Scarlet & Violet' },
  { value: 'Sword & Shield', label: 'Sword & Shield' },
  { value: 'Sun & Moon', label: 'Sun & Moon' },
  { value: 'XY', label: 'XY' },
  { value: 'Black & White', label: 'Black & White' },
]

const CHASE_FILTER_TABS = ['All', 'Illustration Rare', 'Special Art', 'Holo', 'Ultra Rare']

function getRarityVariant(rarity: string) {
  const r = rarity.toLowerCase()
  if (r.includes('special art') || r.includes('hyper')) return 'danger' as const
  if (r.includes('illustration') || r.includes('secret')) return 'warning' as const
  if (r.includes('ultra') || r.includes('full art')) return 'accent' as const
  if (r.includes('holo') || r.includes('rare')) return 'success' as const
  return 'default' as const
}

function getPullRateColor(rate: number): 'success' | 'accent' | 'warning' | 'danger' {
  if (rate >= 20) return 'accent'
  if (rate >= 5) return 'success'
  if (rate >= 1) return 'warning'
  return 'danger'
}

export default function Database() {
  const [series, setSeries] = useState('')
  const [selectedSet, setSelectedSet] = useState('')
  const [chaseFilter, setChaseFilter] = useState('All')
  const [cardsPage, setCardsPage] = useState(1)
  const [activeTab, setActiveTab] = useState<'all' | 'chase'>('all')
  const [selectedCard, setSelectedCard] = useState<SetCardItem | null>(null)
  const [setSearch, setSetSearch] = useState('')

  // Fetch sets from API
  const { data: setsData, isLoading: setsLoading, isError: setsError } = useSets(series || undefined)
  const sets = setsData?.data ?? []

  // Build set options from real API data
  const setOptions = useMemo(() => {
    const opts = [{ value: '', label: 'Select a set...' }]
    sets.forEach((s) => {
      opts.push({ value: s.id, label: s.name })
    })
    return opts
  }, [sets])

  // Fetch pull rates for selected set
  const { data: pullRatesData, isLoading: pullRatesLoading } = usePullRates(selectedSet)
  const pullRates = pullRatesData?.data ?? []

  // Fetch all cards (paginated)
  const { data: allCardsData, isLoading: allCardsLoading } = useSetCards(selectedSet, cardsPage, 60)
  const allCards = allCardsData?.data ?? []
  const totalPages = allCardsData?.pages ?? 1
  const totalCards = allCardsData?.total ?? 0

  // Fetch chase cards for selected set
  const { data: chaseData, isLoading: chaseLoading } = useChaseCards(selectedSet, undefined, 100)
  const chaseCards = chaseData?.data ?? []

  // Filter chase cards by rarity tab
  const filteredChaseCards = useMemo(() => {
    if (chaseFilter === 'All') return chaseCards
    return chaseCards.filter((c) =>
      c.rarity.toLowerCase().includes(chaseFilter.toLowerCase())
    )
  }, [chaseCards, chaseFilter])

  const selectedSetInfo = sets.find((s) => s.id === selectedSet)

  const filteredSets = useMemo(() => {
    if (!setSearch.trim()) return sets
    const q = setSearch.toLowerCase()
    return sets.filter((s) =>
      s.name.toLowerCase().includes(q) || (s.series || '').toLowerCase().includes(q)
    )
  }, [sets, setSearch])

  return (
    <PageTransition>
      <div className="space-y-8">
        {/* Header */}
        <div className="page-header">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Set Database</h1>
          <p className="mt-1 text-muted-foreground/60 text-sm">Explore every Pokemon TCG set</p>
        </div>

        {/* Filters row */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="w-full sm:w-44 shrink-0">
            <Select
              label="Series"
              options={SERIES_OPTIONS}
              value={series}
              onChange={(e) => { setSeries(e.target.value); setSelectedSet(''); setSetSearch('') }}
            />
          </div>
          {/* Search box */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted pointer-events-none" />
            <input
              type="text"
              value={setSearch}
              onChange={(e) => { setSetSearch(e.target.value); setSelectedSet('') }}
              placeholder="Search sets… (e.g. Prismatic, 151, Surging)"
              className="w-full h-10 pl-9 pr-9 rounded-lg text-sm bg-surface border border-border text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
            />
            {setSearch && (
              <button
                onClick={() => setSetSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-foreground transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Set Grid (when no set selected) */}
        {!selectedSet && (
          <>
            {setsLoading ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                {Array.from({ length: 12 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton className="h-24 w-full rounded-xl" />
                    <Skeleton className="h-3 w-3/4 mx-auto" />
                    <Skeleton className="h-2.5 w-1/2 mx-auto" />
                  </div>
                ))}
              </div>
            ) : setsError ? (
              <div className="flex items-center gap-2 text-sm text-rose-400">
                <AlertCircle className="h-4 w-4" />
                Failed to load sets — check that the backend is online
              </div>
            ) : filteredSets.length > 0 ? (
              <>
                <p className="text-xs text-muted-foreground/50">
                  {filteredSets.length} set{filteredSets.length !== 1 ? 's' : ''}
                  {setSearch ? ` matching "${setSearch}"` : (series ? ` in ${series}` : ' across all series')}
                  {' '}— click any set to explore its cards
                </p>
                <motion.div
                  variants={staggerContainer}
                  initial="initial"
                  animate="animate"
                  className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
                >
                  {filteredSets.map((set) => (
                    <motion.div key={set.id} variants={staggerItem}>
                      <Card
                        hover
                        className="cursor-pointer overflow-hidden group transition-all duration-300 hover:border-accent/30"
                        onClick={() => { setSelectedSet(set.id); setCardsPage(1); setActiveTab('all') }}
                      >
                        <CardContent className="p-3 flex flex-col items-center">
                          {/* Set logo — tall box so logos have room */}
                          <div className="w-full h-20 flex items-center justify-center mb-2 rounded-lg overflow-hidden bg-gradient-to-br from-white/[0.03] to-white/[0.01] group-hover:from-accent/10 group-hover:to-accent/5 transition-colors duration-300">
                            {set.logo_url ? (
                              <img
                                src={set.logo_url}
                                alt={set.name}
                                className="max-h-16 max-w-full object-contain drop-shadow-[0_2px_8px_rgba(0,0,0,0.4)] transition-transform duration-300 group-hover:scale-105"
                                loading="lazy"
                                onError={(e) => {
                                  // fallback: hide broken image, show icon
                                  ;(e.currentTarget as HTMLImageElement).style.display = 'none'
                                }}
                              />
                            ) : (
                              <DatabaseIcon className="h-8 w-8 text-accent/40" />
                            )}
                          </div>
                          <p className="text-xs font-semibold text-center leading-tight line-clamp-2">{set.name}</p>
                          <p className="text-[10px] text-muted text-center mt-0.5 truncate w-full">
                            {set.series || '—'}{set.total_cards ? ` · ${set.total_cards}` : ''}
                          </p>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </motion.div>
              </>
            ) : (
              <p className="text-sm text-muted text-center py-8">No sets found{setSearch ? ` for "${setSearch}"` : ''}</p>
            )}
          </>
        )}

        {/* Back to all sets */}
        {selectedSet && (
          <button
            onClick={() => { setSelectedSet(''); setCardsPage(1) }}
            className="flex items-center gap-1.5 text-sm text-muted hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            All Sets
          </button>
        )}

        {/* Set Info Hero Card */}
        {selectedSet && selectedSetInfo && (
          <motion.div
            variants={fadeInUp}
            initial="initial"
            animate="animate"
            transition={{ duration: 0.3 }}
          >
            <Card variant="elevated">
              <CardContent className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-[96px_1fr] gap-6 items-center">
                  {selectedSetInfo.logo_url ? (
                    <img src={selectedSetInfo.logo_url} alt={selectedSetInfo.name} className="h-24 object-contain" />
                  ) : (
                    <div className="w-24 h-24 rounded-xl bg-gradient-to-br from-accent/30 to-accent/10 flex items-center justify-center">
                      <DatabaseIcon className="h-10 w-10 text-accent" />
                    </div>
                  )}
                  <div className="space-y-2">
                    <h2 className="text-2xl font-bold text-foreground">{selectedSetInfo.name}</h2>
                    <div className="flex flex-wrap gap-4 text-sm text-muted">
                      <span>Series: {selectedSetInfo.series}</span>
                      {selectedSetInfo.release_date && <span>Released: {selectedSetInfo.release_date}</span>}
                      {selectedSetInfo.total_cards && <span>Total Cards: {selectedSetInfo.total_cards}</span>}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Pull Rates */}
        {selectedSet && (
          <Card>
            <CardHeader>
              <CardTitle>Pull Rates</CardTitle>
            </CardHeader>
            <CardContent>
              {pullRatesLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-8 w-full rounded" />
                  ))}
                </div>
              ) : pullRates.length > 0 ? (
                <div className="space-y-4">
                  {pullRates.map((rate) => (
                    <div key={rate.rarity} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-foreground font-medium">{rate.rarity}</span>
                        <span className="text-muted font-mono-numbers">{rate.rate}%</span>
                      </div>
                      <Progress value={rate.rate} color={getPullRateColor(rate.rate)} />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted text-center py-4">No pull rate data available for this set</p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Cards Section — tabbed All / Chase */}
        {selectedSet && (
          <div className="space-y-4">
            {/* Tab bar */}
            <div className="flex items-center gap-1 border-b border-border pb-0">
              {(['all', 'chase'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => { setActiveTab(tab); if (tab === 'all') setCardsPage(1) }}
                  className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                    activeTab === tab
                      ? 'border-accent text-foreground'
                      : 'border-transparent text-muted hover:text-foreground'
                  }`}
                >
                  {tab === 'all' ? `All Cards${totalCards ? ` (${totalCards})` : ''}` : `Chase Cards${chaseCards.length ? ` (${chaseCards.length})` : ''}`}
                </button>
              ))}
            </div>

            {/* ── All Cards tab ── */}
            {activeTab === 'all' && (
              <>
                {allCardsLoading ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                    {Array.from({ length: 10 }).map((_, i) => (
                      <div key={i} className="space-y-2">
                        <Skeleton className="aspect-[3/4] w-full rounded-xl" />
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                      </div>
                    ))}
                  </div>
                ) : allCards.length > 0 ? (
                  <>
                    <motion.div
                      key={`page-${cardsPage}`}
                      className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4"
                      variants={staggerContainer}
                      initial="initial"
                      animate="animate"
                    >
                      {allCards.map((card) => (
                        <motion.div key={card.id} variants={staggerItem}>
                          <Card
                            hover
                            className="overflow-hidden cursor-pointer group"
                            onClick={() => setSelectedCard(card)}
                          >
                            <div className="aspect-[3/4] bg-gradient-to-br from-surface-elevated to-surface relative overflow-hidden">
                              {card.image_url || card.small_image_url ? (
                                <img
                                  src={card.small_image_url ?? card.image_url}
                                  alt={card.name}
                                  className="absolute inset-0 w-full h-full object-contain transition-transform duration-300 group-hover:scale-105"
                                  loading="lazy"
                                />
                              ) : null}
                              {/* Grade chart hint overlay */}
                              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-200 flex items-center justify-center">
                                <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-[10px] text-white font-medium bg-black/60 px-2 py-1 rounded-full">
                                  View Grades
                                </span>
                              </div>
                            </div>
                            <CardContent className="p-3 space-y-1">
                              <p className="text-sm font-medium text-foreground truncate">{card.name}</p>
                              {card.rarity && <Badge variant={getRarityVariant(card.rarity)}>{card.rarity}</Badge>}
                              {card.tcgplayer_market != null && (
                                <p className="text-base font-bold font-mono-numbers text-accent">
                                  ${card.tcgplayer_market.toFixed(2)}
                                </p>
                              )}
                            </CardContent>
                          </Card>
                        </motion.div>
                      ))}
                    </motion.div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-center gap-3 pt-2">
                        <button
                          onClick={() => setCardsPage((p) => Math.max(1, p - 1))}
                          disabled={cardsPage === 1}
                          className="flex items-center justify-center h-9 w-9 rounded-lg bg-surface-elevated border border-border text-muted hover:text-foreground disabled:opacity-40 transition-colors"
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </button>
                        <span className="text-sm text-muted">
                          Page <span className="text-foreground font-medium">{cardsPage}</span> of {totalPages}
                        </span>
                        <button
                          onClick={() => setCardsPage((p) => Math.min(totalPages, p + 1))}
                          disabled={cardsPage === totalPages}
                          className="flex items-center justify-center h-9 w-9 rounded-lg bg-surface-elevated border border-border text-muted hover:text-foreground disabled:opacity-40 transition-colors"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-muted text-center py-8">No cards found for this set</p>
                )}
              </>
            )}

            {/* ── Chase Cards tab ── */}
            {activeTab === 'chase' && (
              <>
                <div className="flex gap-2 flex-wrap">
                  {CHASE_FILTER_TABS.map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setChaseFilter(tab)}
                      className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                        chaseFilter === tab
                          ? 'bg-accent text-white'
                          : 'bg-surface-elevated text-muted hover:text-foreground'
                      }`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                {chaseLoading ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                    {Array.from({ length: 8 }).map((_, i) => (
                      <div key={i} className="space-y-2">
                        <Skeleton className="aspect-[3/4] w-full rounded-xl" />
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                      </div>
                    ))}
                  </div>
                ) : filteredChaseCards.length > 0 ? (
                  <motion.div
                    className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4"
                    variants={staggerContainer}
                    initial="initial"
                    animate="animate"
                  >
                    {filteredChaseCards.map((card) => (
                      <motion.div key={card.id || card.name} variants={staggerItem}>
                        <Card
                          hover
                          className="overflow-hidden cursor-pointer group"
                          onClick={() => setSelectedCard(card as unknown as SetCardItem)}
                        >
                          <div className="aspect-[3/4] bg-gradient-to-br from-accent/20 via-surface-elevated to-accent/5 relative overflow-hidden">
                            {card.image_url ? (
                              <img
                                src={card.image_url}
                                alt={card.name}
                                className="absolute inset-0 w-full h-full object-contain transition-transform duration-300 group-hover:scale-105"
                                loading="lazy"
                              />
                            ) : null}
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-200 flex items-center justify-center">
                              <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-[10px] text-white font-medium bg-black/60 px-2 py-1 rounded-full">
                                View Grades
                              </span>
                            </div>
                          </div>
                          <CardContent className="p-3 space-y-1.5">
                            <p className="text-sm font-medium text-foreground truncate">{card.name}</p>
                            <Badge variant={getRarityVariant(card.rarity)}>{card.rarity}</Badge>
                            {card.price != null && (
                              <p className="text-lg font-bold font-mono-numbers text-accent">
                                ${typeof card.price === 'number' ? card.price.toFixed(2) : card.price}
                              </p>
                            )}
                          </CardContent>
                        </Card>
                      </motion.div>
                    ))}
                  </motion.div>
                ) : (
                  <p className="text-sm text-muted text-center py-8">No chase cards found for this filter</p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Grade chart modal */}
      <CardGradeModal card={selectedCard} onClose={() => setSelectedCard(null)} />
    </PageTransition>
  )
}
