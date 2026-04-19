/**
 * Terminal — the home view after Landing.
 * Multi-panel: market pulse / top movers / watchlist / drops feed.
 */
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  TrendingUp, TrendingDown, Minus, ArrowUpRight, ArrowDownRight,
  Activity, Flame, Sparkles, LineChart, Wallet,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import {
  useHealth, useStats, useTrendingCards, useSets,
  useDrops, useDropsLiveIntel,
} from '@/hooks/useApi'
import { formatPrice } from '@/lib/utils'
import { getCardImageUrl, proxyImageUrl } from '@/lib/product-images'
import Sparkline from '@/components/shared/Sparkline'

// Synthesize a sparkline from change_7d for a card (since we don't have per-card
// history in trending response). Short-term fallback until backend adds series.
function synthFromChange(current: number | null, change7d: number | null): number[] {
  if (current == null) return []
  const pct = (change7d ?? 0) / 100
  const start = current / (1 + pct)
  const points: number[] = []
  for (let i = 0; i < 12; i++) {
    const t = i / 11
    // subtle noise + smooth linear interpolation
    const noise = (Math.sin(i * 2.3) + Math.cos(i * 1.7)) * 0.01 * current
    points.push(start + (current - start) * t + noise)
  }
  return points
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { data: healthData } = useHealth()
  const { data: statsData } = useStats()
  const { data: trendingData } = useTrendingCards(30)
  const { data: setsData } = useSets()
  const { data: dropsData } = useDrops('this_month')
  const { data: liveData } = useDropsLiveIntel(undefined, false)

  const isOnline = healthData?.status === 'ok' || healthData?.status === 'healthy'
  const trending = trendingData?.data ?? []

  const { gainers, losers } = useMemo(() => {
    const sorted = [...trending].sort((a, b) => (b.change_7d ?? 0) - (a.change_7d ?? 0))
    return {
      gainers: sorted.filter(c => (c.change_7d ?? 0) > 0).slice(0, 6),
      losers: sorted.filter(c => (c.change_7d ?? 0) < 0).slice(-6).reverse(),
    }
  }, [trending])

  const watchlist = useMemo(() => trending.slice(0, 4), [trending])

  // Market pulse stats
  const avgChange = useMemo(() => {
    const vals = trending.map(c => c.change_7d).filter((n): n is number => n != null)
    if (vals.length === 0) return null
    return vals.reduce((a, b) => a + b, 0) / vals.length
  }, [trending])

  const totalValue = useMemo(() => {
    return trending.reduce((sum, c) => sum + (c.price ?? c.tcgplayer_market ?? 0), 0)
  }, [trending])

  const pulseStats = [
    {
      label: 'Market Pulse',
      value: avgChange != null ? `${avgChange >= 0 ? '+' : ''}${avgChange.toFixed(2)}%` : '—',
      sub: '24h average · trending 30',
      tone: avgChange == null ? 'neutral' : avgChange >= 0 ? 'up' : 'down',
    },
    {
      label: 'Top 30 Cap',
      value: `$${totalValue.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`,
      sub: 'combined market value',
      tone: 'neutral',
    },
    {
      label: 'Sets Indexed',
      value: String(setsData?.data?.length ?? '—'),
      sub: `${(statsData?.collections as Record<string, unknown>)?.unique_cards_tracked ?? 0} cards tracked`,
      tone: 'neutral',
    },
    {
      label: 'System',
      value: isOnline ? 'Online' : 'Offline',
      sub: `API · Render · v2.0`,
      tone: isOnline ? 'up' : 'down',
    },
  ] as const

  const upcomingDrops = (dropsData?.data ?? []).slice(0, 4)
  const liveIntel = (liveData?.data ?? []).slice(0, 6)

  return (
    <PageTransition>
      <div className="space-y-6 py-6">
        {/* ── Header ── */}
        <div className="flex items-baseline justify-between flex-wrap gap-3">
          <div>
            <h1 className="font-display text-4xl sm:text-5xl leading-none tracking-tight-er">
              Terminal
            </h1>
            <div className="flex items-center gap-3 mt-2 text-[11px] font-mono text-muted uppercase tracking-wider">
              <span className="live-dot" />
              {isOnline ? 'Live · all streams connected' : 'Backend disconnected'}
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => navigate('/cards')} className="btn btn-outline">
              <LineChart className="w-3.5 h-3.5" /> Track cards
            </button>
            <button onClick={() => navigate('/portfolio')} className="btn btn-primary">
              <Wallet className="w-3.5 h-3.5" /> Portfolio
            </button>
          </div>
        </div>

        {/* ── Market Pulse strip ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border overflow-hidden rounded">
          {pulseStats.map((s) => (
            <div key={s.label} className="panel-hover bg-background p-5">
              <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted">
                {s.label}
              </div>
              <div className={`font-mono-numbers text-3xl mt-2 leading-none ${
                s.tone === 'up' ? 'delta-up' : s.tone === 'down' ? 'delta-down' : 'text-foreground'
              }`}>
                {s.value}
              </div>
              <div className="text-[11px] text-muted mt-2 truncate">{s.sub}</div>
            </div>
          ))}
        </div>

        {/* ── Movers: gainers + losers ── */}
        <div className="grid lg:grid-cols-2 gap-4">
          <MoversPanel
            title="Top Gainers"
            subtitle="7d"
            items={gainers}
            tone="up"
            onRowClick={(id) => navigate(`/cards/${id}`)}
          />
          <MoversPanel
            title="Top Losers"
            subtitle="7d"
            items={losers}
            tone="down"
            onRowClick={(id) => navigate(`/cards/${id}`)}
          />
        </div>

        {/* ── Watchlist + Live intel ── */}
        <div className="grid lg:grid-cols-3 gap-4">
          {/* Watchlist (left, 2col) */}
          <div className="lg:col-span-2 panel-2 p-5">
            <div className="flex items-baseline justify-between mb-4">
              <div>
                <h3 className="font-display italic text-2xl leading-none">Watchlist</h3>
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted mt-1.5">
                  Pinned · auto-refresh 60s
                </div>
              </div>
              <button onClick={() => navigate('/cards')} className="text-[11px] text-muted hover:text-accent font-mono uppercase tracking-wider transition-colors">
                Browse →
              </button>
            </div>

            {watchlist.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-muted text-sm font-mono">Loading…</div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {watchlist.map((card) => {
                  const price = card.price ?? card.tcgplayer_market ?? null
                  const change = card.change_7d ?? 0
                  const isUp = change > 0
                  return (
                    <motion.button
                      key={card.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={() => navigate(`/cards/${card.id}`)}
                      whileHover={{ y: -2 }}
                      className="panel p-3 text-left transition-colors hover:border-border-light"
                    >
                      <div className="flex gap-3">
                        <div className="relative w-14 h-20 shrink-0 rounded overflow-hidden bg-surface-2 holo-foil">
                          <img
                            src={proxyImageUrl(getCardImageUrl(card, 'small'))}
                            alt={card.name}
                            className="w-full h-full object-cover"
                            loading="lazy"
                          />
                        </div>
                        <div className="flex-1 min-w-0 flex flex-col justify-between">
                          <div>
                            <div className="text-[13px] font-medium text-foreground truncate leading-tight">
                              {card.name}
                            </div>
                            <div className="text-[10px] font-mono text-muted truncate mt-0.5">
                              {card.set_name}
                            </div>
                          </div>
                          <div className="flex items-end justify-between gap-2">
                            <div className="font-mono-numbers text-lg text-foreground leading-none">
                              ${price != null ? formatPrice(price) : '—'}
                            </div>
                            <div className={`text-[11px] font-mono-numbers leading-none ${
                              isUp ? 'delta-up' : change < 0 ? 'delta-down' : 'delta-flat'
                            }`}>
                              {change != null ? `${isUp ? '+' : ''}${change.toFixed(1)}%` : '—'}
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="mt-2">
                        <Sparkline data={synthFromChange(price, change)} height={28} />
                      </div>
                    </motion.button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Live intel (right) */}
          <div className="panel-2 p-5">
            <div className="flex items-baseline justify-between mb-4">
              <div>
                <h3 className="font-display italic text-2xl leading-none">Signal</h3>
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted mt-1.5">
                  Live intel feed
                </div>
              </div>
              <Activity className="w-4 h-4 text-muted" />
            </div>

            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {liveIntel.length === 0 ? (
                <div className="text-muted text-xs font-mono">No intel.</div>
              ) : (
                liveIntel.map((item) => (
                  <div key={item.id} className="border-l-2 border-border pl-3 hover:border-accent transition-colors">
                    <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider">
                      <span className="text-accent">{item.source}</span>
                      <span className="text-muted">·</span>
                      <span className="text-muted">{item.timestamp}</span>
                    </div>
                    <p className="text-[12px] text-foreground-dim mt-1 leading-snug">{item.content}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* ── Drops strip ── */}
        <div className="panel-2 p-5">
          <div className="flex items-baseline justify-between mb-4">
            <div>
              <h3 className="font-display italic text-2xl leading-none">
                Coming up <span className="text-muted not-italic">·</span> <span className="text-accent">drops</span>
              </h3>
              <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted mt-1.5">
                This month
              </div>
            </div>
            <button onClick={() => navigate('/drops')} className="text-[11px] text-muted hover:text-accent font-mono uppercase tracking-wider transition-colors">
              All drops →
            </button>
          </div>

          {upcomingDrops.length === 0 ? (
            <div className="text-muted text-xs font-mono h-24 flex items-center">No drops scheduled this month.</div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {upcomingDrops.map((drop) => (
                <button
                  key={drop.id}
                  onClick={() => navigate('/drops')}
                  className="panel p-3 text-left hover:border-border-light transition-colors"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Flame className="w-3 h-3 text-accent" />
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted">
                      {drop.type.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-[13px] font-medium text-foreground leading-tight truncate">
                    {drop.title}
                  </div>
                  <div className="flex items-baseline justify-between mt-3">
                    <span className="text-[11px] font-mono text-muted">{drop.date_label}</span>
                    <span className="font-mono-numbers text-[13px] text-accent">
                      {drop.days_until}d
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── Quick actions ── */}
        <div className="grid sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {[
            { label: 'Cards', icon: LineChart, path: '/cards' },
            { label: 'Sealed', icon: Sparkles, path: '/sealed' },
            { label: 'Portfolio', icon: Wallet, path: '/portfolio' },
            { label: 'Monitors', icon: Activity, path: '/monitors' },
            { label: 'Flip', icon: ArrowUpRight, path: '/flip' },
            { label: 'Settings', icon: ArrowDownRight, path: '/settings' },
          ].map((a) => {
            const Icon = a.icon
            return (
              <button
                key={a.path}
                onClick={() => navigate(a.path)}
                className="panel-hover panel p-4 text-left group"
              >
                <Icon className="w-4 h-4 text-muted group-hover:text-accent transition-colors" />
                <div className="mt-2 text-[13px] font-medium text-foreground">{a.label}</div>
              </button>
            )
          })}
        </div>
      </div>
    </PageTransition>
  )
}

// ── Movers panel (sub-component) ─────────────────────────
interface MoversItem {
  id: string
  name: string
  set_name?: string
  price: number | null
  change_7d?: number | null
  tcgplayer_market?: number | null
}

function MoversPanel({
  title, subtitle, items, tone, onRowClick,
}: {
  title: string; subtitle: string
  items: MoversItem[]; tone: 'up' | 'down'
  onRowClick: (id: string) => void
}) {
  return (
    <div className="panel-2 overflow-hidden">
      <div className="flex items-baseline justify-between px-5 pt-5 pb-4">
        <h3 className="font-display italic text-2xl leading-none">{title}</h3>
        <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted">{subtitle}</div>
      </div>

      {items.length === 0 ? (
        <div className="px-5 pb-5 text-muted text-xs font-mono">No data.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Card</th>
              <th className="text-right w-24">Last</th>
              <th className="text-right w-24">7d</th>
              <th className="w-24 text-right pr-5">Trend</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => {
              const price = c.price ?? c.tcgplayer_market ?? null
              const change = c.change_7d ?? 0
              const Arrow = tone === 'up' ? TrendingUp : tone === 'down' ? TrendingDown : Minus
              return (
                <tr key={c.id} onClick={() => onRowClick(c.id)}>
                  <td>
                    <div className="flex flex-col">
                      <span className="text-[13px] text-foreground truncate max-w-[22ch]">{c.name}</span>
                      <span className="text-[10px] font-mono text-muted truncate max-w-[22ch]">{c.set_name}</span>
                    </div>
                  </td>
                  <td className="text-right font-mono-numbers text-foreground">
                    ${price != null ? formatPrice(price) : '—'}
                  </td>
                  <td className="text-right">
                    <span className={`inline-flex items-center gap-0.5 font-mono-numbers text-[12px] ${
                      tone === 'up' ? 'delta-up' : 'delta-down'
                    }`}>
                      <Arrow className="w-3 h-3" />
                      {change >= 0 ? '+' : ''}{change.toFixed(1)}%
                    </span>
                  </td>
                  <td className="pr-5">
                    <Sparkline data={synthFromChange(price, change)} width={80} height={22} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
