import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import {
  DollarSign, Bell, CreditCard, TrendingUp, TrendingDown,
  Search, Flame, Sparkles, ArrowRight, Activity, ArrowUpRight,
  Zap, Eye, BarChart3, Wifi, WifiOff,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { useHealth, useStats } from '@/hooks/useApi'

/* ── Animated counter ── */
function AnimatedNumber({ value, prefix = '', suffix = '', duration = 1.6 }: {
  value: number; prefix?: string; suffix?: string; duration?: number
}) {
  const mv = useMotionValue(0)
  const display = useTransform(mv, (v) => {
    if (value >= 1000) return `${prefix}${Math.round(v).toLocaleString()}${suffix}`
    return `${prefix}${Math.round(v)}${suffix}`
  })
  useEffect(() => {
    const ctrl = animate(mv, value, { duration, ease: [0.22, 1, 0.36, 1] })
    return ctrl.stop
  }, [mv, value, duration])
  return <motion.span>{display}</motion.span>
}

const ACTIONS = [
  { label: 'Find Stock', desc: 'Search retailers near you', icon: Search, path: '/stock', gradient: 'from-blue-400/8 via-transparent to-transparent', iconColor: 'text-blue-400' },
  { label: 'Card Lookup', desc: 'Prices & market data', icon: CreditCard, path: '/cards', gradient: 'from-indigo-400/8 via-transparent to-transparent', iconColor: 'text-indigo-400' },
  { label: 'Drop Calendar', desc: 'Upcoming releases', icon: Flame, path: '/drops', gradient: 'from-cyan-400/8 via-transparent to-transparent', iconColor: 'text-cyan-400' },
  { label: 'AI Grading', desc: 'Grade cards from photos', icon: Sparkles, path: '/grading', gradient: 'from-violet-400/8 via-transparent to-transparent', iconColor: 'text-violet-400' },
]

const TRENDING = [
  { name: 'Prismatic Evolutions ETB', price: '$74.99', change: '+15%', up: true },
  { name: 'Surging Sparks BB', price: '$129.99', change: '+3%', up: true },
  { name: '151 ETB', price: '$54.99', change: '-2%', up: false },
  { name: 'Evolving Skies BB', price: '$420.00', change: '+8%', up: true },
  { name: 'Obsidian Flames BB', price: '$109.99', change: '+1%', up: true },
]

const FEED = [
  { text: 'Charizard ex detected at Target — Aisle D42', time: '2m', color: 'bg-emerald-500' },
  { text: 'Prismatic Evolutions restocked at Walmart', time: '18m', color: 'bg-blue-500' },
  { text: 'Pikachu VMAX price dropped 12%', time: '45m', color: 'bg-rose-500' },
  { text: 'New PSA 10 listing — Umbreon VMAX Alt', time: '1h', color: 'bg-amber-500' },
  { text: 'Surging Sparks back in stock at Pokemon Center', time: '2h', color: 'bg-violet-500' },
]

/* ── Page ── */
export default function Dashboard() {
  const navigate = useNavigate()
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])

  // Wire to real API
  const { data: healthData } = useHealth()
  const { data: statsData } = useStats()

  const isConnected = healthData?.status === 'ok' || healthData?.status === 'healthy'

  // Build KPI from real stats or fallback to defaults
  const collectionStats = statsData?.collections as Record<string, number> | undefined
  const alertStats = statsData?.alerts as Record<string, number> | undefined

  const KPI = [
    {
      label: 'Portfolio Value',
      value: collectionStats?.total_value ?? 0,
      prefix: '$',
      icon: DollarSign,
      delta: isConnected ? 'Live' : 'Offline',
      up: isConnected,
      accent: 'from-blue-400/15 to-blue-500/5',
    },
    {
      label: 'Active Alerts',
      value: alertStats?.active_alerts ?? 0,
      prefix: '',
      icon: Activity,
      delta: `${alertStats?.triggered_today ?? 0} triggered`,
      up: true,
      accent: 'from-cyan-400/15 to-cyan-500/5',
    },
    {
      label: 'Cards Tracked',
      value: collectionStats?.total_items ?? 0,
      prefix: '',
      icon: Eye,
      accent: 'from-indigo-400/15 to-indigo-500/5',
    },
    {
      label: 'Backend Status',
      value: isConnected ? 1 : 0,
      prefix: '',
      icon: isConnected ? Wifi : WifiOff,
      delta: isConnected ? 'Connected' : 'Disconnected',
      up: isConnected,
      accent: 'from-teal-400/15 to-teal-500/5',
    },
  ]

  return (
    <PageTransition>
      <div className="space-y-8">

        {/* ── Hero section ── */}
        <motion.section
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="relative overflow-hidden rounded-2xl border border-white/[0.04] bg-gradient-to-br from-white/[0.02] to-transparent p-8 sm:p-12"
        >
          {/* Decorative elements */}
          <div className="pointer-events-none absolute -top-40 -right-40 w-96 h-96 rounded-full bg-accent/[0.05] blur-[120px]" />
          <div className="pointer-events-none absolute -bottom-32 -left-32 w-72 h-72 rounded-full bg-blue-500/[0.04] blur-[100px]" />
          <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-violet-500/[0.02] blur-[150px]" />

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-accent/70 mb-4">
              <span className="h-1 w-1 rounded-full bg-accent/60" />
              TCG Intelligence Platform
            </span>
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="text-3xl sm:text-4xl lg:text-[2.75rem] font-bold tracking-[-0.03em] text-foreground leading-[1.1]"
          >
            Welcome back
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="mt-3 text-sm sm:text-[15px] text-muted-foreground/70 max-w-lg leading-relaxed"
          >
            Track prices, find stock, and manage your collection — all powered by AI agents.
            {isConnected && (
              <span className="inline-flex items-center gap-1.5 ml-2 text-emerald-400 text-xs font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Backend connected
              </span>
            )}
          </motion.p>
        </motion.section>

        {/* ── KPI Cards ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {KPI.map((k, i) => {
            const Icon = k.icon
            return (
              <motion.div
                key={k.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.06, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              >
                <div className="group relative rounded-2xl border border-white/[0.04] bg-gradient-to-b from-white/[0.02] to-transparent p-5 sm:p-6 hover:border-white/[0.08] transition-all duration-500">
                  {/* Subtle gradient accent */}
                  <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${k.accent} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />

                  <div className="relative">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/60">{k.label}</span>
                      <div className="h-8 w-8 rounded-xl bg-white/[0.04] flex items-center justify-center group-hover:bg-white/[0.06] transition-colors duration-300">
                        <Icon className="h-3.5 w-3.5 text-muted-foreground/50 group-hover:text-accent/70 transition-colors duration-300" />
                      </div>
                    </div>
                    <p className="text-2xl sm:text-3xl font-mono-numbers font-bold tracking-[-0.02em]">
                      {k.label === 'Backend Status' ? (
                        <span className={isConnected ? 'text-emerald-400' : 'text-rose-400'}>
                          {isConnected ? 'Online' : 'Offline'}
                        </span>
                      ) : (
                        mounted ? <AnimatedNumber value={k.value} prefix={k.prefix} /> : `${k.prefix}0`
                      )}
                    </p>
                    {k.delta && (
                      <div className="mt-2.5 flex items-center gap-1">
                        <span className={`inline-flex items-center gap-0.5 text-[11px] font-semibold ${k.up ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {k.up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                          {k.delta}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* ── Quick Actions ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {ACTIONS.map((a, i) => {
            const Icon = a.icon
            return (
              <motion.div
                key={a.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.06, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              >
                <motion.button
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.98 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => navigate(a.path)}
                  className={`w-full text-left rounded-2xl border border-white/[0.04] bg-gradient-to-br ${a.gradient} p-5 sm:p-6 hover:border-white/[0.08] transition-all duration-400 group`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <Icon className={`h-5 w-5 ${a.iconColor} opacity-80`} />
                    <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground/20 group-hover:text-accent/60 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all duration-300" />
                  </div>
                  <p className="text-sm font-semibold text-foreground/90">{a.label}</p>
                  <p className="text-[11px] text-muted-foreground/50 mt-0.5">{a.desc}</p>
                </motion.button>
              </motion.div>
            )
          })}
        </div>

        {/* ── Bottom row: Trending + Feed ── */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 sm:gap-6">
          {/* Trending */}
          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-[13px] font-semibold tracking-[-0.01em] text-foreground/80">Trending Products</h2>
              <button
                onClick={() => navigate('/stock')}
                className="text-[11px] text-muted-foreground/40 hover:text-accent flex items-center gap-1 transition-colors duration-300 group"
              >
                View all <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform duration-200" />
              </button>
            </div>
            <div className="rounded-2xl border border-white/[0.04] bg-white/[0.01] overflow-hidden divide-y divide-white/[0.03]">
              {TRENDING.map((p, i) => (
                <motion.div
                  key={p.name}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 + i * 0.06, ease: [0.22, 1, 0.36, 1] }}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-white/[0.015] transition-colors duration-300 cursor-pointer group"
                  onClick={() => navigate('/stock')}
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="h-8 w-8 rounded-lg bg-white/[0.03] flex items-center justify-center shrink-0 group-hover:bg-white/[0.05] transition-colors duration-300">
                      <CreditCard className="h-3.5 w-3.5 text-muted-foreground/30" />
                    </div>
                    <span className="text-[13px] font-medium truncate text-foreground/80">{p.name}</span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0 ml-4">
                    <span className="text-[13px] font-mono-numbers font-semibold text-foreground/70">{p.price}</span>
                    <span className={`text-[11px] font-mono-numbers font-semibold w-10 text-right ${p.up ? 'text-emerald-400/80' : 'text-rose-400/80'}`}>
                      {p.change}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Activity Feed */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-[13px] font-semibold tracking-[-0.01em] text-foreground/80">Live Feed</h2>
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-1.5 w-1.5">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-rose-400'} opacity-50`} />
                  <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${isConnected ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                </span>
                <span className={`text-[10px] font-medium ${isConnected ? 'text-emerald-400/60' : 'text-rose-400/60'}`}>
                  {isConnected ? 'Real-time' : 'Offline'}
                </span>
              </div>
            </div>
            <div className="rounded-2xl border border-white/[0.04] bg-white/[0.01] overflow-hidden divide-y divide-white/[0.03]">
              {FEED.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + i * 0.07, ease: [0.22, 1, 0.36, 1] }}
                  className="flex items-start gap-3 px-4 py-3.5 hover:bg-white/[0.015] transition-colors duration-300"
                >
                  <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${item.color} opacity-60`} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[12px] text-foreground/70 leading-relaxed">{item.text}</p>
                    <p className="text-[10px] text-muted-foreground/40 mt-0.5">{item.time} ago</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  )
}
