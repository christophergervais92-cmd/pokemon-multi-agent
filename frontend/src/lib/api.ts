/* ═══════════════════════════════════════════════════════
   API Client — connects to Flask backend
   Proxied via Vite dev server (/api → Render)
   ═══════════════════════════════════════════════════════ */

const BASE = import.meta.env.VITE_API_URL || '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${body || res.statusText}`)
  }
  return res.json()
}

/* ── Health ── */
export const api = {
  health: () => request<{ status: string }>('/health'),

  /* ── Sets ── */
  sets: {
    list: (series?: string) =>
      request<{ data: SetItem[] }>(`/sets${series ? `?series=${series}` : ''}`),
    get: (setId: string) =>
      request<SetDetail>(`/sets/${encodeURIComponent(setId)}`),
    pullRates: (setId: string) =>
      request<{ data: PullRate[]; set_id: string }>(`/sets/${encodeURIComponent(setId)}/pull-rates`),
    chaseCards: (setId: string, rarity?: string, limit = 24) => {
      const params = new URLSearchParams()
      if (rarity) params.set('rarity', rarity)
      if (limit !== 24) params.set('limit', String(limit))
      const qs = params.toString()
      return request<{ data: ChaseCard[]; set_id: string }>(
        `/sets/${encodeURIComponent(setId)}/chase-cards${qs ? `?${qs}` : ''}`
      )
    },
  },

  /* ── Cards ── */
  cards: {
    search: (q: string, opts?: { set?: string; rarity?: string; limit?: number }) => {
      const params = new URLSearchParams({ q })
      if (opts?.set) params.set('set', opts.set)
      if (opts?.rarity) params.set('rarity', opts.rarity)
      if (opts?.limit) params.set('limit', String(opts.limit))
      return request<{ data: CardSearchResult[]; query: string; count: number }>(
        `/search/cards?${params}`
      )
    },
    get: (cardId: string) =>
      request<{ card: CardDetail; related: CardSearchResult[] }>(`/cards/${encodeURIComponent(cardId)}`),
    gradedPrices: (cardId: string) =>
      request<GradedPrices>(`/cards/${encodeURIComponent(cardId)}/graded-prices`),
    gradedPricesStructured: (cardId: string) =>
      request<GradedPricesStructured>(`/cards/${encodeURIComponent(cardId)}/graded-prices-structured`),
    priceHistory: (cardId: string, days = 90) =>
      request<{ card_id: string; days: number; data: PriceHistoryPoint[]; count: number }>(
        `/cards/${encodeURIComponent(cardId)}/price-history?days=${days}`
      ),
    ebaySold: (cardId: string, limit = 10) =>
      request<EbaySoldResult>(
        `/cards/${encodeURIComponent(cardId)}/ebay-sold?limit=${limit}`
      ),
  },

  /* ── Sealed Products ── */
  sealed: {
    list: (setName?: string, productType?: string) => {
      const params = new URLSearchParams()
      if (setName) params.set('set_name', setName)
      if (productType) params.set('product_type', productType)
      const qs = params.toString()
      return request<{ data: SealedProduct[]; count: number }>(
        `/sealed${qs ? `?${qs}` : ''}`
      )
    },
    get: (productId: number) =>
      request<SealedProduct>(`/sealed/${productId}`),
    priceHistory: (productId: number, days = 365) =>
      request<{ sealed_product_id: number; days: number; data: PriceHistoryPoint[]; count: number }>(
        `/sealed/${productId}/price-history?days=${days}`
      ),
  },

  /* ── Trending ── */
  trending: (limit = 20) =>
    request<{ data: TrendingCard[]; count: number }>(`/trending?limit=${limit}`),

  /* ── Collection ── */
  collection: {
    get: (userId: string, set?: string) =>
      request<{ user_id: string; items: CollectionItem[]; summary: CollectionSummary; count: number }>(
        `/collection/${userId}${set ? `?set=${set}` : ''}`
      ),
    add: (userId: string, body: AddCollectionBody) =>
      request<{ success: boolean; message: string }>(`/collection/${userId}`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    remove: (userId: string, cardId: string, condition?: string) =>
      request<{ success: boolean }>(`/collection/${userId}/${cardId}${condition ? `?condition=${condition}` : ''}`, {
        method: 'DELETE',
      }),
    portfolio: (userId: string, days = 30) =>
      request<{ user_id: string; summary: PortfolioSummary; history: PortfolioHistory[] }>(
        `/collection/${userId}/portfolio?days=${days}`
      ),
    stats: () => request<CollectionStats>('/collection/stats'),
  },

  /* ── Alerts ── */
  alerts: {
    list: (userId: string) =>
      request<{ user_id: string; alerts: AlertItem[] }>(`/alerts/${userId}`),
    create: (userId: string, body: CreateAlertBody) =>
      request<{ success: boolean; alert: AlertItem }>(`/alerts/${userId}`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    remove: (userId: string, alertId: number) =>
      request<{ success: boolean }>(`/alerts/${userId}/${alertId}`, { method: 'DELETE' }),
    check: (userId: string) =>
      request<{ user_id: string; triggered: AlertItem[]; count: number }>(`/alerts/${userId}/check`, {
        method: 'POST',
      }),
    stats: () => request<AlertStats>('/alerts/stats'),
  },

  /* ── Grading ── */
  grading: {
    estimate: (conditionNotes: string) =>
      request<GradeEstimate>('/grading/estimate', {
        method: 'POST',
        body: JSON.stringify({ condition_notes: conditionNotes }),
      }),
    costEstimate: (cardValue: number, estimatedGrade: number) =>
      request<GradeCostEstimate>('/grading/cost-estimate', {
        method: 'POST',
        body: JSON.stringify({ card_value: cardValue, estimated_grade: estimatedGrade }),
      }),
  },

  /* ── Agent ── */
  agent: {
    settings: () => request<AgentSettings>('/agent/settings'),
    updateSettings: (body: Partial<AgentSettings>) =>
      request<{ success: boolean; settings: AgentSettings }>('/agent/settings', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    canPurchase: (price: number, marketPrice: number) =>
      request<{ can_auto_purchase: boolean; price: number; market_price: number; remaining_budget: number }>(
        '/agent/can-purchase',
        { method: 'POST', body: JSON.stringify({ price, market_price: marketPrice }) }
      ),
    budget: () =>
      request<{ daily_budget: number; spent_today: number; remaining: number; autonomy_level: number }>(
        '/agent/budget'
      ),
  },

  /* ── Assistant ── */
  assistant: {
    chat: (message: string, history: ChatMessage[]) =>
      request<AssistantResponse>('/assistant/chat', {
        method: 'POST',
        body: JSON.stringify({ message, history }),
      }),
  },

  /* ── Stats ── */
  stats: () => request<{ collections: Record<string, unknown>; alerts: Record<string, unknown> }>('/stats'),

  /* ── Prices ── */
  prices: {
    cardHistory: (cardId: string, days: number = 90) =>
      request<{ card_id: string; days: number; data: PriceHistoryPoint[]; count: number }>(
        `/cards/${encodeURIComponent(cardId)}/price-history?days=${days}`
      ),
    gradedStructured: (cardId: string) =>
      request<GradedPricesStructured>(`/cards/${encodeURIComponent(cardId)}/graded-prices-structured`),
  },

  /* ── Stock Scanner ── */
  scan: {
    all: (query: string, retailers?: string[]) =>
      request<ScanResult>('/scan', {
        method: 'POST',
        body: JSON.stringify({ query, retailers }),
      }),
    retailer: (query: string, retailer: string) =>
      request<RetailerScanResult>(`/scan/${retailer}`, {
        method: 'POST',
        body: JSON.stringify({ query }),
      }),
  },

  /* ── Sync ── */
  sync: {
    triggerPriceSync: () =>
      request<{ success: boolean }>('/sync/prices', { method: 'POST' }),
  },
}

/* ═══════════════════════════════════════════════════════
   Types — matching Flask API responses
   ═══════════════════════════════════════════════════════ */

export interface SetItem {
  id: string
  name: string
  series: string
  release_date?: string
  total_cards?: number
  logo_url?: string
}

export interface SetDetail extends SetItem {
  value_index?: number
  description?: string
}

export interface PullRate {
  rarity: string
  rate: number
  [key: string]: unknown
}

export interface ChaseCard {
  id: string
  name: string
  number: string
  rarity: string
  image_url?: string
  price?: number
  [key: string]: unknown
}

export interface CardSearchResult {
  id: string
  name: string
  set: string
  number: string
  rarity: string
  image?: string
  price?: number | null
  [key: string]: unknown
}

export interface CardDetail {
  id: string
  name: string
  set: string
  set_id?: string
  number: string
  rarity: string
  supertype?: string
  subtype?: string
  image?: string
  image_url?: string
  small_image_url?: string
  tcgplayer_market?: number | null
  tcgplayer_low?: number | null
  tcgplayer_mid?: number | null
  tcgplayer_high?: number | null
  price?: number | null
  price_history?: { date: string; price: number }[]
  set_name?: string
  set_series?: string
  updated_at?: string
  raw_json?: string | null
  [key: string]: unknown
}

export interface GradedPriceEntry {
  grader: string
  grade: string
  grade_label?: string | null
  market: number | null
  low: number | null
  high: number | null
  source?: string | null
  updated_at?: string
}

export interface GradedPrices {
  [company: string]: GradedPriceEntry | { [grade: string]: number | null }
}

export interface CollectionItem {
  card_id: string
  card_name?: string
  quantity: number
  condition: string
  purchase_price?: number
  current_price?: number
  tcgplayer_market?: number
  [key: string]: unknown
}

export interface CollectionSummary {
  total_value: number
  total_cost: number
  total_items: number
  gain_loss: number
  [key: string]: unknown
}

export interface AddCollectionBody {
  card_id: string
  quantity?: number
  condition?: string
  purchase_price?: number
  purchase_date?: string
  notes?: string
}

export interface PortfolioSummary {
  total_value: number
  total_cost: number
  gain_loss: number
  roi_percent: number
  [key: string]: unknown
}

export interface PortfolioHistory {
  date: string
  value: number
}

export interface CollectionStats {
  [key: string]: unknown
}

export interface AlertItem {
  id: number
  card_id: string
  condition: string
  threshold: number
  is_active?: boolean
  created_at?: string
  last_triggered?: string | null
}

export interface CreateAlertBody {
  card_id: string
  condition: 'above' | 'below' | 'change_percent'
  threshold: number
}

export interface AlertStats {
  [key: string]: unknown
}

export interface GradeEstimate {
  estimated_grade?: number
  confidence?: number
  subgrades?: {
    centering?: number
    corners?: number
    surface?: number
    edges?: number
  }
  defects?: string[]
  [key: string]: unknown
}

export interface GradeCostEstimate {
  worth_grading?: boolean
  estimated_value?: number
  grading_cost?: number
  roi?: number
  [key: string]: unknown
}

export interface AgentSettings {
  autonomy_level: number
  daily_budget: number
  per_card_max: number
  deal_threshold_percent: number
  psa10_only: boolean
  raw_allowed: boolean
  modern_only: boolean
  ebay_allowed: boolean
  tcgplayer_allowed: boolean
  facebook_allowed: boolean
  notification_discord: boolean
  notification_telegram: boolean
  [key: string]: unknown
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AssistantResponse {
  response: string
  tool_results?: Record<string, unknown>[]
  model?: string
  demo_mode?: boolean
}

/* ── Sealed Products ── */
export interface SealedProduct {
  id: number
  name: string
  set_name: string
  product_type: string
  msrp: number | null
  current_price: number | null
  release_date?: string
  image_url?: string | null
  notes?: string | null
  [key: string]: unknown
}

/* ── Price History ── */
export interface PriceHistoryPoint {
  date: string
  price: number
}

/* ── Trending Cards ── */
export interface TrendingCard {
  id: string
  name: string
  set_name?: string
  set?: string
  rarity?: string
  price: number | null
  change_7d?: number | null
  change_30d?: number | null
  image_url?: string | null
  small_image_url?: string | null
  [key: string]: unknown
}

/* ── Graded Prices Structured ── */
export interface GradedPriceStructuredEntry {
  grade: string
  grade_label?: string | null
  market: number | null
  low: number | null
  high: number | null
  source?: string | null
  updated_at?: string
}

export interface GradedPricesStructured {
  [grader: string]: GradedPriceStructuredEntry[]
}

/* ── eBay Sold Listings ── */
export interface EbaySoldListing {
  title: string
  price: number
  currency: string
  condition: string
  image_url: string
  item_url: string
  item_id: string
}

export interface EbaySoldResult {
  listings: EbaySoldListing[]
  avg_price: number
  median_price: number
  low_price: number
  high_price: number
  count: number
  query: string
  fallback?: boolean
  message?: string
}

/* ── Stock Scanner ── */
export interface ScannedProduct {
  name: string
  retailer: string
  retailer_id: string
  price: number | null
  in_stock: boolean
}

export interface RetailerScanResult {
  retailer: string
  retailer_id: string
  products: ScannedProduct[]
  error: string | null
}

export interface ScanResult {
  query: string
  results: RetailerScanResult[]
  total_products: number
}
