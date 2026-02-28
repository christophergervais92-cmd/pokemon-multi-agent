export interface PokemonCard {
  id: string
  name: string
  supertype?: string
  subtypes?: string[]
  hp?: string
  types?: string[]
  set: {
    id: string
    name: string
    series: string
    printedTotal: number
    total: number
    releaseDate: string
    images: { symbol: string; logo: string }
  }
  number: string
  rarity?: string
  images: { small: string; large: string }
  tcgplayer?: {
    url: string
    prices: Record<string, { low?: number; mid?: number; high?: number; market?: number }>
  }
  cardmarket?: {
    url: string
    prices: { averageSellPrice?: number; trendPrice?: number }
  }
}

export interface CardPrice {
  raw?: number
  psa10?: number
  psa9?: number
  psa8?: number
  cgc10?: number
  bgs10?: number
  market?: number
  low?: number
  high?: number
}

export interface GradedPrice {
  grade: string
  company: string
  price: number
  lastSold?: string
  change?: number
}

export interface PriceHistory {
  date: string
  price: number
  grade?: string
}

export interface CardSet {
  id: string
  name: string
  series: string
  printedTotal: number
  total: number
  releaseDate: string
  images: { symbol: string; logo: string }
}

export interface ChaseCard {
  id: string
  name: string
  rarity: string
  image: string
  price?: number
}

export interface RecentSale {
  date: string
  price: number
  grade?: string
  condition?: string
  platform?: string
}
