import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Search,
  CreditCard,
  Flame,
  MoreHorizontal,
  X,
  Database,
  Bell,
  Calculator,
  Sparkles,
  MessageSquare,
  PieChart,
  BarChart3,
  MapPin,
  Settings,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { NAV_ITEMS } from '@/lib/constants'
import type { LucideIcon } from 'lucide-react'

const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard,
  Search,
  CreditCard,
  Database,
  Flame,
  Bell,
  Calculator,
  Sparkles,
  MessageSquare,
  PieChart,
  BarChart3,
  MapPin,
  Settings,
}

const PRIMARY_ITEMS = [
  { path: '/', label: 'Dashboard', icon: 'LayoutDashboard' },
  { path: '/stock', label: 'Stock', icon: 'Search' },
  { path: '/cards', label: 'Cards', icon: 'CreditCard' },
  { path: '/drops', label: 'Drops', icon: 'Flame' },
] as const

const REMAINING_ITEMS = NAV_ITEMS.filter(
  (item) => !PRIMARY_ITEMS.some((p) => p.path === item.path)
)

export default function MobileNav() {
  const [moreOpen, setMoreOpen] = useState(false)

  return (
    <>
      {/* Slide-up panel overlay */}
      <AnimatePresence>
        {moreOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/60 md:hidden"
              onClick={() => setMoreOpen(false)}
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed bottom-0 left-0 right-0 z-50 bg-surface border-t border-border rounded-t-2xl pb-20 md:hidden"
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="text-sm font-semibold text-foreground">
                  More
                </span>
                <button
                  onClick={() => setMoreOpen(false)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg text-muted hover:text-foreground hover:bg-surface-hover transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <nav className="grid grid-cols-3 gap-1 p-3">
                {REMAINING_ITEMS.map((item) => {
                  const Icon = iconMap[item.icon]
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => setMoreOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          'flex flex-col items-center gap-1 rounded-xl py-3 px-2 text-xs font-medium transition-colors',
                          isActive
                            ? 'text-accent bg-accent-muted'
                            : 'text-muted hover:text-foreground hover:bg-surface-hover'
                        )
                      }
                    >
                      {Icon && <Icon className="h-5 w-5" />}
                      <span className="truncate">{item.label}</span>
                    </NavLink>
                  )
                })}
              </nav>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Bottom tab bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 h-16 bg-surface/80 backdrop-blur-md border-t border-border flex items-center justify-around px-2 md:hidden">
        {PRIMARY_ITEMS.map((item) => {
          const Icon = iconMap[item.icon]
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                cn(
                  'flex flex-col items-center gap-0.5 py-1 px-3 rounded-lg text-[11px] font-medium transition-colors',
                  isActive ? 'text-accent' : 'text-muted'
                )
              }
            >
              {Icon && <Icon className="h-5 w-5" />}
              <span>{item.label}</span>
            </NavLink>
          )
        })}
        <button
          onClick={() => setMoreOpen(true)}
          className={cn(
            'flex flex-col items-center gap-0.5 py-1 px-3 rounded-lg text-[11px] font-medium transition-colors',
            moreOpen ? 'text-accent' : 'text-muted'
          )}
        >
          <MoreHorizontal className="h-5 w-5" />
          <span>More</span>
        </button>
      </nav>
    </>
  )
}
