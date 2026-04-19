/**
 * Track — unified card price table. The daily-use page.
 * Default: top trending. Search: live query. Inline sparklines.
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Search, TrendingUp, TrendingDown, Minus, ArrowUpDown,
  ChevronUp, ChevronDown, Loader2,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import Sparkline from '@/components/shared/Sparkline'
import { useTrendingCards, useCardSearch, useSets } from '@/hooks/useApi'
import { formatPrice } from '@/lib/utils'
import { getCardImageUrl, proxyImageUrl } from '@/lib/product-images'

type SortKey = 'change_7d' | 'change_30d' | 'price' | 'name'
type SortDir = 'asc' | 'desc'

// Stable-ish synthetic sparkline from change_7d
function synthLine(current: number | null, change: number | null): number[] {
  if (current == null) return []
  const pct = (change ?? 0) / 100
  const start = current / (1 + pct)
  const points: number[] = []
  for (let i = 0; i < 14; i++) {
    const t = i / 13
    const noise = (Math.sin(i * 2.3) + Math.cos(i * 1.7)) * 0.012 * current
    points.push(start + (current - start) * t + noise)
  }
  return points
}

function rarityChipClass(rarity?: string): string {
  if (!rarity) return 'chip'
  const r = rarity.toLowerCase()
  if (r.includes('special')) return 'chip chip-danger'
  if (r.includes('secret')) return 'chip chip-danger'
  if (r.includes('illustration')) return 'chip chip-info'
  if (r.includes('ultra')) return 'chip chip-warning'
  if (r.includes('hyper')) return 'chip chip-warning'
  if (r.includes('holo')) return 'chip chip-success'
  return 'chip'
}

export default function Cards() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [committedQuery, setCommittedQuery] = useState(searchParams.get('q') || '')
  const [setFilter, setSetFilter] = useState<string>('')
  const [sortKey, setSortKey] = useState<SortKey>('change_7d')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const trendingQ = useTrendingCards(50)
  const searchQ = useCardSearch(committedQuery)
  const setsQ = useSets()

  useEffect(() => {
    const q = searchParams.get('q') ?? ''
    setQuery(q)
    setCommittedQuery(q)
  }, [searchParams])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    setCommittedQuery(q)
    if (q) setSearchParams({ q })
    else setSearchParams({})
  }

  const isSearching = committedQuery.length >= 2
  const rows = useMemo(() => {
    if (isSearching) {
      // Normalize search results to same shape as trending
      return (searchQ.data?.data ?? []).map(c => ({
        id: c.id,
        name: c.name,
        set_name: c.set ?? '',
        number: (c.number as string | undefined) ?? '',
        rarity: c.rarity,
        price: c.price ?? null,
        change_7d: null as number | null,
        change_30d: null as number | null,
        tcgplayer_market: (c.price as number | null) ?? null,
        image_url: (c.image as string | undefined) ?? null,
        small_image_url: (c.image as string | undefined) ?? null,
      }))
    }
    return (trendingQ.data?.data ?? []).map(c => ({
      id: c.id,
      name: c.name,
      set_name: c.set_name ?? c.set ?? '',
      number: c.number ?? '',
      rarity: c.rarity,
      price: c.price ?? c.tcgplayer_market ?? null,
      change_7d: c.change_7d ?? null,
      change_30d: c.change_30d ?? null,
      tcgplayer_market: c.tcgplayer_market ?? null,
      image_url: c.image_url ?? null,
      small_image_url: c.small_image_url ?? null,
    }))
  }, [isSearching, searchQ.data, trendingQ.data])

  const filtered = useMemo(() => {
    let out = rows
    if (setFilter) out = out.filter(r => r.set_name?.toLowerCase().includes(setFilter.toLowerCase()))
    return out
  }, [rows, setFilter])

  const sorted = useMemo(() => {
    const copy = [...filtered]
    copy.sort((a, b) => {
      let av: number | string | null = 0
      let bv: number | string | null = 0
      if (sortKey === 'name') {
        av = a.name ?? ''
        bv = b.name ?? ''
      } else if (sortKey === 'price') {
        av = a.price ?? -Infinity
        bv = b.price ?? -Infinity
      } else if (sortKey === 'change_7d') {
        av = a.change_7d ?? -Infinity
        bv = b.change_7d ?? -Infinity
      } else {
        av = a.change_30d ?? -Infinity
        bv = b.change_30d ?? -Infinity
      }
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
      }
      const aN = av as number
      const bN = bv as number
      return sortDir === 'asc' ? aN - bN : bN - aN
    })
    return copy
  }, [filtered, sortKey, sortDir])

  const loading = isSearching ? searchQ.isPending : trendingQ.isPending

  const toggleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    else { setSortKey(k); setSortDir('desc') }
  }
  const sortArrow = (k: SortKey) => {
    if (sortKey !== k) return <ArrowUpDown className="w-3 h-3 opacity-40" />
    return sortDir === 'asc' ? <ChevronUp className="w-3 h-3 text-accent" /> : <ChevronDown className="w-3 h-3 text-accent" />
  }

  return (
    <PageTransition>
      <div className="space-y-5 py-6">
        {/* Header */}
        <div className="flex items-baseline justify-between flex-wrap gap-3">
          <div>
            <h1 className="font-display text-4xl sm:text-5xl leading-none tracking-tight-er">
              Track
            </h1>
            <div className="text-[11px] font-mono text-muted uppercase tracking-wider mt-2">
              {isSearching
                ? `Search · ${committedQuery}`
                : `Top ${rows.length} cards · sorted by ${sortKey.replace('change_', '')} ${sortDir}`}
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="grid md:grid-cols-[1fr_auto_auto] gap-3">
          <form onSubmit={handleSearchSubmit}>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search a card by name…"
                className="input pl-10 pr-3 h-10 w-full"
              />
            </div>
          </form>

          <select
            value={setFilter}
            onChange={(e) => setSetFilter(e.target.value)}
            className="input h-10 text-[13px] md:w-56"
          >
            <option value="">All sets</option>
            {(setsQ.data?.data ?? []).map(s => (
              <option key={s.id} value={s.name}>{s.name}</option>
            ))}
          </select>

          {isSearching && (
            <button
              onClick={() => { setQuery(''); setCommittedQuery(''); setSearchParams({}) }}
              className="btn btn-outline h-10"
            >
              Clear
            </button>
          )}
        </div>

        {/* Table */}
        <div className="panel-2 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="w-10 text-right pl-5">#</th>
                  <th>
                    <button className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => toggleSort('name')}>
                      Card {sortArrow('name')}
                    </button>
                  </th>
                  <th className="text-right">
                    <button className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => toggleSort('price')}>
                      Last {sortArrow('price')}
                    </button>
                  </th>
                  <th className="text-right w-20">
                    <button className="inline-flex items-center gap-1 hover:text-foreground justify-end w-full" onClick={() => toggleSort('change_7d')}>
                      7d {sortArrow('change_7d')}
                    </button>
                  </th>
                  <th className="text-right w-24 hidden md:table-cell">
                    <button className="inline-flex items-center gap-1 hover:text-foreground justify-end w-full" onClick={() => toggleSort('change_30d')}>
                      30d {sortArrow('change_30d')}
                    </button>
                  </th>
                  <th className="w-24 pr-5 hidden lg:table-cell">Trend</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 12 }).map((_, i) => (
                    <tr key={`sk-${i}`}>
                      <td colSpan={6}><div className="h-12 animate-shimmer rounded my-1" /></td>
                    </tr>
                  ))
                ) : sorted.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center text-muted py-16 font-mono text-xs">
                      {isSearching ? 'No matches. Try a different spelling.' : 'No cards.'}
                    </td>
                  </tr>
                ) : (
                  sorted.map((c, idx) => {
                    const change = c.change_7d ?? 0
                    const Arrow = change > 0 ? TrendingUp : change < 0 ? TrendingDown : Minus
                    return (
                      <motion.tr
                        key={c.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: Math.min(idx, 20) * 0.015 }}
                        onClick={() => navigate(`/cards/${c.id}`)}
                      >
                        <td className="text-right text-muted font-mono text-[11px] pl-5">{idx + 1}</td>
                        <td>
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="relative w-10 h-14 shrink-0 rounded overflow-hidden bg-surface-2 holo-foil">
                              <img
                                src={proxyImageUrl(c.small_image_url || c.image_url || getCardImageUrl(c, 'small'))}
                                alt={c.name}
                                className="w-full h-full object-cover"
                                loading="lazy"
                              />
                            </div>
                            <div className="flex flex-col min-w-0">
                              <span className="text-[13px] font-medium text-foreground truncate">{c.name}</span>
                              <span className="text-[10px] font-mono text-muted truncate flex items-center gap-1.5">
                                <span className="truncate">{c.set_name}</span>
                                {c.rarity && (
                                  <span className={rarityChipClass(c.rarity)}>{c.rarity}</span>
                                )}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="text-right font-mono-numbers text-foreground">
                          ${c.price != null ? formatPrice(c.price) : '—'}
                        </td>
                        <td className="text-right">
                          <span className={`inline-flex items-center gap-0.5 justify-end w-full font-mono-numbers text-[12px] ${
                            change > 0 ? 'delta-up' : change < 0 ? 'delta-down' : 'delta-flat'
                          }`}>
                            <Arrow className="w-3 h-3" />
                            {c.change_7d != null ? `${change >= 0 ? '+' : ''}${change.toFixed(1)}%` : '—'}
                          </span>
                        </td>
                        <td className="text-right font-mono-numbers text-[12px] hidden md:table-cell">
                          {c.change_30d != null ? (
                            <span className={c.change_30d >= 0 ? 'delta-up' : 'delta-down'}>
                              {c.change_30d >= 0 ? '+' : ''}{c.change_30d.toFixed(1)}%
                            </span>
                          ) : <span className="delta-flat">—</span>}
                        </td>
                        <td className="pr-5 hidden lg:table-cell">
                          <Sparkline data={synthLine(c.price, c.change_7d)} width={80} height={22} />
                        </td>
                      </motion.tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          {loading && (
            <div className="flex items-center justify-center py-4 text-muted text-xs font-mono gap-2 border-t border-border">
              <Loader2 className="w-3 h-3 animate-spin" /> Loading markets…
            </div>
          )}
        </div>

        <div className="text-[10px] font-mono text-muted uppercase tracking-[0.2em] text-center py-2">
          Data · TCGPlayer · updated every minute
        </div>
      </div>
    </PageTransition>
  )
}
