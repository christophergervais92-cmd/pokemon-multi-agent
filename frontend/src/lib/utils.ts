import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '??'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num) || num === 0) return '??'
  if (num >= 1000) return num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  if (num >= 100) return num.toFixed(0)
  return num.toFixed(2)
}

export function formatPriceWithSign(value: number): string {
  const formatted = formatPrice(Math.abs(value))
  if (value > 0) return `+$${formatted}`
  if (value < 0) return `-$${formatted}`
  return `$${formatted}`
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toString()
}

export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  return formatDate(d)
}

export function debounce<T extends (...args: unknown[]) => unknown>(fn: T, ms: number) {
  let timer: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), ms)
  }
}

export function getRetailerColor(retailer: string): string {
  const r = retailer.toLowerCase()
  if (r.includes('target')) return 'text-[#cc0000]'
  if (r.includes('walmart')) return 'text-[#0071dc]'
  if (r.includes('best buy') || r.includes('bestbuy')) return 'text-[#0046be]'
  if (r.includes('gamestop')) return 'text-[#e21e26]'
  if (r.includes('pokemon center') || r.includes('pokecenter')) return 'text-[#ffcb05]'
  if (r.includes('amazon')) return 'text-[#ff9900]'
  if (r.includes('costco')) return 'text-[#e31837]'
  if (r.includes('tcgplayer')) return 'text-[#0f7ff4]'
  return 'text-muted'
}

export function getRetailerBgColor(retailer: string): string {
  const r = retailer.toLowerCase()
  if (r.includes('target')) return 'bg-[#cc000020]'
  if (r.includes('walmart')) return 'bg-[#0071dc20]'
  if (r.includes('best buy') || r.includes('bestbuy')) return 'bg-[#0046be20]'
  if (r.includes('gamestop')) return 'bg-[#e21e2620]'
  if (r.includes('pokemon center') || r.includes('pokecenter')) return 'bg-[#ffcb0520]'
  if (r.includes('amazon')) return 'bg-[#ff990020]'
  if (r.includes('costco')) return 'bg-[#e3183720]'
  if (r.includes('tcgplayer')) return 'bg-[#0f7ff420]'
  return 'bg-surface'
}
