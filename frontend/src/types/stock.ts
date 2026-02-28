export interface StoreResult {
  store: string
  retailer: string
  address?: string
  city?: string
  state?: string
  zip?: string
  distance?: number
  products: StoreProduct[]
  inStock: boolean
  lastChecked?: string
  url?: string
}

export interface StoreProduct {
  name: string
  sku?: string
  upc?: string
  price?: number
  quantity?: number
  inStock: boolean
  url?: string
  image?: string
}

export interface StockStats {
  stores: number
  inStock: number
  products: number
  totalUnits: number
}

export interface SealedProduct {
  name: string
  type: string
  msrp: number
  set?: string
  image?: string
  upc?: string
  skus?: Record<string, string>
}
