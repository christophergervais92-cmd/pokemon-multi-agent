import { useLocation, useNavigate } from 'react-router-dom'
import { Sun, Moon, Bell, Search, User, LogIn } from 'lucide-react'
import { cn } from '@/lib/utils'
import { NAV_ITEMS } from '@/lib/constants'
import { useAuthStore } from '@/store/authStore'
import { useUIStore } from '@/store/uiStore'
import { useTheme } from '@/hooks/useTheme'
import { useState, useRef, useEffect } from 'react'

export default function TopBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuthStore()
  const { sidebarCollapsed } = useUIStore()
  const { isDark, toggleTheme } = useTheme()
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchValue, setSearchValue] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)

  const currentPage = NAV_ITEMS.find((item) => {
    if (item.path === '/') return location.pathname === '/'
    return location.pathname.startsWith(item.path)
  })

  const leftOffset = sidebarCollapsed ? 'md:left-[72px]' : 'md:left-[280px]'

  useEffect(() => {
    if (searchOpen && searchRef.current) {
      searchRef.current.focus()
    }
  }, [searchOpen])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchValue.trim()) {
      navigate(`/cards?q=${encodeURIComponent(searchValue.trim())}`)
      setSearchValue('')
      setSearchOpen(false)
    }
  }

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-30 h-16 flex items-center justify-between gap-4 px-4 md:px-6',
        'bg-surface/80 backdrop-blur-md border-b border-border transition-all duration-300',
        leftOffset
      )}
    >
      {/* Left: Breadcrumb */}
      <div className="flex items-center gap-2 text-sm min-w-0">
        <span className="text-muted hidden sm:inline">PokeAgent</span>
        <span className="text-muted hidden sm:inline">/</span>
        <span className="font-medium text-foreground truncate">
          {currentPage?.label ?? 'Page'}
        </span>
      </div>

      {/* Center: Global search */}
      <form
        onSubmit={handleSearchSubmit}
        className="hidden md:flex items-center flex-1 max-w-md mx-4"
      >
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
          <input
            ref={searchRef}
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="Search cards, sets, products..."
            className={cn(
              'w-full h-9 pl-9 pr-4 rounded-lg text-sm',
              'bg-surface border border-border text-foreground placeholder:text-muted',
              'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
              'transition-colors'
            )}
          />
        </div>
      </form>

      {/* Right: Actions */}
      <div className="flex items-center gap-1">
        {/* Mobile search toggle */}
        <button
          onClick={() => setSearchOpen(!searchOpen)}
          className="md:hidden flex items-center justify-center h-9 w-9 rounded-lg text-muted hover:text-foreground hover:bg-surface-hover transition-colors"
        >
          <Search className="h-4 w-4" />
        </button>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="flex items-center justify-center h-9 w-9 rounded-lg text-muted hover:text-foreground hover:bg-surface-hover transition-colors"
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* Notifications */}
        <button
          className="relative flex items-center justify-center h-9 w-9 rounded-lg text-muted hover:text-foreground hover:bg-surface-hover transition-colors"
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
          {/* Badge — hidden by default, can be made visible with state */}
        </button>

        {/* User / Login */}
        {isAuthenticated && user ? (
          <button
            className="flex items-center gap-2 h-9 rounded-lg px-2 text-sm text-muted hover:text-foreground hover:bg-surface-hover transition-colors"
            title={user.username}
          >
            {user.avatar ? (
              <img
                src={user.avatar}
                alt={user.username}
                className="h-6 w-6 rounded-full object-cover"
              />
            ) : (
              <User className="h-4 w-4" />
            )}
            <span className="hidden lg:inline truncate max-w-[100px]">
              {user.username}
            </span>
          </button>
        ) : (
          <button
            className="flex items-center gap-2 h-9 rounded-lg px-3 text-sm bg-accent text-accent-foreground hover:bg-accent/90 transition-colors"
            title="Login"
          >
            <LogIn className="h-4 w-4" />
            <span className="hidden sm:inline">Login</span>
          </button>
        )}
      </div>

      {/* Mobile search bar (expanded) */}
      {searchOpen && (
        <form
          onSubmit={handleSearchSubmit}
          className="absolute left-0 right-0 top-full md:hidden px-4 py-2 bg-surface border-b border-border"
        >
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
            <input
              type="text"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="Search cards, sets, products..."
              autoFocus
              className={cn(
                'w-full h-9 pl-9 pr-4 rounded-lg text-sm',
                'bg-surface border border-border text-foreground placeholder:text-muted',
                'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
              )}
            />
          </div>
        </form>
      )}
    </header>
  )
}
