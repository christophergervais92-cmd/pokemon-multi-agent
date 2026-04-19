/* ═══════════════════════════════════════════════════════
   React Query hooks — live data from Flask backend
   ═══════════════════════════════════════════════════════ */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AddCollectionBody, CreateAlertBody, AgentSettings, ChatMessage, SetCardItem } from '@/lib/api'

/* ── Sets (stable data — long cache) ── */
export function useSets(series?: string) {
  return useQuery({
    queryKey: ['sets', series],
    queryFn: () => api.sets.list(series),
    staleTime: 10 * 60_000,   // sets rarely change — 10 min
    gcTime: 60 * 60_000,      // keep in memory 1 hour
  })
}

export function useSet(setId: string) {
  return useQuery({
    queryKey: ['set', setId],
    queryFn: () => api.sets.get(setId),
    enabled: !!setId,
    staleTime: 10 * 60_000,
    gcTime: 60 * 60_000,
  })
}

export function usePullRates(setId: string) {
  return useQuery({
    queryKey: ['pullRates', setId],
    queryFn: () => api.sets.pullRates(setId),
    enabled: !!setId,
    staleTime: 15 * 60_000,   // pull rates are static
    gcTime: 60 * 60_000,
  })
}

export function useChaseCards(setId: string, rarity?: string, limit = 24) {
  return useQuery({
    queryKey: ['chaseCards', setId, rarity, limit],
    queryFn: () => api.sets.chaseCards(setId, rarity, limit),
    enabled: !!setId,
    staleTime: 5 * 60_000,
    gcTime: 30 * 60_000,
  })
}

export function useSetCards(setId: string, page = 1, limit = 60) {
  return useQuery({
    queryKey: ['setCards', setId, page, limit],
    queryFn: () => api.sets.cards(setId, page, limit),
    enabled: !!setId,
    staleTime: 10 * 60_000,
    gcTime: 60 * 60_000,
    placeholderData: (prev) => prev,
  })
}
// Re-export SetCardItem for convenience
export type { SetCardItem }

/* ── Cards ── */
export function useAllCards(opts?: {
  page?: number; limit?: number;
  set?: string; rarity?: string;
  minPrice?: number; maxPrice?: number;
  q?: string;
  sort?: 'price' | 'name' | 'set' | 'rarity';
  dir?: 'asc' | 'desc';
}) {
  return useQuery({
    queryKey: ['allCards', opts],
    queryFn: () => api.cards.list(opts),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    placeholderData: (prev) => prev,
  })
}

export function useCardRarities() {
  return useQuery({
    queryKey: ['cardRarities'],
    queryFn: () => api.cards.rarities(),
    staleTime: 10 * 60_000,
    gcTime: 60 * 60_000,
  })
}

export function useCardSearch(query: string, opts?: { set?: string; rarity?: string; limit?: number }) {
  return useQuery({
    queryKey: ['cardSearch', query, opts],
    queryFn: () => api.cards.search(query, opts),
    enabled: query.length >= 2,
    staleTime: 2 * 60_000,
  })
}

export function useCard(cardId: string) {
  return useQuery({
    queryKey: ['card', cardId],
    queryFn: () => api.cards.get(cardId),
    enabled: !!cardId,
    staleTime: 2 * 60_000,
  })
}

export function useGradedPrices(cardId: string) {
  return useQuery({
    queryKey: ['gradedPrices', cardId],
    queryFn: () => api.cards.gradedPrices(cardId),
    enabled: !!cardId,
    staleTime: 5 * 60_000,
  })
}

export function useEbaySold(cardId: string | undefined, limit = 10) {
  return useQuery({
    queryKey: ['ebaySold', cardId, limit],
    queryFn: () => api.cards.ebaySold(cardId!, limit),
    enabled: !!cardId,
    staleTime: 5 * 60_000,
  })
}

/* ── Collection ── */
export function useCollection(userId: string, set?: string) {
  return useQuery({
    queryKey: ['collection', userId, set],
    queryFn: () => api.collection.get(userId, set),
    enabled: !!userId,
    staleTime: 60_000,
  })
}

export function useAddToCollection(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AddCollectionBody) => api.collection.add(userId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['collection', userId] }),
  })
}

export function useRemoveFromCollection(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ cardId, condition }: { cardId: string; condition?: string }) =>
      api.collection.remove(userId, cardId, condition),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['collection', userId] }),
  })
}

export function usePortfolio(userId: string, days = 30) {
  return useQuery({
    queryKey: ['portfolio', userId, days],
    queryFn: () => api.collection.portfolio(userId, days),
    enabled: !!userId,
    staleTime: 2 * 60_000,
  })
}

/* ── Alerts ── */
export function useAlerts(userId: string) {
  return useQuery({
    queryKey: ['alerts', userId],
    queryFn: () => api.alerts.list(userId),
    enabled: !!userId,
    staleTime: 60_000,
  })
}

export function useCreateAlert(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateAlertBody) => api.alerts.create(userId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts', userId] }),
  })
}

export function useCheckAlerts(userId: string) {
  return useMutation({
    mutationFn: () => api.alerts.check(userId),
  })
}

/* ── Grading ── */
export function useGradeEstimate() {
  return useMutation({
    mutationFn: (conditionNotes: string) => api.grading.estimate(conditionNotes),
  })
}

export function useGradeCostEstimate() {
  return useMutation({
    mutationFn: ({ cardValue, estimatedGrade }: { cardValue: number; estimatedGrade: number }) =>
      api.grading.costEstimate(cardValue, estimatedGrade),
  })
}

/* ── Agent ── */
export function useAgentSettings() {
  return useQuery({
    queryKey: ['agentSettings'],
    queryFn: () => api.agent.settings(),
    staleTime: 5 * 60_000,
  })
}

export function useUpdateAgentSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<AgentSettings>) => api.agent.updateSettings(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agentSettings'] }),
  })
}

export function useAgentBudget() {
  return useQuery({
    queryKey: ['agentBudget'],
    queryFn: () => api.agent.budget(),
    staleTime: 60_000,
  })
}

/* ── Stats ── */
export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => api.stats(),
    staleTime: 5 * 60_000,
  })
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    staleTime: 30_000,
    retry: 4,
    retryDelay: (attempt) => Math.min(3000 * (attempt + 1), 15_000), // 3s, 6s, 9s, 12s
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}

/* ── Assistant ── */
export function useAssistantChat() {
  return useMutation({
    mutationFn: ({ message, history }: { message: string; history: ChatMessage[] }) =>
      api.assistant.chat(message, history),
  })
}

/* ── Sealed Products (moderately stable) ── */
export function useSealedProducts(setName?: string, productType?: string) {
  return useQuery({
    queryKey: ['sealed', setName, productType],
    queryFn: () => api.sealed.list(setName, productType),
    staleTime: 10 * 60_000,  // sealed products change slowly
    gcTime: 60 * 60_000,
  })
}

export function useSealedPriceHistory(id: number | undefined, days: number = 90) {
  return useQuery({
    queryKey: ['sealedPriceHistory', id, days],
    queryFn: () => api.sealed.priceHistory(id!, days),
    enabled: !!id,
    staleTime: 5 * 60_000,
    gcTime: 30 * 60_000,
  })
}

/* ── Card Price History ── */
export function useCardPriceHistory(cardId: string | undefined, days: number = 90) {
  return useQuery({
    queryKey: ['cardPriceHistory', cardId, days],
    queryFn: () => api.cards.priceHistory(cardId!, days),
    enabled: !!cardId,
    staleTime: 5 * 60_000,
    gcTime: 30 * 60_000,
  })
}

export function useGradedPricesStructured(cardId: string | undefined) {
  return useQuery({
    queryKey: ['gradedPricesStructured', cardId],
    queryFn: () => api.cards.gradedPricesStructured(cardId!),
    enabled: !!cardId,
    staleTime: 10 * 60_000,
    gcTime: 60 * 60_000,
  })
}

/* ── Trending (cached but refreshes more often) ── */
export function useTrendingCards(limit: number = 20) {
  return useQuery({
    queryKey: ['trending', limit],
    queryFn: () => api.trending(limit),
    staleTime: 5 * 60_000,
    gcTime: 30 * 60_000,
  })
}

/* ── Drops ── */
export function useDrops(filter?: string) {
  return useQuery({
    queryKey: ['drops', filter],
    queryFn: () => api.drops.list(filter),
    staleTime: 2 * 60_000,
    gcTime: 10 * 60_000,
  })
}

export function useDropsCalendar() {
  return useQuery({
    queryKey: ['dropsCalendar'],
    queryFn: () => api.drops.calendar(),
    staleTime: 5 * 60_000,
    gcTime: 30 * 60_000,
  })
}

export function useDropsRumors(reliability?: string) {
  return useQuery({
    queryKey: ['dropsRumors', reliability],
    queryFn: () => api.drops.rumors(reliability),
    staleTime: 5 * 60_000,
    gcTime: 30 * 60_000,
  })
}

export function useDropsLiveIntel(source?: string, verifiedOnly?: boolean) {
  return useQuery({
    queryKey: ['dropsLiveIntel', source, verifiedOnly],
    queryFn: () => api.drops.liveIntel(source, verifiedOnly),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  })
}

/* ── Monitors ── */
export function useMonitors(userId: string) {
  return useQuery({
    queryKey: ['monitors', userId],
    queryFn: () => api.monitors.list(userId),
    enabled: !!userId,
    staleTime: 30_000,
  })
}

export function useCreateMonitor(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: import('@/lib/api').CreateMonitorBody) => api.monitors.create(userId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['monitors', userId] }),
  })
}

export function useUpdateMonitor(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<import('@/lib/api').CreateMonitorBody> }) =>
      api.monitors.update(userId, id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['monitors', userId] }),
  })
}

export function useToggleMonitor(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.monitors.toggle(userId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['monitors', userId] }),
  })
}

export function useDeleteMonitor(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.monitors.delete(userId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['monitors', userId] }),
  })
}

/* ── Vending ── */
export function useVendingLocations(params?: {
  zip?: string; state?: string; city?: string; radius?: number; verifiedOnly?: boolean
}) {
  return useQuery({
    queryKey: ['vendingLocations', params],
    queryFn: () => api.vending.locations(params),
    staleTime: 10 * 60_000,
    gcTime: 60 * 60_000,
  })
}
