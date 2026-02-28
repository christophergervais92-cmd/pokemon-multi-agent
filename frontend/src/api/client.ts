import { useSettingsStore } from '@/store/settingsStore'
import { useAuthStore } from '@/store/authStore'

class APIClient {
  private getBaseUrl(): string {
    return useSettingsStore.getState().apiUrl
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    const token = useAuthStore.getState().token
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    return headers
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(endpoint, this.getBaseUrl())
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) url.searchParams.set(key, value)
      })
    }
    const res = await fetch(url.toString(), {
      headers: this.getHeaders(),
    })
    if (!res.ok) throw new Error(`API Error: ${res.status} ${res.statusText}`)
    return res.json()
  }

  async post<T>(endpoint: string, body?: unknown): Promise<T> {
    const url = new URL(endpoint, this.getBaseUrl())
    const res = await fetch(url.toString(), {
      method: 'POST',
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    })
    if (!res.ok) throw new Error(`API Error: ${res.status} ${res.statusText}`)
    return res.json()
  }

  async delete<T>(endpoint: string): Promise<T> {
    const url = new URL(endpoint, this.getBaseUrl())
    const res = await fetch(url.toString(), {
      method: 'DELETE',
      headers: this.getHeaders(),
    })
    if (!res.ok) throw new Error(`API Error: ${res.status} ${res.statusText}`)
    return res.json()
  }

  getStreamUrl(endpoint: string): string {
    return `${this.getBaseUrl()}${endpoint}`
  }
}

export const api = new APIClient()
