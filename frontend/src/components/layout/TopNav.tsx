import { useState, useRef, useEffect } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sun, Moon, Bell, Search, User, LogIn, Wifi, WifiOff,
  LayoutDashboard, CreditCard, Database, Flame, Calculator,
  Sparkles, MessageSquare, PieChart, BarChart3, MapPin, Settings,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import { useTheme } from '@/hooks/useTheme'
import { useHealth } from '@/hooks/useApi'
import type { LucideIcon } from 'lucide-react'

const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard, Search, CreditCard, Database, Flame, Bell,
  Calculator, Sparkles, MessageSquare, PieChart, BarChart3, MapPin, Settings,
}

const TABS = [
  { path: '/', label: 'Dashboard', icon: 'LayoutDashboard' },
  { path: '/drops', label: 'Drops', icon: 'Flame' },
  { path: '/stock', label: 'Stock', icon: 'Search' },
  { path: '/monitors', label: 'Monitors', icon: 'Bell' },
  { path: '/database', label: 'Database', icon: 'Database' },
  { path: '/cards', label: 'Cards', icon: 'CreditCard' },
  { path: '/flip', label: 'Flip Calc', icon: 'Calculator' },
  { path: '/grading', label: 'Grading', icon: 'Sparkles' },
  { path: '/assistant', label: 'AI Chat', icon: 'MessageSquare' },
  { path: '/portfolio', label: 'Portfolio', icon: 'PieChart' },
  { path: '/analytics', label: 'Analytics', icon: 'BarChart3' },
  { path: '/settings', label: 'Settings', icon: 'Settings' },
] as const

export default function TopNav() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuthStore()
  const { isDark, toggleTheme } = useTheme()
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchValue, setSearchValue] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)
  const tabsRef = useRef<HTMLDivElement>(null)

  // Wire health check to real API
  const { data: healthData, isError: healthError } = useHealth()
  const isConnected = !healthError && (healthData?.status === 'ok' || healthData?.status === 'healthy')

  useEffect(() => {
    if (searchOpen && searchRef.current) searchRef.current.focus()
  }, [searchOpen])

  // Auto-scroll active tab into view
  useEffect(() => {
    if (!tabsRef.current) return
    const active = tabsRef.current.querySelector('[data-active="true"]')
    if (active) {
      active.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
    }
  }, [location.pathname])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchValue.trim()) {
      navigate(`/cards?q=${encodeURIComponent(searchValue.trim())}`)
      setSearchValue('')
      setSearchOpen(false)
    }
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50">
      {/* ── Main header bar ── */}
      <div className="relative">
        {/* Subtle top gradient line */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-accent/30 to-transparent" />

        <div className="h-14 bg-background/70 backdrop-blur-2xl border-b border-white/[0.06]">
          <div className="max-w-[1440px] mx-auto h-full flex items-center justify-between px-5 sm:px-8">

            {/* ── Brand ── */}
            <motion.button
              onClick={() => navigate('/')}
              className="flex items-center gap-3 group"
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              {/* Pokeball icon */}
              <div className="relative">
                <div className="w-8 h-8 rounded-full border-2 border-accent/60 group-hover:border-accent transition-colors duration-300 flex items-center justify-center overflow-hidden">
                  <div className="absolute top-0 left-0 right-0 h-1/2 bg-accent/10" />
                  <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-transparent" />
                  <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-[2px] bg-accent/30" />
                  <div className="relative w-2.5 h-2.5 rounded-full border-2 border-accent/60 bg-background group-hover:bg-accent/20 transition-colors duration-300" />
                </div>
                {/* Ambient glow */}
                <div className="absolute -inset-1 rounded-full bg-accent/10 blur-md opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              </div>
              <div className="hidden sm:flex flex-col">
                <span className="text-sm font-bold tracking-tight text-foreground leading-none">
                  Poke<span className="text-accent">Agent</span>
                </span>
                <span className="text-[9px] font-medium tracking-[0.2em] uppercase text-muted-foreground/50 leading-none mt-0.5">
                  TCG Intelligence
                </span>
              </div>
            </motion.button>

            {/* ── Center search ── */}
            <form onSubmit={handleSearchSubmit} className="hidden md:flex flex-1 max-w-md mx-10">
              <div className="relative w-full group">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-accent/70 transition-colors duration-300" />
                <input
                  ref={searchRef}
                  type="text"
                  value={searchValue}
                  onChange={(e) => setSearchValue(e.target.value)}
                  placeholder="Search cards, sets, products..."
                  className="w-full h-9 pl-10 pr-12 rounded-xl text-[13px] bg-white/[0.03] border border-white/[0.06] text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-accent/30 focus:bg-white/[0.05] focus:shadow-[0_0_20px_rgba(96,165,250,0.06)] transition-all duration-300"
                />
                <div className="hidden lg:flex absolute right-3 top-1/2 -translate-y-1/2 items-center">
                  <kbd className="text-[10px] text-muted-foreground/30 font-mono px-1.5 py-0.5 rounded-md bg-white/[0.03] border border-white/[0.06]">
                    ⌘K
                  </kbd>
                </div>
              </div>
            </form>

            {/* ── Right actions ── */}
            <div className="flex items-center gap-1">
              {/* Connection status — wired to real /api/health */}
              <div className={cn(
                'hidden sm:flex items-center gap-1.5 mr-2 px-2.5 py-1 rounded-lg border',
                isConnected
                  ? 'bg-emerald-500/[0.08] border-emerald-500/[0.12]'
                  : 'bg-rose-500/[0.08] border-rose-500/[0.12]'
              )}>
                <span className="relative flex h-1.5 w-1.5">
                  <span className={cn(
                    'animate-ping absolute inline-flex h-full w-full rounded-full opacity-60',
                    isConnected ? 'bg-emerald-400' : 'bg-rose-400'
                  )} />
                  <span className={cn(
                    'relative inline-flex rounded-full h-1.5 w-1.5',
                    isConnected ? 'bg-emerald-400' : 'bg-rose-400'
                  )} />
                </span>
                <span className={cn(
                  'text-[10px] font-medium',
                  isConnected ? 'text-emerald-400/80' : 'text-rose-400/80'
                )}>
                  {isConnected ? 'Live' : 'Offline'}
                </span>
              </div>

              {/* Mobile search */}
              <button
                onClick={() => setSearchOpen(!searchOpen)}
                className="md:hidden h-9 w-9 flex items-center justify-center rounded-xl text-muted-foreground/60 hover:text-foreground hover:bg-white/[0.04] transition-all duration-200"
              >
                <Search className="h-4 w-4" />
              </button>

              {/* Theme toggle */}
              <motion.button
                onClick={toggleTheme}
                whileTap={{ scale: 0.9, rotate: 180 }}
                transition={{ duration: 0.3 }}
                className="h-9 w-9 flex items-center justify-center rounded-xl text-muted-foreground/60 hover:text-foreground hover:bg-white/[0.04] transition-all duration-200"
              >
                {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </motion.button>

              {/* Notifications */}
              <button className="relative h-9 w-9 flex items-center justify-center rounded-xl text-muted-foreground/60 hover:text-foreground hover:bg-white/[0.04] transition-all duration-200">
                <Bell className="h-4 w-4" />
                <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
                </span>
              </button>

              {/* User */}
              {isAuthenticated && user ? (
                <button className="h-9 flex items-center gap-2 rounded-xl px-2 text-muted-foreground/60 hover:text-foreground hover:bg-white/[0.04] transition-all duration-200">
                  {user.avatar ? (
                    <img src={user.avatar} alt="" className="h-6 w-6 rounded-full ring-1 ring-white/10" />
                  ) : (
                    <div className="h-6 w-6 rounded-full bg-gradient-to-br from-accent/30 to-accent/10 flex items-center justify-center text-[10px] font-bold text-accent ring-1 ring-accent/20">
                      {user.username?.[0]?.toUpperCase()}
                    </div>
                  )}
                </button>
              ) : (
                <motion.button
                  onClick={() => navigate('/login')}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="h-8 flex items-center gap-1.5 rounded-lg px-3 text-[11px] font-semibold bg-accent/90 text-white hover:bg-accent shadow-[0_0_20px_rgba(96,165,250,0.15)] hover:shadow-[0_0_25px_rgba(96,165,250,0.25)] transition-all duration-300"
                >
                  <LogIn className="h-3 w-3" />
                  <span className="hidden sm:inline">Sign in</span>
                </motion.button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Tab navigation ── */}
      <div className="hidden md:block bg-background/50 backdrop-blur-xl border-b border-white/[0.04]">
        <div className="max-w-[1440px] mx-auto px-5 sm:px-8">
          <div
            ref={tabsRef}
            className="flex items-center gap-0.5 overflow-x-auto scrollbar-none -mb-px"
          >
            {TABS.map((tab) => {
              const Icon = iconMap[tab.icon]
              const isActive = tab.path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(tab.path)
              return (
                <NavLink
                  key={tab.path}
                  to={tab.path}
                  end={tab.path === '/'}
                  data-active={isActive}
                  className="relative shrink-0 group"
                >
                  <div className={cn(
                    'flex items-center gap-1.5 px-3 py-2.5 text-[11px] font-medium tracking-wide transition-all duration-300',
                    isActive
                      ? 'text-accent'
                      : 'text-muted-foreground/50 hover:text-foreground/80'
                  )}>
                    {Icon && (
                      <Icon className={cn(
                        'h-3 w-3 transition-all duration-300',
                        isActive ? 'text-accent' : 'text-muted-foreground/40 group-hover:text-foreground/60'
                      )} />
                    )}
                    <span>{tab.label}</span>
                  </div>

                  {/* Active indicator — gradient glow line */}
                  {isActive && (
                    <motion.div
                      layoutId="nav-tab-glow"
                      className="absolute bottom-0 left-1 right-1"
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    >
                      <div className="h-[2px] rounded-full bg-gradient-to-r from-accent/60 via-accent to-accent/60" />
                      <div className="h-[6px] -mt-[2px] rounded-full bg-accent/20 blur-sm" />
                    </motion.div>
                  )}
                </NavLink>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Mobile search expansion ── */}
      <AnimatePresence>
        {searchOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="md:hidden bg-background/90 backdrop-blur-xl border-b border-white/[0.04] overflow-hidden"
          >
            <form onSubmit={handleSearchSubmit} className="px-4 py-3">
              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
                <input
                  type="text"
                  value={searchValue}
                  onChange={(e) => setSearchValue(e.target.value)}
                  placeholder="Search cards, sets, products..."
                  autoFocus
                  className="w-full h-11 pl-10 pr-4 rounded-xl text-sm bg-white/[0.04] border border-white/[0.06] text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-accent/30 transition-all duration-300"
                />
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
