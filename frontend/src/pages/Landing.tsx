/**
 * Landing page for PokeAgent — public-facing marketing page.
 * Shows features, stats, and a CTA to connect wallet.
 */
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Zap, Eye, Bot, TrendingUp,
  Search, Bell, Calculator, Sparkles, ArrowRight,
  Globe, Database, BarChart3,
} from 'lucide-react'

const FEATURES = [
  {
    icon: Search,
    title: 'Real-Time Stock Finder',
    description: 'Scan Target, Walmart, Best Buy, GameStop, and more. Get alerts the second products drop.',
    color: 'text-blue-400',
    bg: 'from-blue-500/20 to-blue-600/5',
    glow: 'group-hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]',
  },
  {
    icon: TrendingUp,
    title: 'Price Intelligence',
    description: 'Live TCGPlayer market data, price history charts, and trend analysis across 3,000+ cards.',
    color: 'text-red-400',
    bg: 'from-red-500/20 to-red-600/5',
    glow: 'group-hover:shadow-[0_0_30px_rgba(52,211,153,0.15)]',
  },
  {
    icon: Bot,
    title: 'AI-Powered Agents',
    description: 'Autonomous agents scan, analyze, and alert you to deals. Configurable auto-buy with budget controls.',
    color: 'text-purple-400',
    bg: 'from-purple-500/20 to-purple-600/5',
    glow: 'group-hover:shadow-[0_0_30px_rgba(168,85,247,0.15)]',
  },
  {
    icon: Calculator,
    title: 'Flip Calculator',
    description: 'Grade-or-sell-raw analysis with PSA, CGC, BGS cost modeling. Know your ROI before you submit.',
    color: 'text-amber-400',
    bg: 'from-amber-500/20 to-amber-600/5',
    glow: 'group-hover:shadow-[0_0_30px_rgba(251,191,36,0.15)]',
  },
  {
    icon: Sparkles,
    title: 'AI Card Grading',
    description: 'Upload photos for instant grade estimates. Centering, corners, surface, and edge analysis.',
    color: 'text-pink-400',
    bg: 'from-pink-500/20 to-pink-600/5',
    glow: 'group-hover:shadow-[0_0_30px_rgba(236,72,153,0.15)]',
  },
  {
    icon: Bell,
    title: 'Smart Alerts',
    description: 'Price drop notifications, restock alerts, and deal triggers delivered to Discord in real time.',
    color: 'text-cyan-400',
    bg: 'from-cyan-500/20 to-cyan-600/5',
    glow: 'group-hover:shadow-[0_0_30px_rgba(34,211,238,0.15)]',
  },
]

const STATS = [
  { label: 'Cards Tracked', value: '2,414', icon: Database },
  { label: 'Sets Indexed', value: '171', icon: Globe },
  { label: 'Card Analytics', value: '130,170+', icon: BarChart3 },
  { label: 'Retailers Monitored', value: '7', icon: Eye },
]


export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background text-foreground relative overflow-hidden">
      {/* Background effects */}
      <div className="particles-bg" aria-hidden="true" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-red-500/[0.05] via-transparent to-transparent" />
      {/* Extra ambient orbs */}
      <div className="absolute top-[20%] left-[60%] w-[500px] h-[500px] rounded-full bg-red-500/[0.03] blur-[120px] pointer-events-none" />
      <div className="absolute top-[60%] left-[20%] w-[400px] h-[400px] rounded-full bg-blue-500/[0.03] blur-[100px] pointer-events-none" />

      {/* ── Hero ── */}
      <section className="relative pt-20 pb-28 px-5 sm:px-8">
        <div className="max-w-5xl mx-auto text-center">
          {/* Logo + Title */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            {/* Large pokeball — outline style, red top / white bottom */}
            <div className="flex justify-center mb-8">
              <motion.div
                className="relative"
                animate={{ y: [0, -6, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
              >
                {/* Outer glow rings */}
                <div className="absolute inset-[-16px] rounded-full bg-red-500/10 blur-2xl pointer-events-none" />
                <div className="absolute inset-[-32px] rounded-full bg-red-500/5 blur-3xl pointer-events-none" />
                {/* Pokeball SVG — outline strokes */}
                <svg
                  viewBox="0 0 100 100"
                  className="w-28 h-28 sm:w-32 sm:h-32 drop-shadow-[0_0_40px_rgba(239,68,68,0.2)]"
                >
                  {/* Top half arc — red outline */}
                  <path
                    d="M 4 50 A 46 46 0 0 1 96 50"
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="3.5"
                    strokeLinecap="round"
                  />
                  {/* Bottom half arc — white outline */}
                  <path
                    d="M 96 50 A 46 46 0 0 1 4 50"
                    fill="none"
                    stroke="rgba(255,255,255,0.9)"
                    strokeWidth="3.5"
                    strokeLinecap="round"
                  />
                  {/* Center line */}
                  <line
                    x1="4"
                    y1="50"
                    x2="96"
                    y2="50"
                    stroke="#52525b"
                    strokeWidth="3.5"
                  />
                  {/* Center circle outer ring */}
                  <circle
                    cx="50"
                    cy="50"
                    r="14"
                    fill="none"
                    stroke="#52525b"
                    strokeWidth="3.5"
                  />
                  {/* Center circle inner — white with glow */}
                  <circle
                    cx="50"
                    cy="50"
                    r="7"
                    fill="white"
                    filter="drop-shadow(0 0 6px rgba(255,255,255,0.4))"
                  />
                </svg>
              </motion.div>
            </div>

            <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight mb-5">
              Poke<span className="text-red-500 drop-shadow-[0_0_20px_rgba(239,68,68,0.4)]">Agent</span>
            </h1>
            <p className="text-lg sm:text-xl text-muted-foreground/70 max-w-2xl mx-auto leading-relaxed">
              The ultimate Pokemon TCG intelligence platform.
              Real-time stock tracking, AI-powered price analysis,
              and autonomous deal-finding agents.
            </p>
          </motion.div>

          {/* Online badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.35 }}
            className="flex justify-center mt-8"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-medium">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
              </span>
              Systems Online
            </div>
          </motion.div>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-6"
          >
            <motion.button
              onClick={() => navigate('/dashboard')}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              className="flex items-center gap-2.5 h-14 px-10 rounded-2xl text-base font-semibold bg-red-500 text-white hover:bg-red-400 shadow-xl shadow-red-500/25 hover:shadow-red-500/40 transition-all duration-300"
            >
              <Zap className="w-5 h-5" />
              Launch App
              <ArrowRight className="w-4 h-4" />
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <section className="relative py-10 border-y border-white/[0.06] bg-surface/30 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-5 sm:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {STATS.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.1 }}
                className="flex items-center gap-3"
              >
                <div className="w-11 h-11 rounded-xl bg-red-500/10 border border-red-500/10 flex items-center justify-center shrink-0">
                  <stat.icon className="w-5 h-5 text-red-400" />
                </div>
                <div>
                  <p className="text-xl font-bold text-foreground font-mono">{stat.value}</p>
                  <p className="text-xs text-muted-foreground/60">{stat.label}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="relative py-24 px-5 sm:px-8">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <p className="text-xs font-medium tracking-[0.2em] uppercase text-red-400 mb-3">
              Platform Features
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold">
              Everything you need to dominate the TCG market
            </h2>
          </motion.div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className={`group relative bg-surface/50 backdrop-blur-sm border border-white/[0.06] rounded-2xl p-6 hover:border-white/[0.12] transition-all duration-500 hover:translate-y-[-4px] ${feature.glow}`}
              >
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.bg} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
                {/* Holo shine on hover */}
                <div className="absolute inset-0 rounded-2xl overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.03] to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                </div>
                <div className="relative">
                  <div className="w-11 h-11 rounded-xl bg-white/[0.06] border border-white/[0.04] flex items-center justify-center mb-4">
                    <feature.icon className={`w-5 h-5 ${feature.color}`} />
                  </div>
                  <h3 className="text-base font-semibold mb-2">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground/70 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer CTA ── */}
      <section className="relative py-20 px-5 sm:px-8 border-t border-white/[0.06]">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to level up?</h2>
          <p className="text-sm text-muted-foreground/60 mb-10 max-w-md mx-auto">
            Real-time stock tracking, price intelligence, and AI agents — all in one platform.
          </p>
          <motion.button
            onClick={() => navigate('/dashboard')}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="inline-flex items-center gap-2 h-13 px-10 rounded-2xl text-sm font-semibold bg-red-500 text-white hover:bg-red-400 shadow-xl shadow-red-500/25 hover:shadow-red-500/40 transition-all duration-300"
          >
            <Zap className="w-4 h-4" />
            Launch App
          </motion.button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-8 px-5 sm:px-8 border-t border-white/[0.06]">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold">Poke<span className="text-red-500">Agent</span></span>
            <span className="text-xs text-muted-foreground/40">TCG Intelligence</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="https://drip.trade/collections/locals-only" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground/50 hover:text-foreground transition-colors">
              Locals Only
            </a>
            <a href="https://x.com/demi_hl" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground/50 hover:text-foreground transition-colors">
              Twitter
            </a>
            <a href="https://discord.gg/a56Tjc7BEr" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground/50 hover:text-foreground transition-colors">
              Discord
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
