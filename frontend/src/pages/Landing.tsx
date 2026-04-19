/**
 * Landing — editorial hero, live ticker, feature grid. Public-facing.
 */
import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, Activity, LineChart, Wallet, Bell, Flame, Sparkles,
  TrendingUp, TrendingDown, Minus,
} from 'lucide-react'
import { useSets, useHealth, useTrendingCards } from '@/hooks/useApi'
import { formatPrice } from '@/lib/utils'
import Sparkline from '@/components/shared/Sparkline'

const FEATURES = [
  {
    icon: LineChart,
    title: 'Every price, charted.',
    body: '2,400+ modern cards with tick-by-tick TCGPlayer, eBay sold, and graded-copy history.',
  },
  {
    icon: Activity,
    title: 'A terminal, not a toy.',
    body: 'Dense tables. Inline sparklines. Sortable by 24h, 7d, 30d delta. No hand-holding.',
  },
  {
    icon: Wallet,
    title: 'Your book, your PnL.',
    body: 'Track raw, PSA-10, BGS-9.5. Purchase-price cost basis. Realised vs unrealised.',
  },
  {
    icon: Bell,
    title: 'Alerts that fire.',
    body: 'Stock monitors wired to Discord. Price thresholds. Set once, forget.',
  },
  {
    icon: Flame,
    title: 'Drops before they drop.',
    body: 'Calendar, rumours, live sightings from Reddit, PokeBeach, Twitter.',
  },
  {
    icon: Sparkles,
    title: 'Grade or sell raw.',
    body: 'PSA / CGC / BGS cost + outcome modelling. Break-even in one click.',
  },
]

function formatNumber(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1000) return n.toLocaleString('en-US')
  return String(n)
}

export default function Landing() {
  const navigate = useNavigate()
  const setsQ = useSets()
  const healthQ = useHealth()
  const trendingQ = useTrendingCards(8)

  const setsCount = setsQ.data?.data?.length ?? null
  const cardsTracked = setsCount != null ? setsCount * 200 : null
  const isOnline = healthQ.data?.status === 'ok' || healthQ.data?.status === 'healthy'

  const tickers = useMemo(() => {
    const cards = trendingQ.data?.data ?? []
    return cards.slice(0, 6).map(c => ({
      id: c.id,
      name: c.name,
      price: c.price ?? c.tcgplayer_market ?? null,
      change: c.change_7d ?? c.change_30d ?? null,
      set: c.set_name ?? '',
    }))
  }, [trendingQ.data])

  return (
    <div className="min-h-screen bg-background text-foreground relative overflow-hidden">
      <div className="ambient-orbs" aria-hidden="true" />

      {/* Sticky minimal header for Landing */}
      <header className="sticky top-0 z-40 h-14 border-b border-border bg-background/80 backdrop-blur-xl flex items-center px-6">
        <div className="flex items-center gap-3">
          <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" stroke="var(--color-accent)" />
            <line x1="2" y1="12" x2="22" y2="12" stroke="var(--color-foreground-dim)" />
            <circle cx="12" cy="12" r="3" stroke="var(--color-foreground-dim)" fill="var(--color-background)" />
          </svg>
          <span className="font-display italic text-[22px] leading-none">pokeagent</span>
          <span className="hidden sm:inline text-[10px] font-mono tracking-[0.2em] uppercase text-muted ml-2">Terminal</span>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-1.5 text-[10px] font-mono tracking-wider uppercase text-muted">
            <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-success' : healthQ.isPending ? 'bg-warning' : 'bg-danger'}`} />
            {isOnline ? 'Online' : healthQ.isPending ? 'Checking' : 'Offline'}
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn btn-primary"
          >
            Enter Terminal <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* ── HERO ── */}
      <section className="relative px-6 pt-20 pb-24 sm:pt-32 sm:pb-32">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="grid lg:grid-cols-[1.35fr_1fr] gap-12 items-center"
          >
            {/* Left — headline */}
            <div>
              <div className="chip chip-accent mb-6">
                <span className="live-dot w-1 h-1" style={{ boxShadow: 'none' }} />
                live card markets
              </div>

              <h1 className="font-display text-[clamp(3rem,8vw,6.5rem)] leading-[0.95] tracking-tight-er text-foreground">
                Watch every card<br />
                <span className="italic text-accent">like a ticker.</span>
              </h1>

              <p className="mt-8 max-w-xl text-lg text-foreground-dim leading-relaxed">
                A Pokemon TCG price terminal. Real-time TCGPlayer + eBay + graded-copy
                charts across 2,400+ cards and every modern sealed product. Inline
                sparklines. Sortable tables. Zero fluff.
              </p>

              <div className="mt-10 flex flex-wrap items-center gap-3">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="btn btn-primary btn-lg"
                >
                  Enter Terminal <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => navigate('/cards')}
                  className="btn btn-outline btn-lg"
                >
                  Browse cards
                </button>
              </div>
            </div>

            {/* Right — live snapshot card */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="panel-2 p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="live-dot" />
                  <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-muted">Trending · 7d</span>
                </div>
                <span className="text-[10px] font-mono text-muted">TCGPlayer</span>
              </div>

              <div className="space-y-0.5">
                {tickers.length === 0 ? (
                  Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-11 animate-shimmer rounded" />
                  ))
                ) : (
                  tickers.map((t, i) => {
                    const isUp = (t.change ?? 0) > 0
                    const isDown = (t.change ?? 0) < 0
                    const Arrow = isUp ? TrendingUp : isDown ? TrendingDown : Minus
                    return (
                      <motion.button
                        key={t.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 + i * 0.05 }}
                        onClick={() => navigate(`/cards/${t.id}`)}
                        className="w-full flex items-center justify-between gap-3 py-2.5 px-1 -mx-1 rounded hover:bg-surface-hover transition-colors text-left"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="text-[13px] text-foreground truncate">{t.name}</div>
                          <div className="text-[10px] font-mono text-muted truncate">{t.set}</div>
                        </div>
                        <div className="font-mono-numbers text-[13px] text-foreground tabular-nums">
                          ${t.price != null ? formatPrice(t.price) : '—'}
                        </div>
                        <div className={`font-mono-numbers text-[11px] tabular-nums w-16 text-right flex items-center justify-end gap-0.5 ${
                          isUp ? 'delta-up' : isDown ? 'delta-down' : 'delta-flat'
                        }`}>
                          <Arrow className="w-3 h-3" />
                          {t.change != null ? `${isUp ? '+' : ''}${t.change.toFixed(1)}%` : '—'}
                        </div>
                      </motion.button>
                    )
                  })
                )}
              </div>

              <div className="mt-5 pt-4 border-t border-border grid grid-cols-3 text-center">
                <div>
                  <div className="font-mono-numbers text-lg text-foreground">{formatNumber(cardsTracked)}</div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted">Cards</div>
                </div>
                <div className="border-x border-border">
                  <div className="font-mono-numbers text-lg text-foreground">{formatNumber(setsCount)}</div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted">Sets</div>
                </div>
                <div>
                  <div className="font-mono-numbers text-lg text-foreground">7</div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted">Retailers</div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="relative px-6 py-20 border-t border-border">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-baseline justify-between mb-14">
            <h2 className="font-display italic text-4xl sm:text-5xl">The kit.</h2>
            <span className="hidden sm:inline font-mono text-[11px] tracking-[0.2em] uppercase text-muted">
              / 06
            </span>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border">
            {FEATURES.map((f, i) => {
              const Icon = f.icon
              return (
                <motion.div
                  key={f.title}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-80px' }}
                  transition={{ delay: i * 0.05 }}
                  className="bg-background p-7 group hover:bg-surface transition-colors"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-9 h-9 rounded-md bg-surface-2 border border-border flex items-center justify-center">
                      <Icon className="w-4 h-4 text-accent" />
                    </div>
                    <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted">
                      /0{i + 1}
                    </span>
                  </div>
                  <h3 className="font-display text-2xl leading-tight mb-2 text-foreground">
                    {f.title}
                  </h3>
                  <p className="text-sm text-foreground-dim leading-relaxed">
                    {f.body}
                  </p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── BIG NUMBERS ── */}
      <section className="relative px-6 py-20 border-t border-border">
        <div className="max-w-6xl mx-auto">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { label: 'Cards in index', value: formatNumber(cardsTracked) },
              { label: 'Sets covered', value: formatNumber(setsCount) },
              { label: 'Retailers tracked', value: '7' },
              { label: 'Grading services', value: '3' },
            ].map((stat) => (
              <div key={stat.label} className="border-t border-border pt-6">
                <div className="font-display text-[clamp(2.5rem,6vw,4.5rem)] leading-none text-foreground">
                  {stat.value}
                </div>
                <div className="mt-3 font-mono text-[10px] tracking-[0.22em] uppercase text-muted">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-16 flex flex-wrap items-center justify-center gap-6">
            <div className="relative">
              <Sparkline data={[1, 3, 2, 5, 4, 7, 6, 9, 8, 12, 11, 14]} width={180} height={40} color="accent" strokeWidth={1.5} />
              <div className="absolute inset-x-0 -bottom-6 text-center font-mono text-[10px] tracking-[0.2em] uppercase text-muted">
                Index · 12M
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="relative px-6 py-28 border-t border-border text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-[clamp(2.5rem,6vw,5rem)] leading-[0.95] text-foreground">
            Open the<br />
            <span className="italic text-accent">terminal.</span>
          </h2>
          <p className="mt-6 text-foreground-dim max-w-xl mx-auto">
            Free to explore. Connect a wallet to unlock portfolio &amp; monitors.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn btn-primary btn-lg mt-10"
          >
            Enter <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-display italic text-lg">pokeagent</span>
            <span className="font-mono text-[10px] tracking-widest uppercase text-muted">v2.0 · 2026</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="https://drip.trade/collections/locals-only" target="_blank" rel="noopener noreferrer" className="text-[11px] text-muted hover:text-foreground transition-colors font-mono uppercase tracking-wider">Locals Only</a>
            <a href="https://x.com/demi_hl" target="_blank" rel="noopener noreferrer" className="text-[11px] text-muted hover:text-foreground transition-colors font-mono uppercase tracking-wider">Twitter</a>
            <a href="https://discord.gg/a56Tjc7BEr" target="_blank" rel="noopener noreferrer" className="text-[11px] text-muted hover:text-foreground transition-colors font-mono uppercase tracking-wider">Discord</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
