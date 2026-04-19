export const RETAILERS = [
  { id: 'all', name: 'All Retailers', color: '#ef4444' },
  { id: 'target', name: 'Target', color: '#cc0000' },
  { id: 'walmart', name: 'Walmart', color: '#0071dc' },
  { id: 'amazon', name: 'Amazon', color: '#ff9900' },
  { id: 'bestbuy', name: 'Best Buy', color: '#0046be' },
  { id: 'gamestop', name: 'GameStop', color: '#e21e26' },
  { id: 'pokecenter', name: 'Pokemon Center', color: '#ffcb05' },
  { id: 'costco', name: 'Costco', color: '#e31837' },
  { id: 'tcgplayer', name: 'TCGPlayer', color: '#0f7ff4' },
] as const

export const GRADE_TYPES = [
  { value: 'raw', label: 'Raw' },
  { value: 'psa10', label: 'PSA 10' },
  { value: 'psa9', label: 'PSA 9' },
  { value: 'psa8', label: 'PSA 8' },
  { value: 'cgc10', label: 'CGC 10' },
  { value: 'bgs10', label: 'BGS 10' },
] as const

export const GRADING_COMPANIES = [
  { value: 'PSA', label: 'PSA', color: '#ef4444' },
  { value: 'CGC', label: 'CGC', color: '#dc2626' },
  { value: 'BGS', label: 'BGS', color: '#a855f7' },
] as const

export const TIME_RANGES = [
  { value: '1M', label: '1M' },
  { value: '3M', label: '3M' },
  { value: '6M', label: '6M' },
  { value: '1Y', label: '1Y' },
  { value: '2Y', label: '2Y' },
] as const

export const CHART_COLORS = {
  line: '#ff6b1a',
  fill: 'rgba(255, 107, 26, 0.10)',
  grid: 'rgba(255,255,255,0.05)',
  text: '#7a7a75',
  tooltip: '#121215',
} as const

/* ── Multi-dataset graded price chart colors ── */
/* Raw = accent; grades = spectrum that reads on the oil-black palette */
export const GRADE_DATASETS = [
  { key: 'raw',    label: 'Raw',              color: '#ff6b1a' },
  { key: 'psa10',  label: 'PSA 10',           color: '#f43f5e' },
  { key: 'psa9',   label: 'PSA 9',            color: '#fb7185' },
  { key: 'psa8',   label: 'PSA 8',            color: '#facc15' },
  { key: 'cgc10',  label: 'CGC 10',           color: '#38bdf8' },
  { key: 'bgs10',  label: 'BGS 10 / Black Label', color: '#a855f7' },
] as const

export const GRADED_CHART_COLORS: Record<string, string> = {
  raw:   '#ff6b1a',
  psa10: '#f43f5e',
  psa9:  '#fb7185',
  psa8:  '#facc15',
  cgc10: '#38bdf8',
  bgs10: '#a855f7',
} as const

/* ── Product MSRP reference ── */
export const PRODUCT_MSRP = {
  pack: 4.49,
  boosterBox: 143.64,
  etb: 49.99,
  boosterBundle: 29.99,
  buildBattle: 14.99,
  blister3: 14.99,
  collectionBox: 24.99,
  ultraPremium: 119.99,
} as const

export const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: 'LayoutDashboard' },
  { path: '/stock', label: 'Stock Finder', icon: 'Search' },
  { path: '/cards', label: 'Card Lookup', icon: 'CreditCard' },
  { path: '/database', label: 'Set Database', icon: 'Database' },
  { path: '/drops', label: 'Drops Intel', icon: 'Flame' },
  { path: '/monitors', label: 'Monitors', icon: 'Bell' },
  { path: '/flip', label: 'Flip Calculator', icon: 'Calculator' },
  { path: '/pack-ev', label: 'Pack EV', icon: 'TrendingUp' },
  { path: '/sealed', label: 'Sealed Tracker', icon: 'Lock' },
  { path: '/grading', label: 'AI Grading', icon: 'Sparkles' },
  { path: '/assistant', label: 'AI Assistant', icon: 'MessageSquare' },
  { path: '/portfolio', label: 'Portfolio', icon: 'PieChart' },
  { path: '/analytics', label: 'Analytics', icon: 'BarChart3' },
  { path: '/vending', label: 'Vending Map', icon: 'MapPin' },
  { path: '/settings', label: 'Settings', icon: 'Settings' },
] as const
