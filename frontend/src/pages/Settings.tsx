import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Globe, Bell, BellOff, Volume2, VolumeX,
  Wifi, MapPin, CreditCard, Link, Download, Upload, Trash2, AlertTriangle,
  ExternalLink, Check, X,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Switch } from '@/components/ui/Switch'
import { Badge } from '@/components/ui/Badge'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { useSettingsStore } from '@/store/settingsStore'

const RETAILER_ACCOUNTS = [
  { name: 'Target', icon: '🎯', url: 'https://target.com' },
  { name: 'Walmart', icon: '🔵', url: 'https://walmart.com' },
  { name: 'Best Buy', icon: '🟡', url: 'https://bestbuy.com' },
  { name: 'GameStop', icon: '🔴', url: 'https://gamestop.com' },
  { name: 'Pokemon Center', icon: '⚡', url: 'https://pokemoncenter.com' },
  { name: 'TCGPlayer', icon: '🃏', url: 'https://tcgplayer.com' },
]

export default function Settings() {
  const {
    apiUrl, setApiUrl,
    zip, setZip,
    notifications, setNotifications,
    desktopNotifications, toggleDesktopNotifications,
    soundAlerts, toggleSoundAlerts,
    liveScanner, toggleLiveScanner,
    safeMode, toggleSafeMode,
  } = useSettingsStore()

  const [localApiUrl, setLocalApiUrl] = useState(apiUrl)
  const [localZip, setLocalZip] = useState(zip)
  const [testResult, setTestResult] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [testLatency, setTestLatency] = useState<number | null>(null)

  useEffect(() => { setLocalApiUrl(apiUrl) }, [apiUrl])
  useEffect(() => { setLocalZip(zip) }, [zip])

  const testConnection = async () => {
    setTestResult('testing')
    setTestLatency(null)
    const started = performance.now()
    try {
      // Normalize: strip trailing slash, ensure no trailing /api
      const base = localApiUrl.replace(/\/+$/, '').replace(/\/api$/, '')
      const res = await fetch(`${base}/api/health`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      })
      const latency = Math.round(performance.now() - started)
      if (res.ok) {
        const data = await res.json().catch(() => null)
        if (data && data.status === 'ok') {
          setTestResult('success')
          setTestLatency(latency)
        } else {
          setTestResult('error')
        }
      } else {
        setTestResult('error')
      }
    } catch {
      setTestResult('error')
    }
    setTimeout(() => setTestResult((prev) => (prev === 'testing' ? 'idle' : prev)), 100)
    setTimeout(() => setTestResult('idle'), 4000)
  }

  const saveApiUrl = () => {
    // Normalize to include /api path for consistency with VITE_API_URL default
    const trimmed = localApiUrl.replace(/\/+$/, '')
    setApiUrl(trimmed)
  }

  const saveZip = () => setZip(localZip.trim())

  const exportData = () => {
    const blob = new Blob([JSON.stringify({
      settings: useSettingsStore.getState(),
      exportedAt: new Date().toISOString(),
    }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pokeagent-backup-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const wipeLocal = () => {
    if (!confirm('Delete all local PokeAgent data? This clears settings, cached queries, and local auth. Cannot be undone.')) {
      return
    }
    // Known keys this app persists via zustand.
    const keys = ['pokeagent-auth', 'pokeagent-settings', 'ptcg-query-cache']
    keys.forEach((k) => localStorage.removeItem(k))
    // And anything that starts with pokeagent- just in case
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i)
      if (k && k.startsWith('pokeagent-')) localStorage.removeItem(k)
    }
    window.location.reload()
  }

  return (
    <PageTransition>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="page-header">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Settings</h1>
          <p className="text-muted-foreground/60 text-sm mt-1">Configure your PokeAgent experience</p>
        </div>

        <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-6">
          {/* API Configuration */}
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><Globe className="w-4 h-4" /> API Configuration</CardTitle>
                <CardDescription>Backend API URL — persisted to your browser</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  <Input
                    placeholder="https://pokemon-multi-agent.onrender.com"
                    value={localApiUrl}
                    onChange={(e) => setLocalApiUrl(e.target.value)}
                    className="flex-1 min-w-[260px]"
                  />
                  <Button
                    variant="outline"
                    onClick={testConnection}
                    isLoading={testResult === 'testing'}
                  >
                    {testResult === 'success' ? (
                      <><Check className="w-4 h-4 mr-1 text-success" /> OK {testLatency != null ? `${testLatency}ms` : ''}</>
                    ) : testResult === 'error' ? (
                      <><X className="w-4 h-4 mr-1 text-danger" /> Failed</>
                    ) : 'Test'}
                  </Button>
                  <Button onClick={saveApiUrl} disabled={localApiUrl === apiUrl}>Save</Button>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-border">
                  <div>
                    <p className="text-sm font-medium">Safe Mode</p>
                    <p className="text-xs text-muted">Disable proxy, use direct API calls only</p>
                  </div>
                  <Switch checked={safeMode} onChange={toggleSafeMode} />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Notifications */}
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><Bell className="w-4 h-4" /> Notifications</CardTitle>
                <CardDescription>Control how you receive alerts</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  {
                    label: 'Desktop Notifications', desc: 'Browser push notifications for stock alerts',
                    icon: notifications ? Bell : BellOff,
                    checked: notifications,
                    onChange: (v: boolean) => { setNotifications(v); if (v !== desktopNotifications) toggleDesktopNotifications() },
                  },
                  {
                    label: 'Sound Alerts', desc: 'Play sound when stock is found',
                    icon: soundAlerts ? Volume2 : VolumeX,
                    checked: soundAlerts,
                    onChange: () => toggleSoundAlerts(),
                  },
                  {
                    label: 'Live Scanner Feed', desc: 'Show real-time stock transitions',
                    icon: Wifi,
                    checked: liveScanner,
                    onChange: () => toggleLiveScanner(),
                  },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between p-3 rounded-lg bg-surface border border-border">
                    <div className="flex items-center gap-3">
                      <item.icon className="w-5 h-5 text-muted" />
                      <div>
                        <p className="text-sm font-medium">{item.label}</p>
                        <p className="text-xs text-muted">{item.desc}</p>
                      </div>
                    </div>
                    <Switch checked={item.checked} onChange={item.onChange} />
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>

          {/* Location */}
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><MapPin className="w-4 h-4" /> Location</CardTitle>
                <CardDescription>Default ZIP for stock searches &amp; local alerts</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-3 items-end">
                  <Input
                    label="Default ZIP Code"
                    placeholder="90210"
                    value={localZip}
                    onChange={(e) => setLocalZip(e.target.value)}
                    className="max-w-xs"
                  />
                  <Button onClick={saveZip} disabled={localZip === zip}>Save ZIP</Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Retailer Accounts */}
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><Link className="w-4 h-4" /> Retailer Accounts</CardTitle>
                <CardDescription>Open retailer sites to manage your accounts</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {RETAILER_ACCOUNTS.map((r) => (
                    <div key={r.name} className="flex items-center justify-between p-3 rounded-lg bg-surface border border-border">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{r.icon}</span>
                        <span className="text-sm font-medium">{r.name}</span>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => window.open(r.url, '_blank')}>
                        <ExternalLink className="w-3 h-3 mr-1" /> Open
                      </Button>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-muted mt-3">
                  Account linking requires server-side OAuth per retailer — coming soon.
                </p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Data */}
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><CreditCard className="w-4 h-4" /> Data Management</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1" onClick={exportData}>
                    <Download className="w-4 h-4 mr-2" /> Export Settings
                  </Button>
                  <Button variant="outline" className="flex-1" disabled>
                    <Upload className="w-4 h-4 mr-2" /> Import <Badge className="ml-2">Soon</Badge>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Danger Zone */}
          <motion.div variants={staggerItem}>
            <Card variant="danger">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2 text-danger">
                  <AlertTriangle className="w-4 h-4" /> Danger Zone
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted mb-4">
                  Permanently delete all local data — settings, cached queries, and local auth tokens. The page will reload.
                </p>
                <Button variant="danger" onClick={wipeLocal}>
                  <Trash2 className="w-4 h-4 mr-2" /> Delete All Local Data
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </PageTransition>
  )
}
