import { useState } from 'react'
import { motion } from 'framer-motion'
import { Lock, Plus, Trash2, TestTube, Activity, Wifi, WifiOff, Bell } from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Switch } from '@/components/ui/Switch'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { RETAILERS } from '@/lib/constants'
import { useAuthStore } from '@/store/authStore'

interface Monitor {
  id: string
  query: string
  retailer: string
  interval: number
  active: boolean
  lastHit: string | null
}

const MOCK_MONITORS: Monitor[] = [
  { id: '1', query: 'Prismatic Evolutions ETB', retailer: 'target', interval: 60, active: true, lastHit: '2 min ago' },
  { id: '2', query: 'Surging Sparks Booster Box', retailer: 'all', interval: 300, active: true, lastHit: null },
  { id: '3', query: 'Pokemon 151 ETB', retailer: 'walmart', interval: 30, active: false, lastHit: '1 hour ago' },
]

export default function Monitors() {
  const { user } = useAuthStore()
  const [monitors, setMonitors] = useState<Monitor[]>(MOCK_MONITORS)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [newQuery, setNewQuery] = useState('')
  const [newRetailer, setNewRetailer] = useState('all')
  const [newInterval, setNewInterval] = useState('60')
  const [newZip, setNewZip] = useState('')
  const [scannerRunning, setScannerRunning] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const isAuthenticated = !!user

  const toggleMonitor = (id: string) => {
    setMonitors(monitors.map(m => m.id === id ? { ...m, active: !m.active } : m))
  }

  const deleteMonitor = (id: string) => {
    setMonitors(monitors.filter(m => m.id !== id))
  }

  if (!isAuthenticated) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Card variant="elevated" className="max-w-md w-full text-center">
            <CardContent className="p-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent-muted flex items-center justify-center">
                <Lock className="w-8 h-8 text-accent" />
              </div>
              <h2 className="text-xl font-bold mb-2">Login Required</h2>
              <p className="text-muted text-sm mb-6">Connect your Discord account to create and manage stock monitors</p>
              <Button className="w-full">
                <img src="https://cdn.prod.website-files.com/6257adef93867e50d84d30e2/636e0a6ca814282eca7172c6_icon_clyde_white_RGB.svg" className="w-5 h-5 mr-2 invert" alt="" />
                Login with Discord
              </Button>
            </CardContent>
          </Card>
        </div>
      </PageTransition>
    )
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Stock Monitors</h1>
            <p className="text-muted-foreground/60 text-sm mt-1">Automated stock alerts with Discord webhooks</p>
          </div>
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus className="w-4 h-4 mr-1" /> New Monitor
          </Button>
        </div>

        {/* Scanner Status */}
        <Card variant={scannerRunning ? 'accent' : 'default'}>
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${scannerRunning ? 'bg-success animate-pulse' : 'bg-danger'}`} />
              <div>
                <p className="font-semibold">{scannerRunning ? 'Scanner Running' : 'Scanner Stopped'}</p>
                <p className="text-xs text-muted">{scannerRunning ? 'Last scan: 30s ago · 3 active monitors' : 'Click start to begin scanning'}</p>
              </div>
            </div>
            <Button
              variant={scannerRunning ? 'outline' : 'default'}
              size="sm"
              onClick={() => setScannerRunning(!scannerRunning)}
            >
              {scannerRunning ? <><WifiOff className="w-4 h-4 mr-1" /> Stop</> : <><Wifi className="w-4 h-4 mr-1" /> Start</>}
            </Button>
          </CardContent>
        </Card>

        {/* Webhook Config */}
        <Card variant="elevated">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Bell className="w-4 h-4" /> Discord Webhook
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3">
              <Input
                placeholder="https://discord.com/api/webhooks/..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="flex-1"
              />
              <Button variant="outline" size="sm">
                <TestTube className="w-4 h-4 mr-1" /> Test
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Create Monitor Form */}
        {showForm && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base">Create New Monitor</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Search Query"
                    placeholder="e.g. Prismatic Evolutions ETB"
                    value={newQuery}
                    onChange={(e) => setNewQuery(e.target.value)}
                  />
                  <Select
                    label="Retailer"
                    value={newRetailer}
                    onChange={(e) => setNewRetailer(e.target.value)}
                    options={RETAILERS.map(r => ({ value: r.id, label: r.name }))}
                  />
                  <Input
                    label="ZIP Code"
                    placeholder="e.g. 90210"
                    value={newZip}
                    onChange={(e) => setNewZip(e.target.value)}
                  />
                  <Select
                    label="Check Interval"
                    value={newInterval}
                    onChange={(e) => setNewInterval(e.target.value)}
                    options={[
                      { value: '30', label: 'Every 30 seconds' },
                      { value: '60', label: 'Every 1 minute' },
                      { value: '300', label: 'Every 5 minutes' },
                      { value: '900', label: 'Every 15 minutes' },
                    ]}
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                  <Button><Plus className="w-4 h-4 mr-1" /> Create Monitor</Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Monitor List */}
        <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
          {monitors.map((monitor) => (
            <motion.div key={monitor.id} variants={staggerItem}>
              <Card className="hover:border-border-light transition">
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold truncate">{monitor.query}</p>
                      <Badge variant={monitor.active ? 'success' : 'warning'}>
                        {monitor.active ? 'Active' : 'Paused'}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted">
                      <span className="capitalize">{monitor.retailer === 'all' ? 'All Retailers' : monitor.retailer}</span>
                      <span>·</span>
                      <span>Every {monitor.interval}s</span>
                      {monitor.lastHit && (
                        <>
                          <span>·</span>
                          <span className="text-success">Last hit: {monitor.lastHit}</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 ml-4">
                    <Switch
                      checked={monitor.active}
                      onChange={() => toggleMonitor(monitor.id)}
                    />
                    <button
                      onClick={() => deleteMonitor(monitor.id)}
                      className="p-2 text-muted hover:text-danger transition rounded-lg hover:bg-danger-muted"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </PageTransition>
  )
}
