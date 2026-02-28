/* ═══════════════════════════════════════════════════════
   React Query hooks — live data from Flask backend
   ═══════════════════════════════════════════════════════ */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AddCollectionBody, CreateAlertBody, AgentSettings, ChatMessage } from '@/lib/api'

/* ── Sets ── */
export function useSets(series?: string) {
  return useQuery({
    queryKey: ['sets', series],
    queryFn: () => api.sets.list(series),
    staleTime: 5 * 60_000,
  })
}

export function useSet(setId: string) {
  return useQuery({
    queryKey: ['set', setId],
    queryFn: () => api.sets.get(setId),
    enabled: !!setId,
    staleTime: 5 * 60_000,
  })
}

export function usePullRates(setId: string) {
  return useQuery({
    queryKey: ['pullRates', setId],
    queryFn: () => api.sets.pullRates(setId),
    enabled: !!setId,
    staleTime: 10 * 60_000,
  })
}

export function useChaseCards(setId: string, rarity?: string, limit = 24) {
  return useQuery({
    queryKey: ['chaseCards', setId, rarity, limit],
    queryFn: () => api.sets.chaseCards(setId, rarity, limit),
    enabled: !!setId,
    staleTime: 5 * 60_000,
  })
}

/* ── Cards ── */
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
    retry: 2,
  })
}

/* ── Assistant ── */
export function useAssistantChat() {
  return useMutation({
    mutationFn: ({ message, history }: { message: string; history: ChatMessage[] }) =>
      api.assistant.chat(message, history),
  })
}
