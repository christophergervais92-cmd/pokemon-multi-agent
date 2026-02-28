import { useState } from 'react'
import { motion } from 'framer-motion'
import { PieChart as PieIcon, Plus, RefreshCw, Trash2, TrendingUp, TrendingDown, DollarSign, Package } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { GRADE_TYPES } from '@/lib/constants'

interface PortfolioItem {
  id: string
  name: string
  grade: string
  type: string
  costBasis: number
  currentPrice: number
  quantity: number
}

const MOCK_PORTFOLIO: PortfolioItem[] = [
  { id: '1', name: 'Charizard ex SAR', grade: 'PSA 10', type: 'Pokemon', costBasis: 180, currentPrice: 275, quantity: 1 },
  { id: '2', name: 'Umbreon VMAX Alt Art', grade: 'Raw', type: 'Pokemon', costBasis: 280, currentPrice: 350, quantity: 1 },
  { id: '3', name: 'Pikachu ex SAR', grade: 'PSA 9', type: 'Pokemon', costBasis: 120, currentPrice: 145, quantity: 2 },
  { id: '4', name: 'Evolving Skies Booster Box', grade: 'Sealed', type: 'Sealed', costBasis: 250, currentPrice: 420, quantity: 1 },
  { id: '5', name: 'Prismatic Evolutions ETB', grade: 'Sealed', type: 'Sealed', costBasis: 55, currentPrice: 85, quantity: 3 },
  { id: '6', name: 'Gengar ex SAR', grade: 'Raw', type: 'Pokemon', costBasis: 42, currentPrice: 55, quantity: 1 },
]

const PIE_COLORS = ['#60a5fa', '#818cf8', '#34d399', '#22d3ee', '#a78bfa', '#67e8f9']

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>(MOCK_PORTFOLIO)
  const [showAddForm, setShowAddForm] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const totalCost = portfolio.reduce((sum, item) => sum + item.costBasis * item.quantity, 0)
  const totalValue = portfolio.reduce((sum, item) => sum + item.currentPrice * item.quantity, 0)
  const totalGain = totalValue - totalCost
  const roiPercent = totalCost > 0 ? ((totalGain / totalCost) * 100) : 0
  const totalItems = portfolio.reduce((sum, item) => sum + item.quantity, 0)

  const pieData = portfolio.map(item => ({
    name: item.name,
    value: item.currentPrice * item.quantity,
  }))

  const refreshPrices = () => {
    setIsRefreshing(true)
    setTimeout(() => setIsRefreshing(false), 2000)
  }

  const deleteItem = (id: string) => {
    setPortfolio(portfolio.filter(p => p.id !== id))
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Portfolio</h1>
            <p className="text-muted-foreground/60 text-sm mt-1">Track your collection value and P&L</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={refreshPrices} isLoading={isRefreshing}>
              <RefreshCw className="w-4 h-4 mr-1" /> Refresh
            </Button>
            <Button onClick={() => setShowAddForm(!showAddForm)}>
              <Plus className="w-4 h-4 mr-1" /> Add Item
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card variant="elevated">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg bg-accent-muted"><DollarSign className="w-4 h-4 text-accent" /></div>
                <span className="text-xs text-muted">Total Value</span>
              </div>
              <p className="text-2xl font-mono-numbers font-bold">${formatPrice(totalValue)}</p>
            </CardContent>
          </Card>
          <Card variant={totalGain >= 0 ? 'accent' : 'danger'}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg bg-success-muted">
                  {totalGain >= 0 ? <TrendingUp className="w-4 h-4 text-success" /> : <TrendingDown className="w-4 h-4 text-danger" />}
                </div>
                <span className="text-xs text-muted">Gain/Loss</span>
              </div>
              <p className={`text-2xl font-mono-numbers font-bold ${totalGain >= 0 ? 'text-success' : 'text-danger'}`}>
                {totalGain >= 0 ? '+' : ''}${formatPrice(totalGain)}
              </p>
            </CardContent>
          </Card>
          <Card variant="elevated">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg bg-info-muted"><Package className="w-4 h-4 text-info" /></div>
                <span className="text-xs text-muted">Items</span>
              </div>
              <p className="text-2xl font-mono-numbers font-bold">{totalItems}</p>
            </CardContent>
          </Card>
          <Card variant="elevated">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg bg-warning-muted"><PieIcon className="w-4 h-4 text-warning" /></div>
                <span className="text-xs text-muted">ROI</span>
              </div>
              <p className={`text-2xl font-mono-numbers font-bold ${roiPercent >= 0 ? 'text-success' : 'text-danger'}`}>
                {roiPercent >= 0 ? '+' : ''}{roiPercent.toFixed(1)}%
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Portfolio Chart */}
          <Card variant="elevated" className="lg:col-span-1">
            <CardHeader><CardTitle className="text-base">Breakdown</CardTitle></CardHeader>
            <CardContent>
              <div className="h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" paddingAngle={2}>
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) => [`$${formatPrice(value as number)}`, 'Value']}
                      contentStyle={{ background: '#0a1228', border: '1px solid #162550', borderRadius: '12px' }}
                      itemStyle={{ color: '#f1f5f9' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2 mt-2">
                {pieData.slice(0, 5).map((item, i) => (
                  <div key={item.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span className="text-muted truncate max-w-[140px]">{item.name}</span>
                    </div>
                    <span className="font-mono-numbers">${formatPrice(item.value)}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Portfolio Items */}
          <div className="lg:col-span-2">
            {showAddForm && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mb-4">
                <Card variant="elevated">
                  <CardHeader><CardTitle className="text-base">Add to Portfolio</CardTitle></CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                      <Input label="Card/Product Name" placeholder="e.g. Charizard ex SAR" />
                      <Select label="Grade" options={GRADE_TYPES.map(g => ({ value: g.value, label: g.label }))} />
                      <Input label="Cost Paid ($)" type="number" placeholder="89.50" />
                      <Input label="Current Price ($)" type="number" placeholder="Auto-fetched" />
                      <Input label="Quantity" type="number" placeholder="1" />
                    </div>
                    <div className="flex justify-end gap-3">
                      <Button variant="ghost" onClick={() => setShowAddForm(false)}>Cancel</Button>
                      <Button><Plus className="w-4 h-4 mr-1" /> Add</Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
              {portfolio.map((item) => {
                const gain = (item.currentPrice - item.costBasis) * item.quantity
                const gainPct = ((item.currentPrice - item.costBasis) / item.costBasis) * 100
                return (
                  <motion.div key={item.id} variants={staggerItem}>
                    <Card className="hover:border-border-light transition">
                      <CardContent className="p-4 flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-semibold truncate">{item.name}</p>
                            <Badge variant="default">{item.grade}</Badge>
                            {item.quantity > 1 && <Badge variant="info">x{item.quantity}</Badge>}
                          </div>
                          <div className="flex items-center gap-4 text-xs text-muted">
                            <span>Cost: ${formatPrice(item.costBasis * item.quantity)}</span>
                            <span>Current: ${formatPrice(item.currentPrice * item.quantity)}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 ml-4">
                          <div className="text-right">
                            <p className={`text-sm font-mono-numbers font-bold ${gain >= 0 ? 'text-success' : 'text-danger'}`}>
                              {gain >= 0 ? '+' : ''}${formatPrice(gain)}
                            </p>
                            <p className={`text-xs ${gainPct >= 0 ? 'text-success' : 'text-danger'}`}>
                              {gainPct >= 0 ? '+' : ''}{gainPct.toFixed(1)}%
                            </p>
                          </div>
                          <button
                            onClick={() => deleteItem(item.id)}
                            className="p-2 text-muted hover:text-danger transition rounded-lg hover:bg-danger-muted"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )
              })}
            </motion.div>
          </div>
        </div>
      </div>
    </PageTransition>
  )
}
