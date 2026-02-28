import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Settings as SettingsIcon, Globe, Bell, BellOff, Volume2, VolumeX,
  Wifi, MapPin, CreditCard, Link, Download, Upload, Trash2, AlertTriangle,
  ExternalLink, Check
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
  { name: 'Target', icon: '🎯', connected: true, url: 'https://target.com' },
  { name: 'Walmart', icon: '🔵', connected: false, url: 'https://walmart.com' },
  { name: 'Best Buy', icon: '🟡', connected: true, url: 'https://bestbuy.com' },
  { name: 'GameStop', icon: '🔴', connected: false, url: 'https://gamestop.com' },
  { name: 'Pokemon Center', icon: '⚡', connected: true, url: 'https://pokemoncenter.com' },
  { name: 'TCGPlayer', icon: '🃏', connected: true, url: 'https://tcgplayer.com' },
]

export default function Settings() {
  const { apiUrl, setApiUrl, notifications, setNotifications } = useSettingsStore()
  const [localApiUrl, setLocalApiUrl] = useState(apiUrl)
  const [zipCode, setZipCode] = useState('90210')
  const [testResult, setTestResult] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [desktopNotifications, setDesktopNotifications] = useState(notifications)
  const [soundAlerts, setSoundAlerts] = useState(true)
  const [liveScanner, setLiveScanner] = useState(true)
  const [safeMode, setSafeMode] = useState(false)

  const testConnection = () => {
    setTestResult('testing')
    setTimeout(() => {
      setTestResult(localApiUrl.includes('render.com') || localApiUrl.includes('localhost') ? 'success' : 'error')
      setTimeout(() => setTestResult('idle'), 3000)
    }, 1500)
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
                <CardDescription>Configure the backend API endpoint</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-3">
                  <Input
                    placeholder="https://pokemon-multi-agent.onrender.com"
                    value={localApiUrl}
                    onChange={(e) => setLocalApiUrl(e.target.value)}
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    onClick={testConnection}
                    isLoading={testResult === 'testing'}
                  >
                    {testResult === 'success' ? <><Check className="w-4 h-4 mr-1 text-success" /> Connected</> :
                     testResult === 'error' ? 'Failed' : 'Test'}
                  </Button>
                  <Button onClick={() => setApiUrl(localApiUrl)}>Save</Button>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-border">
                  <div>
                    <p className="text-sm font-medium">Safe Mode</p>
                    <p className="text-xs text-muted">Disable proxy, use direct API calls only</p>
                  </div>
                  <Switch checked={safeMode} onChange={setSafeMode} />
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
                  { label: 'Desktop Notifications', desc: 'Browser push notifications for stock alerts', icon: desktopNotifications ? Bell : BellOff, checked: desktopNotifications, onChange: (v: boolean) => { setDesktopNotifications(v); setNotifications(v) } },
                  { label: 'Sound Alerts', desc: 'Play sound when stock is found', icon: soundAlerts ? Volume2 : VolumeX, checked: soundAlerts, onChange: setSoundAlerts },
                  { label: 'Live Scanner Feed', desc: 'Show real-time stock transitions', icon: Wifi, checked: liveScanner, onChange: setLiveScanner },
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
              </CardHeader>
              <CardContent>
                <Input
                  label="Default ZIP Code"
                  placeholder="90210"
                  value={zipCode}
                  onChange={(e) => setZipCode(e.target.value)}
                  className="max-w-xs"
                />
              </CardContent>
            </Card>
          </motion.div>

          {/* Retailer Accounts */}
          <motion.div variants={staggerItem}>
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><Link className="w-4 h-4" /> Retailer Accounts</CardTitle>
                <CardDescription>Link your retailer accounts for faster checkout</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {RETAILER_ACCOUNTS.map((r) => (
                    <div key={r.name} className="flex items-center justify-between p-3 rounded-lg bg-surface border border-border">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{r.icon}</span>
                        <span className="text-sm font-medium">{r.name}</span>
                      </div>
                      {r.connected ? (
                        <Badge variant="success">Connected</Badge>
                      ) : (
                        <Button variant="ghost" size="sm" onClick={() => window.open(r.url, '_blank')}>
                          <ExternalLink className="w-3 h-3 mr-1" /> Link
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
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
                  <Button variant="outline" className="flex-1">
                    <Download className="w-4 h-4 mr-2" /> Export Data
                  </Button>
                  <Button variant="outline" className="flex-1">
                    <Upload className="w-4 h-4 mr-2" /> Import Data
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
                <p className="text-sm text-muted mb-4">Permanently delete all local data including portfolio, purchases, settings, and cache.</p>
                <Button variant="danger">
                  <Trash2 className="w-4 h-4 mr-2" /> Delete All Data
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </PageTransition>
  )
}
