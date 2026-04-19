import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Lock, Plus, Trash2, TestTube, Wifi, WifiOff, Bell, Loader2, AlertCircle } from 'lucide-react'
import { useAccount } from 'wagmi'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Switch } from '@/components/ui/Switch'
import { EmptyState } from '@/components/ui/EmptyState'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { RETAILERS } from '@/lib/constants'
import { useSettingsStore } from '@/store/settingsStore'
import {
  useMonitors,
  useCreateMonitor,
  useToggleMonitor,
  useDeleteMonitor,
  useUpdateMonitor,
} from '@/hooks/useApi'

function timeAgo(iso: string | null): string {
  if (!iso) return 'never'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return 'never'
  const diffSec = Math.floor((Date.now() - then) / 1000)
  if (diffSec < 60) return `${diffSec}s ago`
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}

export default function Monitors() {
  const { address, isConnected } = useAccount()
  const userId = address?.toLowerCase() ?? ''
  const storedZip = useSettingsStore((s) => s.zip)

  const monitorsQ = useMonitors(userId)
  const createMut = useCreateMonitor(userId)
  const toggleMut = useToggleMonitor(userId)
  const deleteMut = useDeleteMonitor(userId)
  const updateMut = useUpdateMonitor(userId)

  const [webhookUrl, setWebhookUrl] = useState('')
  const [newQuery, setNewQuery] = useState('')
  const [newRetailer, setNewRetailer] = useState('all')
  const [newInterval, setNewInterval] = useState('60')
  const [newZip, setNewZip] = useState(storedZip || '')
  const [showForm, setShowForm] = useState(false)

  const monitors = monitorsQ.data?.monitors ?? []
  const stats = monitorsQ.data?.stats

  const handleCreate = async () => {
    if (!newQuery.trim()) return
    try {
      await createMut.mutateAsync({
        query: newQuery,
        retailer: newRetailer,
        zip_code: newZip || undefined,
        interval_seconds: parseInt(newInterval, 10),
        webhook_url: webhookUrl || undefined,
        active: true,
      })
      setNewQuery('')
      setShowForm(false)
    } catch {
      // Error bubbles up via mutation state; UI handles below.
    }
  }

  const testWebhook = async () => {
    if (!webhookUrl.trim()) return
    try {
      const res = await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: '🔔 PokeAgent webhook test — if you see this, your webhook is working.',
        }),
      })
      alert(res.ok ? 'Webhook test sent!' : `Webhook test failed: ${res.status}`)
    } catch (e) {
      alert(`Webhook test failed: ${e instanceof Error ? e.message : 'unknown error'}`)
    }
  }

  if (!isConnected) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Card variant="elevated" className="max-w-md w-full text-center">
            <CardContent className="p-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent-muted flex items-center justify-center">
                <Lock className="w-8 h-8 text-accent" />
              </div>
              <h2 className="text-xl font-bold mb-2">Wallet Required</h2>
              <p className="text-muted text-sm mb-6">
                Connect your wallet to create and manage stock monitors. Monitors are scoped to your address.
              </p>
            </CardContent>
          </Card>
        </div>
      </PageTransition>
    )
  }

  const anyRunning = monitors.some((m) => m.active)

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Stock Monitors</h1>
            <p className="text-muted-foreground/60 text-sm mt-1">
              Automated stock alerts with Discord webhooks · {stats ? `${stats.active}/${stats.total} active` : ''}
            </p>
          </div>
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus className="w-4 h-4 mr-1" /> New Monitor
          </Button>
        </div>

        {/* Scanner Status */}
        <Card variant={anyRunning ? 'accent' : 'default'}>
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${anyRunning ? 'bg-success animate-pulse' : 'bg-muted'}`} />
              <div>
                <p className="font-semibold">
                  {anyRunning ? 'Scanner Running' : 'No active monitors'}
                </p>
                <p className="text-xs text-muted">
                  {stats
                    ? `${stats.active} active · ${stats.paused} paused · ${stats.total_hits} total hits`
                    : 'Create a monitor to start scanning'}
                </p>
              </div>
            </div>
            {anyRunning ? (
              <Badge variant="success" className="gap-1"><Wifi className="w-3 h-3" /> Live</Badge>
            ) : (
              <Badge variant="default" className="gap-1"><WifiOff className="w-3 h-3" /> Idle</Badge>
            )}
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
              <Button
                variant="outline"
                size="sm"
                onClick={testWebhook}
                disabled={!webhookUrl.trim()}
              >
                <TestTube className="w-4 h-4 mr-1" /> Test
              </Button>
            </div>
            <p className="text-xs text-muted mt-2">
              Paste a Discord webhook URL above, then attach it to new monitors via the form.
            </p>
          </CardContent>
        </Card>

        {/* Create Monitor Form */}
        <AnimatePresence>
          {showForm && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
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
                      options={RETAILERS.map((r) => ({ value: r.id, label: r.name }))}
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
                  {createMut.isError && (
                    <div className="text-sm text-danger flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      {createMut.error instanceof Error ? createMut.error.message : 'Failed to create monitor'}
                    </div>
                  )}
                  <div className="flex justify-end gap-3">
                    <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                    <Button onClick={handleCreate} isLoading={createMut.isPending}>
                      <Plus className="w-4 h-4 mr-1" /> Create Monitor
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Monitor List */}
        {monitorsQ.isPending ? (
          <div className="flex items-center justify-center py-12 text-muted text-sm gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading monitors…
          </div>
        ) : monitors.length === 0 ? (
          <EmptyState
            icon={<Bell />}
            title="No monitors yet"
            description="Create your first stock monitor to start receiving Discord alerts."
            action={
              <Button onClick={() => setShowForm(true)}>
                <Plus className="w-4 h-4 mr-1" /> Create Monitor
              </Button>
            }
          />
        ) : (
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="space-y-3"
          >
            {monitors.map((m) => (
              <motion.div key={m.id} variants={staggerItem}>
                <Card className="hover:border-border-light transition">
                  <CardContent className="p-4 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-semibold truncate">{m.query}</p>
                        <Badge variant={m.active ? 'success' : 'warning'}>
                          {m.active ? 'Active' : 'Paused'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted flex-wrap">
                        <span className="capitalize">
                          {m.retailer === 'all' ? 'All Retailers' : m.retailer}
                        </span>
                        <span>·</span>
                        <span>Every {m.interval_seconds}s</span>
                        {m.zip_code && (<><span>·</span><span>ZIP {m.zip_code}</span></>)}
                        <span>·</span>
                        <span>
                          Last hit: {m.hit_count > 0 ? timeAgo(m.last_hit_at) : '—'}
                          {m.hit_count > 0 && ` (${m.hit_count} total)`}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 ml-4">
                      <Switch
                        checked={m.active}
                        onChange={() => toggleMut.mutate(m.id)}
                      />
                      <button
                        onClick={() => {
                          if (confirm(`Delete monitor "${m.query}"?`)) {
                            deleteMut.mutate(m.id)
                          }
                        }}
                        disabled={deleteMut.isPending}
                        className="p-2 text-muted hover:text-danger transition rounded-lg hover:bg-danger-muted disabled:opacity-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* Suppress unused warning for updateMut (reserved for future inline edit) */}
        <div style={{ display: 'none' }}>{updateMut.isIdle ? '' : ''}</div>
      </div>
    </PageTransition>
  )
}
