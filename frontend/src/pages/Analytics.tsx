import { useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, ShoppingCart, Target, Crosshair, Clock, Plus, Play } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { RETAILERS, CHART_COLORS } from '@/lib/constants'

const SPENDING_DATA = [
  { period: 'Mon', amount: 125 },
  { period: 'Tue', amount: 0 },
  { period: 'Wed', amount: 89 },
  { period: 'Thu', amount: 210 },
  { period: 'Fri', amount: 45 },
  { period: 'Sat', amount: 320 },
  { period: 'Sun', amount: 0 },
]

const MOCK_PURCHASES = [
  { id: '1', product: 'Prismatic Evolutions ETB', retailer: 'Target', price: 54.99, quantity: 2, date: '2026-02-25' },
  { id: '2', product: 'Surging Sparks Booster Box', retailer: 'GameStop', price: 143.99, quantity: 1, date: '2026-02-24' },
  { id: '3', product: 'Pokemon 151 ETB', retailer: 'Walmart', price: 39.99, quantity: 1, date: '2026-02-22' },
  { id: '4', product: 'Charizard ex SAR', retailer: 'TCGPlayer', price: 89.50, quantity: 1, date: '2026-02-20' },
  { id: '5', product: 'Evolving Skies Booster Pack', retailer: 'Amazon', price: 8.99, quantity: 5, date: '2026-02-19' },
]

const ACCURACY_DATA = [
  { retailer: 'Target', accuracy: 94, checks: 156, hits: 147 },
  { retailer: 'Walmart', accuracy: 87, checks: 203, hits: 177 },
  { retailer: 'Best Buy', accuracy: 91, checks: 89, hits: 81 },
  { retailer: 'GameStop', accuracy: 78, checks: 124, hits: 97 },
  { retailer: 'Pokemon Center', accuracy: 96, checks: 67, hits: 64 },
]

export default function Analytics() {
  const [showPurchaseForm, setShowPurchaseForm] = useState(false)

  const totalSpend = MOCK_PURCHASES.reduce((s, p) => s + p.price * p.quantity, 0)
  const totalScans = ACCURACY_DATA.reduce((s, a) => s + a.checks, 0)
  const totalHits = ACCURACY_DATA.reduce((s, a) => s + a.hits, 0)
  const overallAccuracy = totalScans > 0 ? (totalHits / totalScans * 100) : 0

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Analytics</h1>
          <p className="text-muted-foreground/60 text-sm mt-1">Purchase tracking, stock accuracy, and performance insights</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Scans', value: formatPrice(totalScans), icon: Crosshair, color: 'accent' },
            { label: 'Stock Hits', value: formatPrice(totalHits), icon: Target, color: 'success' },
            { label: 'Accuracy', value: `${overallAccuracy.toFixed(1)}%`, icon: BarChart3, color: 'info' },
            { label: 'Spent (Week)', value: `$${formatPrice(totalSpend)}`, icon: ShoppingCart, color: 'warning' },
          ].map((stat) => (
            <Card variant="elevated" key={stat.label}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className={`p-1.5 rounded-lg bg-${stat.color}-muted`}>
                    <stat.icon className={`w-4 h-4 text-${stat.color}`} />
                  </div>
                  <span className="text-xs text-muted">{stat.label}</span>
                </div>
                <p className="text-2xl font-mono-numbers font-bold">{stat.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Spending Chart */}
          <Card variant="elevated">
            <CardHeader>
              <CardTitle className="text-base">Weekly Spending</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={SPENDING_DATA}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                    <XAxis dataKey="period" stroke={CHART_COLORS.text} fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke={CHART_COLORS.text} fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v: number) => `$${v}`} />
                    <Tooltip
                      contentStyle={{ background: '#0a1228', border: '1px solid #162550', borderRadius: '12px' }}
                      itemStyle={{ color: '#f1f5f9' }}
                      formatter={(v) => [`$${formatPrice(v as number)}`, 'Spent']}
                    />
                    <Bar dataKey="amount" fill={CHART_COLORS.line} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Retailer Accuracy */}
          <Card variant="elevated">
            <CardHeader>
              <CardTitle className="text-base">Stock Check Accuracy</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {ACCURACY_DATA.map((r) => (
                <div key={r.retailer} className="space-y-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{r.retailer}</span>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-muted">{r.hits}/{r.checks} hits</span>
                      <span className="font-mono-numbers font-bold">{r.accuracy}%</span>
                    </div>
                  </div>
                  <Progress
                    value={r.accuracy}
                    color={r.accuracy >= 90 ? 'success' : r.accuracy >= 80 ? 'warning' : 'danger'}
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Purchase History */}
        <Card variant="elevated">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">Purchase History</CardTitle>
            <Button size="sm" onClick={() => setShowPurchaseForm(!showPurchaseForm)}>
              <Plus className="w-4 h-4 mr-1" /> Log Purchase
            </Button>
          </CardHeader>
          <CardContent>
            {showPurchaseForm && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-4 p-4 rounded-lg bg-surface border border-border">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <Input placeholder="Product name" />
                  <Select options={RETAILERS.slice(1).map(r => ({ value: r.id, label: r.name }))} />
                  <Input type="number" placeholder="Price" />
                  <Input type="number" placeholder="Qty" />
                </div>
                <div className="flex justify-end mt-3 gap-2">
                  <Button variant="ghost" size="sm" onClick={() => setShowPurchaseForm(false)}>Cancel</Button>
                  <Button size="sm"><Plus className="w-3 h-3 mr-1" /> Add</Button>
                </div>
              </motion.div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted uppercase">
                    <th className="pb-3 font-medium">Product</th>
                    <th className="pb-3 font-medium">Retailer</th>
                    <th className="pb-3 font-medium text-right">Price</th>
                    <th className="pb-3 font-medium text-right">Qty</th>
                    <th className="pb-3 font-medium text-right">Total</th>
                    <th className="pb-3 font-medium text-right">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_PURCHASES.map((p) => (
                    <tr key={p.id} className="border-b border-border/50 hover:bg-surface-hover/50 transition">
                      <td className="py-3 font-medium">{p.product}</td>
                      <td className="py-3"><Badge variant="default">{p.retailer}</Badge></td>
                      <td className="py-3 text-right font-mono-numbers">${formatPrice(p.price)}</td>
                      <td className="py-3 text-right">{p.quantity}</td>
                      <td className="py-3 text-right font-mono-numbers font-bold">${formatPrice(p.price * p.quantity)}</td>
                      <td className="py-3 text-right text-muted">{p.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Backtest */}
        <Card variant="elevated">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Clock className="w-4 h-4" /> Backtest Runner
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted mb-4">Simulate stock checks over a time period to evaluate monitor performance</p>
            <div className="flex gap-3">
              <Input placeholder="Product name" className="flex-1" />
              <Select options={[{ value: '7d', label: 'Last 7 days' }, { value: '30d', label: 'Last 30 days' }, { value: '90d', label: 'Last 90 days' }]} />
              <Button><Play className="w-4 h-4 mr-1" /> Run</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  )
}
