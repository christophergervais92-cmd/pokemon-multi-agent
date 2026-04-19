import { useState, useRef, useEffect } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  Search, Bell, Command, Activity, Flame, LineChart, Archive, Wallet,
  Sparkles, MessageSquare, Package, MapPin, Settings, SlidersHorizontal,
  Calculator, BarChart3,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useHealth } from '@/hooks/useApi'
import Ticker from '@/components/shared/Ticker'

const PRIMARY = [
  { path: '/dashboard', label: 'Terminal', icon: Activity },
  { path: '/cards',     label: 'Track',    icon: LineChart },
  { path: '/sealed',    label: 'Sealed',   icon: Archive },
  { path: '/portfolio', label: 'Portfolio',icon: Wallet },
  { path: '/drops',     label: 'Drops',    icon: Flame },
  { path: '/monitors',  label: 'Monitors', icon: Bell },
] as const

const SECONDARY = [
  { path: '/database',  label: 'Database',  icon: Package },
  { path: '/stock',     label: 'Stock',     icon: Search },
  { path: '/flip',      label: 'Flip',      icon: Calculator },
  { path: '/pack-ev',   label: 'Pack EV',   icon: SlidersHorizontal },
  { path: '/grading',   label: 'Grading',   icon: Sparkles },
  { path: '/assistant', label: 'Assistant', icon: MessageSquare },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/vending',   label: 'Vending',   icon: MapPin },
  { path: '/settings',  label: 'Settings',  icon: Settings },
] as const

export default function TopNav() {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchValue, setSearchValue] = useState('')
  const [moreOpen, setMoreOpen] = useState(false)
  const moreRef = useRef<HTMLDivElement>(null)

  const { data: healthData, isError: healthError } = useHealth()
  const isConnected = !healthError && (healthData?.status === 'ok' || healthData?.status === 'healthy')

  // Close "More" dropdown on route change or outside click
  useEffect(() => { setMoreOpen(false) }, [location.pathname])
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false)
    }
    if (moreOpen) document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [moreOpen])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = searchValue.trim()
    if (q) {
      navigate(`/cards?q=${encodeURIComponent(q)}`)
      setSearchValue('')
    }
  }

  const sessionTime = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  })

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/85 backdrop-blur-xl border-b border-border">
      {/* ── Ticker row ── */}
      <Ticker />

      {/* ── Main bar ── */}
      <div className="h-14 flex items-center px-4 sm:px-6 gap-6 border-b border-border">
        {/* Brand */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-3 group shrink-0"
        >
          {/* Minimal pokeball glyph */}
          <div className="relative w-7 h-7">
            <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" stroke="var(--color-accent)" />
              <line x1="2" y1="12" x2="22" y2="12" stroke="var(--color-foreground-dim)" />
              <circle cx="12" cy="12" r="3" stroke="var(--color-foreground-dim)" fill="var(--color-background)" />
            </svg>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-display italic text-[22px] leading-none text-foreground">
              pokeagent
            </span>
            <span className="hidden sm:inline text-[9px] font-mono tracking-[0.25em] uppercase text-muted mt-0.5">
              Terminal
            </span>
          </div>
        </button>

        {/* Primary nav tabs */}
        <nav className="hidden lg:flex items-center h-full gap-0.5 -mx-1">
          {PRIMARY.map((tab) => {
            const Icon = tab.icon
            const isActive = location.pathname === tab.path ||
              (tab.path !== '/dashboard' && location.pathname.startsWith(tab.path))
            return (
              <NavLink
                key={tab.path}
                to={tab.path}
                className={cn(
                  'h-full flex items-center gap-1.5 px-2.5 text-[12px] font-medium tracking-wide transition-colors relative',
                  isActive
                    ? 'text-foreground'
                    : 'text-muted hover:text-foreground-dim'
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
                {isActive && (
                  <span className="absolute bottom-0 left-2 right-2 h-px bg-accent" />
                )}
              </NavLink>
            )
          })}

          {/* More menu */}
          <div ref={moreRef} className="relative h-full">
            <button
              onClick={() => setMoreOpen(!moreOpen)}
              className={cn(
                'h-full flex items-center gap-1.5 px-2.5 text-[12px] font-medium tracking-wide transition-colors',
                moreOpen ? 'text-foreground' : 'text-muted hover:text-foreground-dim'
              )}
            >
              More
              <span className="text-[9px]">▾</span>
            </button>
            {moreOpen && (
              <div className="absolute top-full left-0 mt-1 w-52 panel-2 py-1.5 shadow-lg">
                {SECONDARY.map((item) => {
                  const Icon = item.icon
                  const isActive = location.pathname === item.path || location.pathname.startsWith(item.path)
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={cn(
                        'flex items-center gap-2.5 px-3 py-1.5 text-[12px] transition-colors',
                        isActive ? 'text-accent bg-accent-muted' : 'text-foreground-dim hover:bg-surface-hover'
                      )}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {item.label}
                    </NavLink>
                  )
                })}
              </div>
            )}
          </div>
        </nav>

        <div className="flex-1" />

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="hidden md:block w-[320px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted" />
            <input
              type="text"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="Search cards · set · number…"
              className="input pl-9 pr-12 h-9 text-[13px]"
            />
            <kbd className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center gap-0.5 px-1.5 h-5 rounded text-[10px] text-muted font-mono bg-surface-2 border border-border">
              <Command className="w-2.5 h-2.5" />K
            </kbd>
          </div>
        </form>

        {/* Status + session time */}
        <div className="hidden xl:flex items-center gap-4 text-[10px] font-mono tracking-wider uppercase text-muted">
          <div className="flex items-center gap-1.5">
            <span className={cn('w-1.5 h-1.5 rounded-full', isConnected ? 'bg-success' : 'bg-danger')} />
            <span>{isConnected ? 'Online' : 'Offline'}</span>
          </div>
          <span className="text-foreground-dim">{sessionTime} UTC</span>
        </div>
      </div>
    </header>
  )
}
