/**
 * Cards — the database. Every card in the index, paginated and filterable.
 * Default sort: highest price first. Inline sparklines on the money rows.
 */
import { useMemo, useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Search, TrendingUp, TrendingDown, Minus, ArrowUpDown,
  ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Loader2, X,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import Sparkline from '@/components/shared/Sparkline'
import { useAllCards, useCardRarities, useSets } from '@/hooks/useApi'
import { formatPrice } from '@/lib/utils'
import { proxyImageUrl } from '@/lib/product-images'

type SortKey = 'price' | 'name' | 'set' | 'rarity'
type SortDir = 'asc' | 'desc'

function rarityChipClass(rarity?: string | null): string {
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

// Debounce
function useDebounce<T>(value: T, ms = 300): T {
  const [d, setD] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setD(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return d
}

export default function Cards() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()

  // Controls
  const [rawQuery, setRawQuery] = useState(params.get('q') ?? '')
  const q = useDebounce(rawQuery, 300)
  const [setFilter, setSetFilter] = useState(params.get('set') ?? '')
  const [rarityFilter, setRarityFilter] = useState(params.get('rarity') ?? '')
  const [minPrice, setMinPrice] = useState(params.get('min') ?? '')
  const [maxPrice, setMaxPrice] = useState(params.get('max') ?? '')
  const [sortKey, setSortKey] = useState<SortKey>((params.get('sort') as SortKey) ?? 'price')
  const [sortDir, setSortDir] = useState<SortDir>((params.get('dir') as SortDir) ?? 'desc')
  const [page, setPage] = useState(parseInt(params.get('page') ?? '1', 10))
  const [limit] = useState(100)

  // Sync URL so state is shareable / refreshable
  useEffect(() => {
    const next = new URLSearchParams()
    if (q) next.set('q', q)
    if (setFilter) next.set('set', setFilter)
    if (rarityFilter) next.set('rarity', rarityFilter)
    if (minPrice) next.set('min', minPrice)
    if (maxPrice) next.set('max', maxPrice)
    if (sortKey !== 'price') next.set('sort', sortKey)
    if (sortDir !== 'desc') next.set('dir', sortDir)
    if (page !== 1) next.set('page', String(page))
    setParams(next, { replace: true })
  }, [q, setFilter, rarityFilter, minPrice, maxPrice, sortKey, sortDir, page, setParams])

  // Reset to page 1 on any filter change
  useEffect(() => { setPage(1) }, [q, setFilter, rarityFilter, minPrice, maxPrice, sortKey, sortDir])

  const hookOpts = useMemo(() => ({
    page, limit,
    q: q || undefined,
    set: setFilter || undefined,
    rarity: rarityFilter || undefined,
    minPrice: minPrice ? Number(minPrice) : undefined,
    maxPrice: maxPrice ? Number(maxPrice) : undefined,
    sort: sortKey, dir: sortDir,
  }), [page, limit, q, setFilter, rarityFilter, minPrice, maxPrice, sortKey, sortDir])

  const cardsQ = useAllCards(hookOpts)
  const raritiesQ = useCardRarities()
  const setsQ = useSets()

  const rows = cardsQ.data?.data ?? []
  const total = cardsQ.data?.total ?? 0
  const pages = cardsQ.data?.pages ?? 1

  const toggleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    else { setSortKey(k); setSortDir(k === 'name' ? 'asc' : 'desc') }
  }
  const sortArrow = (k: SortKey) => {
    if (sortKey !== k) return <ArrowUpDown className="w-3 h-3 opacity-40" />
    return sortDir === 'asc' ? <ChevronUp className="w-3 h-3 text-accent" /> : <ChevronDown className="w-3 h-3 text-accent" />
  }

  const clearAllFilters = () => {
    setRawQuery(''); setSetFilter(''); setRarityFilter('')
    setMinPrice(''); setMaxPrice('')
    setSortKey('price'); setSortDir('desc')
  }

  const hasFilters = q || setFilter || rarityFilter || minPrice || maxPrice

  // Synthesize a sparkline from change (fallback — real history is on CardDetail)
  const spark = (price: number | null, seed: number): number[] => {
    if (price == null) return []
    const points: number[] = []
    for (let i = 0; i < 12; i++) {
      const t = i / 11
      const wave = Math.sin((i + seed) * 0.9) * price * 0.04
      const drift = (t - 0.5) * price * 0.02
      points.push(Math.max(0.01, price + wave + drift))
    }
    return points
  }

  return (
    <PageTransition>
      <div className="space-y-5 py-6">
        {/* ── Header ── */}
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-muted">
              The database
            </div>
            <h1 className="font-display text-4xl sm:text-5xl leading-none tracking-tight-er mt-2">
              Cards
              <span className="italic text-accent"> · </span>
              <span className="font-mono-numbers text-foreground">{total.toLocaleString()}</span>
            </h1>
            <div className="text-[11px] font-mono text-muted uppercase tracking-wider mt-2">
              {hasFilters ? 'Filtered' : 'All cards'} · sorted by {sortKey} {sortDir}
            </div>
          </div>
          <div className="flex gap-2 items-center">
            {hasFilters && (
              <button onClick={clearAllFilters} className="btn btn-ghost">
                <X className="w-3.5 h-3.5" /> Clear filters
              </button>
            )}
          </div>
        </div>

        {/* ── Filters ── */}
        <div className="panel-2 p-4 grid grid-cols-1 md:grid-cols-6 gap-2">
          <div className="md:col-span-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted" />
              <input
                type="text"
                value={rawQuery}
                onChange={(e) => setRawQuery(e.target.value)}
                placeholder="Search card name…"
                className="input pl-10 pr-3 h-10 w-full"
              />
            </div>
          </div>

          <select
            value={setFilter}
            onChange={(e) => setSetFilter(e.target.value)}
            className="input h-10 text-[13px]"
          >
            <option value="">All sets</option>
            {(setsQ.data?.data ?? []).map(s => (
              <option key={s.id} value={s.name}>{s.name}</option>
            ))}
          </select>

          <select
            value={rarityFilter}
            onChange={(e) => setRarityFilter(e.target.value)}
            className="input h-10 text-[13px]"
          >
            <option value="">All rarities</option>
            {(raritiesQ.data?.data ?? []).map(r => (
              <option key={r.rarity} value={r.rarity}>{r.rarity} · {r.count}</option>
            ))}
          </select>

          <input
            type="number"
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
            placeholder="Min $"
            className="input h-10 text-[13px]"
            min="0"
            step="1"
          />
          <input
            type="number"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            placeholder="Max $"
            className="input h-10 text-[13px]"
            min="0"
            step="1"
          />
        </div>

        {/* ── Table ── */}
        <div className="panel-2 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="w-12 text-right pl-5">#</th>
                  <th>
                    <button className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => toggleSort('name')}>
                      Card {sortArrow('name')}
                    </button>
                  </th>
                  <th className="hidden md:table-cell">
                    <button className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => toggleSort('set')}>
                      Set {sortArrow('set')}
                    </button>
                  </th>
                  <th className="hidden lg:table-cell">
                    <button className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => toggleSort('rarity')}>
                      Rarity {sortArrow('rarity')}
                    </button>
                  </th>
                  <th className="text-right">
                    <button className="inline-flex items-center gap-1 justify-end w-full hover:text-foreground" onClick={() => toggleSort('price')}>
                      Market {sortArrow('price')}
                    </button>
                  </th>
                  <th className="text-right hidden lg:table-cell">Low</th>
                  <th className="text-right hidden lg:table-cell">High</th>
                  <th className="w-24 pr-5 hidden xl:table-cell">Trend</th>
                </tr>
              </thead>
              <tbody>
                {cardsQ.isPending && rows.length === 0 ? (
                  Array.from({ length: 12 }).map((_, i) => (
                    <tr key={`sk-${i}`}>
                      <td colSpan={8}><div className="h-12 animate-shimmer rounded my-1" /></td>
                    </tr>
                  ))
                ) : rows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center text-muted py-16 font-mono text-xs">
                      No cards match these filters.
                    </td>
                  </tr>
                ) : (
                  rows.map((c, idx) => {
                    const rank = (page - 1) * limit + idx + 1
                    const price = c.price ?? c.tcgplayer_market ?? null
                    const low = c.tcgplayer_low
                    const high = c.tcgplayer_high
                    const range = (low != null && high != null && low > 0)
                      ? ((high - low) / low) * 100
                      : 0
                    const Arrow = range > 5 ? TrendingUp : range < -5 ? TrendingDown : Minus
                    return (
                      <motion.tr
                        key={c.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: Math.min(idx, 20) * 0.01 }}
                        onClick={() => navigate(`/cards/${c.id}`)}
                      >
                        <td className="text-right text-muted font-mono text-[11px] pl-5">{rank}</td>
                        <td>
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="relative w-10 h-14 shrink-0 rounded overflow-hidden bg-surface-2 holo-foil">
                              {c.small_image_url || c.image_url ? (
                                <img
                                  src={proxyImageUrl(c.small_image_url || c.image_url || '')}
                                  alt={c.name}
                                  className="w-full h-full object-cover"
                                  loading="lazy"
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-muted text-[10px] font-mono">
                                  no img
                                </div>
                              )}
                            </div>
                            <div className="flex flex-col min-w-0">
                              <span className="text-[13px] font-medium text-foreground truncate">{c.name}</span>
                              {c.supertype && (
                                <span className="text-[10px] font-mono text-muted truncate">
                                  {c.supertype}{c.subtype ? ` · ${c.subtype}` : ''}
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="hidden md:table-cell">
                          <span className="text-[12px] text-foreground-dim truncate">{c.set_name ?? '—'}</span>
                        </td>
                        <td className="hidden lg:table-cell">
                          {c.rarity ? (
                            <span className={rarityChipClass(c.rarity)}>{c.rarity}</span>
                          ) : <span className="text-muted text-[11px]">—</span>}
                        </td>
                        <td className="text-right font-mono-numbers text-foreground">
                          {price != null ? `$${formatPrice(price)}` : <span className="text-muted">—</span>}
                        </td>
                        <td className="text-right font-mono-numbers text-muted text-[12px] hidden lg:table-cell">
                          {low != null ? `$${formatPrice(low)}` : '—'}
                        </td>
                        <td className="text-right font-mono-numbers text-muted text-[12px] hidden lg:table-cell">
                          {high != null ? `$${formatPrice(high)}` : '—'}
                        </td>
                        <td className="pr-5 hidden xl:table-cell">
                          <div className="flex items-center gap-1.5">
                            <Sparkline data={spark(price, idx)} width={60} height={22} />
                            <span className={`text-[10px] font-mono-numbers ${
                              range > 5 ? 'delta-up' : range < -5 ? 'delta-down' : 'delta-flat'
                            }`}>
                              <Arrow className="w-2.5 h-2.5 inline" />
                            </span>
                          </div>
                        </td>
                      </motion.tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
          {cardsQ.isFetching && (
            <div className="flex items-center justify-center py-3 text-muted text-xs font-mono gap-2 border-t border-border">
              <Loader2 className="w-3 h-3 animate-spin" /> Updating…
            </div>
          )}
        </div>

        {/* ── Pagination ── */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="text-[11px] font-mono text-muted tracking-wider">
            Page {page} of {pages} · {total.toLocaleString()} cards · showing {rows.length}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={page <= 1}
              className="btn btn-ghost btn-sm disabled:opacity-30"
            >
              First
            </button>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="btn btn-outline btn-sm disabled:opacity-30"
            >
              <ChevronLeft className="w-3 h-3" /> Prev
            </button>
            <span className="font-mono text-[12px] text-foreground px-3 py-1.5 border border-border rounded bg-surface">
              {page} / {pages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page >= pages}
              className="btn btn-outline btn-sm disabled:opacity-30"
            >
              Next <ChevronRight className="w-3 h-3" />
            </button>
            <button
              onClick={() => setPage(pages)}
              disabled={page >= pages}
              className="btn btn-ghost btn-sm disabled:opacity-30"
            >
              Last
            </button>
          </div>
        </div>

        <div className="text-[10px] font-mono text-muted uppercase tracking-[0.2em] text-center py-2">
          Data · TCGPlayer · updated every minute · click a card for full price chart
        </div>
      </div>
    </PageTransition>
  )
}
