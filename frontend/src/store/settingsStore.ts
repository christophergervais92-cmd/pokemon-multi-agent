import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SettingsState {
  apiUrl: string
  zip: string
  desktopNotifications: boolean
  soundAlerts: boolean
  liveScanner: boolean
  safeMode: boolean
  notifications: boolean
  setApiUrl: (url: string) => void
  setZip: (zip: string) => void
  setNotifications: (v: boolean) => void
  toggleDesktopNotifications: () => void
  toggleSoundAlerts: () => void
  toggleLiveScanner: () => void
  toggleSafeMode: () => void
  updateSettings: (partial: Partial<SettingsState>) => void
}

const detectApiUrl = (): string => {
  const hostname = window.location.hostname
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:5001'
  }
  return 'https://pokemon-multi-agent.onrender.com'
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      apiUrl: detectApiUrl(),
      zip: '',
      desktopNotifications: false,
      soundAlerts: false,
      liveScanner: false,
      safeMode: false,
      notifications: false,
      setApiUrl: (url) => set({ apiUrl: url }),
      setZip: (zip) => set({ zip }),
      setNotifications: (v) => set({ notifications: v }),
      toggleDesktopNotifications: () => set((s) => ({ desktopNotifications: !s.desktopNotifications })),
      toggleSoundAlerts: () => set((s) => ({ soundAlerts: !s.soundAlerts })),
      toggleLiveScanner: () => set((s) => ({ liveScanner: !s.liveScanner })),
      toggleSafeMode: () => set((s) => ({ safeMode: !s.safeMode })),
      updateSettings: (partial) => set(partial),
    }),
    { name: 'pokeagent-settings' }
  )
)
