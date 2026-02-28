export interface Drop {
  id: string
  name: string
  date: string
  type: 'confirmed' | 'rumor'
  retailers?: string[]
  products?: string[]
  setId?: string
  source?: string
  boxColor?: string
  image?: string
  description?: string
}

export interface IntelItem {
  id: string
  source: string
  platform: 'reddit' | 'pokebeach' | 'twitter' | 'instagram' | 'tiktok' | 'other'
  content: string
  timestamp: string
  url?: string
  image?: string
  verified: boolean
}
