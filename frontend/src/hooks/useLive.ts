import { useState, useEffect, useRef, useCallback } from 'react'
import { useSettingsStore } from '@/store/settingsStore'

export interface LiveEvent {
  id: string
  type: 'stock_update' | 'drop_alert' | 'price_change'
  data: Record<string, unknown>
  timestamp: string
}

interface UseLiveReturn {
  isConnected: boolean
  lastEvent: LiveEvent | null
  events: LiveEvent[]
}

const MAX_EVENTS = 100
const RECONNECT_BASE_DELAY = 1000
const RECONNECT_MAX_DELAY = 30000

export function useLive(): UseLiveReturn {
  const { apiUrl, liveScanner } = useSettingsStore()
  const [isConnected, setIsConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null)
  const [events, setEvents] = useState<LiveEvent[]>([])
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectDelayRef = useRef(RECONNECT_BASE_DELAY)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!liveScanner || !apiUrl) return

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const url = `${apiUrl}/api/live/stream`
    const es = new EventSource(url)
    eventSourceRef.current = es

    es.onopen = () => {
      if (!mountedRef.current) return
      setIsConnected(true)
      reconnectDelayRef.current = RECONNECT_BASE_DELAY
    }

    es.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const parsed = JSON.parse(event.data) as Omit<LiveEvent, 'id'>
        const liveEvent: LiveEvent = {
          ...parsed,
          id: crypto.randomUUID(),
          timestamp: parsed.timestamp || new Date().toISOString(),
        }
        setLastEvent(liveEvent)
        setEvents((prev) => [liveEvent, ...prev].slice(0, MAX_EVENTS))
      } catch {
        // Invalid JSON, skip
      }
    }

    // Handle specific event types
    const handleTypedEvent = (type: LiveEvent['type']) => (event: MessageEvent) => {
      if (!mountedRef.current) return
      try {
        const data = JSON.parse(event.data)
        const liveEvent: LiveEvent = {
          id: crypto.randomUUID(),
          type,
          data,
          timestamp: data.timestamp || new Date().toISOString(),
        }
        setLastEvent(liveEvent)
        setEvents((prev) => [liveEvent, ...prev].slice(0, MAX_EVENTS))
      } catch {
        // Invalid JSON, skip
      }
    }

    es.addEventListener('stock_update', handleTypedEvent('stock_update'))
    es.addEventListener('drop_alert', handleTypedEvent('drop_alert'))
    es.addEventListener('price_change', handleTypedEvent('price_change'))

    es.onerror = () => {
      if (!mountedRef.current) return
      setIsConnected(false)
      es.close()

      // Exponential backoff reconnect
      const delay = reconnectDelayRef.current
      reconnectDelayRef.current = Math.min(delay * 2, RECONNECT_MAX_DELAY)
      reconnectTimeoutRef.current = setTimeout(() => {
        if (mountedRef.current) connect()
      }, delay)
    }
  }, [apiUrl, liveScanner])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }
  }, [connect])

  return { isConnected, lastEvent, events }
}
