export interface PortfolioItem {
  id: string
  name: string
  gradeType: string
  cardType: string
  costPaid: number
  currentPrice: number
  quantity: number
  addedAt: string
  image?: string
}

export interface PortfolioStats {
  totalValue: number
  totalCost: number
  gainLoss: number
  roi: number
  itemCount: number
}

export interface Purchase {
  id: string
  product: string
  retailer: string
  price: number
  quantity: number
  date: string
}
