import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  PieChart as PieIcon, Plus, RefreshCw, Trash2, TrendingUp, TrendingDown,
  DollarSign, Package, CheckCircle, Search, BarChart3, Layers,
  Target, Award, AlertCircle
} from 'lucide-react'
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, AreaChart, Area,
  XAxis, YAxis, CartesianGrid
} from 'recharts'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { CHART_COLORS } from '@/lib/constants'
import {
  useCollection, usePortfolio, useAddToCollection,
  useRemoveFromCollection, useSets, useChaseCards
} from '@/hooks/useApi'
import { useQueryClient } from '@tanstack/react-query'

const PIE_COLORS = ['#ef4444', '#818cf8', '#ef4444', '#22d3ee', '#a78bfa', '#67e8f9', '#f472b6', '#fb923c']

type Tab = 'holdings' | 'completion' | 'history'

export default function Portfolio() {
  const [activeTab, setActiveTab] = useState<Tab>('holdings')
  const [showAddForm, setShowAddForm] = useState(false)
  const [selectedCompletionSet, setSelectedCompletionSet] = useState('')
  const [addForm, setAddForm] = useState({ card_id: '', quantity: '1', condition: 'NM', purchase_price: '' })

  const queryClient = useQueryClient()

  // Real API hooks
  const { data: collectionData, isLoading: collectionLoading, isError: collectionError } = useCollection('default')
  const { data: portfolioData } = usePortfolio('default', 90)
  const { data: setsData } = useSets()
  const addMutation = useAddToCollection('default')
  const removeMutation = useRemoveFromCollection('default')

  // For collection completion
  const { data: completionCardsData } = useChaseCards(selectedCompletionSet, undefined, 500)

  // Compute portfolio from real data or fallback
  const items = collectionData?.items ?? []
  const summary = collectionData?.summary
  const history = portfolioData?.history ?? []

  const totalValue = summary?.total_value ?? items.reduce((s, i) => s + (i.current_price ?? 0) * i.quantity, 0)
  const totalCost = summary?.total_cost ?? items.reduce((s, i) => s + (i.purchase_price ?? 0) * i.quantity, 0)
  const totalGain = summary?.gain_loss ?? (totalValue - totalCost)
  const totalItems = items.reduce((s, i) => s + i.quantity, 0)
  const roiPercent = totalCost > 0 ? ((totalGain / totalCost) * 100) : 0

  const pieData = items.slice(0, 8).map(item => ({
    name: item.card_id,
    value: (item.current_price ?? 0) * item.quantity,
  })).filter(d => d.value > 0)

  const chartData = history.map(h => ({
    date: new Date(h.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: h.value,
  }))

  // Collection Completion computation
  const sets = setsData?.data ?? []
  const completionCards = completionCardsData?.data ?? []
  const ownedCardIds = new Set(items.map(i => i.card_id))

  const completionStats = useMemo(() => {
    if (!selectedCompletionSet || completionCards.length === 0) return null
    const totalInSet = completionCards.length
    const owned = completionCards.filter(c => ownedCardIds.has(c.id)).length
    const missing = completionCards.filter(c => !ownedCardIds.has(c.id))
    const costToComplete = missing.reduce((sum, c) => sum + (c.price ?? 0), 0)

    // Group by rarity
    const rarityGroups: Record<string, { total: number; owned: number }> = {}
    completionCards.forEach(c => {
      const r = c.rarity || 'Unknown'
      if (!rarityGroups[r]) rarityGroups[r] = { total: 0, owned: 0 }
      rarityGroups[r].total++
      if (ownedCardIds.has(c.id)) rarityGroups[r].owned++
    })

    return { totalInSet, owned, missing, costToComplete, rarityGroups, pct: totalInSet > 0 ? (owned / totalInSet) * 100 : 0 }
  }, [selectedCompletionSet, completionCards, ownedCardIds])

  const refreshPrices = () => {
    queryClient.invalidateQueries({ queryKey: ['collection'] })
    queryClient.invalidateQueries({ queryKey: ['portfolio'] })
  }

  const handleAdd = () => {
    if (!addForm.card_id.trim()) return
    addMutation.mutate({
      card_id: addForm.card_id,
      quantity: parseInt(addForm.quantity) || 1,
      condition: addForm.condition,
      purchase_price: addForm.purchase_price ? parseFloat(addForm.purchase_price) : undefined,
    }, {
      onSuccess: () => {
        setAddForm({ card_id: '', quantity: '1', condition: 'NM', purchase_price: '' })
        setShowAddForm(false)
      }
    })
  }

  const handleRemove = (cardId: string, condition?: string) => {
    removeMutation.mutate({ cardId, condition })
  }

  const tabs: { id: Tab; label: string; icon: typeof Package }[] = [
    { id: 'holdings', label: 'Holdings', icon: Package },
    { id: 'completion', label: 'Set Completion', icon: CheckCircle },
    { id: 'history', label: 'Value History', icon: BarChart3 },
  ]

  return (
    <PageTransition>
      <div className="space-y-6 py-6">
        {/* ── Header — editorial ── */}
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-muted">
              Your book
            </div>
            <h1 className="font-display text-4xl sm:text-5xl leading-none tracking-tight-er mt-2">
              Portfolio
              <span className="italic text-accent"> · {totalItems} </span>
              <span className="font-mono-numbers text-muted">{totalItems === 1 ? 'item' : 'items'}</span>
            </h1>
          </div>
          <div className="flex gap-2">
            <button onClick={refreshPrices} className="btn btn-outline">
              <RefreshCw className={`w-3.5 h-3.5 ${collectionLoading ? 'animate-spin' : ''}`} /> Refresh
            </button>
            <button onClick={() => setShowAddForm(!showAddForm)} className="btn btn-primary">
              <Plus className="w-3.5 h-3.5" /> Add holding
            </button>
          </div>
        </div>

        {/* ── KPI strip ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border rounded overflow-hidden">
          {[
            { label: 'Total Value', value: `$${formatPrice(totalValue)}`, tone: 'neutral' as const, sub: 'current market' },
            { label: 'Cost Basis', value: `$${formatPrice(totalCost)}`, tone: 'neutral' as const, sub: 'amount invested' },
            {
              label: 'Gain / Loss',
              value: `${totalGain >= 0 ? '+' : '-'}$${formatPrice(Math.abs(totalGain))}`,
              tone: totalGain >= 0 ? 'up' as const : 'down' as const,
              sub: 'unrealised',
            },
            {
              label: 'ROI',
              value: `${roiPercent >= 0 ? '+' : ''}${roiPercent.toFixed(1)}%`,
              tone: roiPercent >= 0 ? 'up' as const : 'down' as const,
              sub: 'cumulative',
            },
          ].map((s) => (
            <div key={s.label} className="bg-background p-5 panel-hover">
              <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted">
                {s.label}
              </div>
              <div className={`font-mono-numbers text-3xl mt-2 leading-none ${
                s.tone === 'up' ? 'delta-up' : s.tone === 'down' ? 'delta-down' : 'text-foreground'
              }`}>
                {s.value}
              </div>
              <div className="text-[11px] text-muted mt-2">{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 p-1 bg-surface rounded-xl border border-border w-fit">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-accent text-white shadow-lg shadow-accent/25'
                  : 'text-muted hover:text-foreground hover:bg-surface-hover'
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Add Form */}
        <AnimatePresence>
          {showAddForm && (
            <motion.div
              initial={{ opacity: 0, height: 0, marginTop: 0 }}
              animate={{ opacity: 1, height: 'auto', marginTop: 24 }}
              exit={{ opacity: 0, height: 0, marginTop: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
              <Card variant="elevated">
                <CardHeader><CardTitle className="text-base">Add to Portfolio</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <Input
                      label="Card ID"
                      placeholder="e.g. sv8-123"
                      value={addForm.card_id}
                      onChange={(e) => setAddForm(f => ({ ...f, card_id: e.target.value }))}
                    />
                    <Select
                      label="Condition"
                      value={addForm.condition}
                      onChange={(e) => setAddForm(f => ({ ...f, condition: e.target.value }))}
                      options={[
                        { value: 'NM', label: 'Near Mint' },
                        { value: 'LP', label: 'Lightly Played' },
                        { value: 'MP', label: 'Moderately Played' },
                        { value: 'HP', label: 'Heavily Played' },
                      ]}
                    />
                    <Input
                      label="Purchase Price ($)"
                      type="number"
                      placeholder="89.50"
                      value={addForm.purchase_price}
                      onChange={(e) => setAddForm(f => ({ ...f, purchase_price: e.target.value }))}
                    />
                    <Input
                      label="Quantity"
                      type="number"
                      placeholder="1"
                      value={addForm.quantity}
                      onChange={(e) => setAddForm(f => ({ ...f, quantity: e.target.value }))}
                    />
                  </div>
                  <div className="flex justify-end gap-3">
                    <Button variant="ghost" onClick={() => setShowAddForm(false)}>Cancel</Button>
                    <Button onClick={handleAdd} isLoading={addMutation.isPending}>
                      <Plus className="w-4 h-4 mr-1" /> Add
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Holdings Tab */}
        {activeTab === 'holdings' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Pie Chart */}
            <Card variant="elevated" className="lg:col-span-1 chart-glow">
              <CardHeader><CardTitle className="text-base">Breakdown</CardTitle></CardHeader>
              <CardContent>
                {pieData.length > 0 ? (
                  <>
                    <div className="h-[240px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" paddingAngle={2}>
                            {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
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
                      {pieData.slice(0, 6).map((item, i) => (
                        <div key={item.name} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                            <span className="text-muted truncate max-w-[140px]">{item.name}</span>
                          </div>
                          <span className="font-mono-numbers">${formatPrice(item.value)}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="h-[240px] flex items-center justify-center text-muted text-sm">
                    <div className="text-center">
                      <Package className="w-8 h-8 mx-auto mb-2 opacity-40" />
                      <p>Add items to see breakdown</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Portfolio Items */}
            <div className="lg:col-span-2">
              {collectionLoading ? (
                <div className="space-y-3">
                  {[1,2,3].map(i => (
                    <div key={i} className="h-20 rounded-xl bg-surface animate-pulse border border-border" />
                  ))}
                </div>
              ) : items.length === 0 ? (
                <Card variant="elevated">
                  <CardContent className="p-12 text-center">
                    <Layers className="w-12 h-12 mx-auto mb-3 text-muted opacity-40" />
                    <h3 className="text-lg font-semibold mb-1">No items yet</h3>
                    <p className="text-sm text-muted mb-4">Add cards or sealed products to start tracking your portfolio</p>
                    <Button onClick={() => setShowAddForm(true)}>
                      <Plus className="w-4 h-4 mr-1" /> Add Your First Item
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
                  {items.map((item) => {
                    const cost = (item.purchase_price ?? 0) * item.quantity
                    const current = (item.current_price ?? 0) * item.quantity
                    const gain = current - cost
                    const gainPct = cost > 0 ? ((gain / cost) * 100) : 0
                    return (
                      <motion.div key={`${item.card_id}-${item.condition}`} variants={staggerItem}>
                        <Card className="hover:border-border-light transition group hover-lift holo-shine">
                          <CardContent className="p-4 flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <p className="font-semibold truncate">{item.card_id}</p>
                                <Badge variant="default">{item.condition}</Badge>
                                {item.quantity > 1 && <Badge variant="info">x{item.quantity}</Badge>}
                              </div>
                              <div className="flex items-center gap-4 text-xs text-muted">
                                <span>Cost: ${formatPrice(cost)}</span>
                                <span>Current: ${formatPrice(current)}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-4 ml-4">
                              <div className="text-right">
                                <p className={`text-sm font-mono-numbers font-bold ${gain >= 0 ? 'text-success' : 'text-danger'}`}>
                                  {gain >= 0 ? '+' : ''}${formatPrice(Math.abs(gain))}
                                </p>
                                <p className={`text-xs ${gainPct >= 0 ? 'text-success' : 'text-danger'}`}>
                                  {gainPct >= 0 ? '+' : ''}{gainPct.toFixed(1)}%
                                </p>
                              </div>
                              <button
                                onClick={() => handleRemove(item.card_id, item.condition)}
                                className="p-2 text-muted hover:text-danger transition rounded-lg hover:bg-danger-muted opacity-0 group-hover:opacity-100"
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
              )}
            </div>
          </motion.div>
        )}

        {/* Collection Completion Tab */}
        {activeTab === 'completion' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="space-y-6"
          >
            {/* Set Selector */}
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Target className="w-4 h-4 text-accent" />
                  Set Completion Tracker
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4 items-end">
                  <div className="flex-1">
                    <Select
                      label="Select a Set"
                      value={selectedCompletionSet}
                      onChange={(e) => setSelectedCompletionSet(e.target.value)}
                      options={[
                        { value: '', label: 'Choose a set...' },
                        ...sets.map(s => ({
                          value: s.id,
                          label: `${s.name} (${s.total_cards ?? '?'} cards)`
                        }))
                      ]}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {completionStats && (
              <>
                {/* Completion Overview */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                >
                  <Card variant="elevated" className="gradient-border">
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-lg font-bold">
                            {completionStats.owned} / {completionStats.totalInSet} Cards
                          </h3>
                          <p className="text-sm text-muted">
                            {completionStats.pct.toFixed(1)}% Complete
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-muted">Cost to Complete</p>
                          <p className="text-xl font-mono-numbers font-bold text-accent">
                            ${formatPrice(completionStats.costToComplete)}
                          </p>
                        </div>
                      </div>

                      <div className="relative h-4 rounded-full bg-surface overflow-hidden border border-border">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${completionStats.pct}%` }}
                          transition={{ type: 'spring', stiffness: 100, damping: 20, delay: 0.2 }}
                          className={`absolute inset-y-0 left-0 rounded-full ${
                            completionStats.pct >= 90 ? 'bg-gradient-to-r from-success to-red-400' :
                            completionStats.pct >= 50 ? 'bg-gradient-to-r from-accent to-blue-400' :
                            'bg-gradient-to-r from-warning to-amber-400'
                          }`}
                        />
                      </div>

                      {completionStats.pct >= 100 && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="mt-4 p-3 rounded-lg bg-success-muted border border-success/20 text-center"
                        >
                          <Award className="w-6 h-6 text-success mx-auto mb-1" />
                          <p className="text-sm font-bold text-success">Set Complete!</p>
                        </motion.div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Rarity Breakdown */}
                <Card variant="elevated">
                  <CardHeader>
                    <CardTitle className="text-base">Rarity Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {Object.entries(completionStats.rarityGroups)
                      .sort((a, b) => b[1].total - a[1].total)
                      .map(([rarity, data], i) => {
                        const pct = data.total > 0 ? (data.owned / data.total) * 100 : 0
                        return (
                          <motion.div
                            key={rarity}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="space-y-1.5"
                          >
                            <div className="flex items-center justify-between text-sm">
                              <span className="font-medium">{rarity}</span>
                              <div className="flex items-center gap-3 text-xs">
                                <span className="text-muted">{data.owned}/{data.total}</span>
                                <span className="font-mono-numbers font-bold">{pct.toFixed(0)}%</span>
                              </div>
                            </div>
                            <div className="relative h-2 rounded-full bg-surface overflow-hidden border border-border">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${pct}%` }}
                                transition={{ type: 'spring', stiffness: 100, damping: 20, delay: 0.3 + i * 0.05 }}
                                className={`absolute inset-y-0 left-0 rounded-full ${
                                  pct >= 100 ? 'bg-success' : pct >= 50 ? 'bg-accent' : 'bg-warning'
                                }`}
                              />
                            </div>
                          </motion.div>
                        )
                      })}
                  </CardContent>
                </Card>

                {/* Missing Cards */}
                {completionStats.missing.length > 0 && (
                  <Card variant="elevated">
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-warning" />
                        Missing Cards ({completionStats.missing.length})
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                        {completionStats.missing
                          .sort((a, b) => (a.price ?? 999) - (b.price ?? 999))
                          .slice(0, 20)
                          .map((card, i) => (
                            <motion.div
                              key={card.id}
                              initial={{ opacity: 0, scale: 0.9 }}
                              animate={{ opacity: 1, scale: 1 }}
                              transition={{ delay: i * 0.02 }}
                              whileHover={{ scale: 1.05, y: -4 }}
                              className="relative group"
                            >
                              <div className="aspect-[2.5/3.5] rounded-xl overflow-hidden bg-surface border border-border group-hover:border-accent/50 transition-all">
                                {card.image_url ? (
                                  <img src={card.image_url} alt={card.name} className="w-full h-full object-cover" />
                                ) : (
                                  <div className="w-full h-full flex items-center justify-center text-xs text-muted p-2 text-center">
                                    {card.name}
                                  </div>
                                )}
                              </div>
                              <div className="mt-1.5">
                                <p className="text-xs font-medium truncate">{card.name}</p>
                                <div className="flex items-center justify-between">
                                  <span className="text-[10px] text-muted">#{card.number}</span>
                                  <span className="text-xs font-mono-numbers font-bold text-accent">
                                    {card.price ? `$${formatPrice(card.price)}` : '—'}
                                  </span>
                                </div>
                              </div>
                            </motion.div>
                          ))}
                      </div>
                      {completionStats.missing.length > 20 && (
                        <p className="text-xs text-muted text-center mt-4">
                          Showing 20 of {completionStats.missing.length} missing cards (sorted by price)
                        </p>
                      )}
                    </CardContent>
                  </Card>
                )}
              </>
            )}

            {!selectedCompletionSet && (
              <Card variant="elevated">
                <CardContent className="p-12 text-center">
                  <Search className="w-12 h-12 mx-auto mb-3 text-muted opacity-40" />
                  <h3 className="text-lg font-semibold mb-1">Select a Set</h3>
                  <p className="text-sm text-muted">Choose a Pokemon TCG set above to track your completion progress</p>
                </CardContent>
              </Card>
            )}
          </motion.div>
        )}

        {/* Value History Tab */}
        {activeTab === 'history' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          >
            <Card variant="elevated" className="chart-glow">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-accent" />
                  Portfolio Value Over Time
                </CardTitle>
              </CardHeader>
              <CardContent>
                {chartData.length > 0 ? (
                  <div className="h-[350px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
                            <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                        <XAxis dataKey="date" stroke={CHART_COLORS.text} fontSize={11} tickLine={false} axisLine={false} />
                        <YAxis stroke={CHART_COLORS.text} fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v: number) => `$${v}`} />
                        <Tooltip
                          contentStyle={{ background: '#0a1228', border: '1px solid #162550', borderRadius: '12px' }}
                          itemStyle={{ color: '#f1f5f9' }}
                          formatter={(v) => [`$${formatPrice(v as number)}`, 'Value']}
                        />
                        <Area type="monotone" dataKey="value" stroke="#ef4444" fill="url(#portfolioGrad)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-[350px] flex items-center justify-center text-muted text-sm">
                    <div className="text-center">
                      <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-40" />
                      <p>No portfolio history data yet</p>
                      <p className="text-xs mt-1">Add items and check back later to see your portfolio trend</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Error State */}
        {collectionError && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="p-4 rounded-xl bg-warning-muted border border-warning/20 text-sm"
          >
            <p className="font-medium text-warning">Unable to load collection data</p>
            <p className="text-muted mt-1">Using offline mode. The API may be unavailable — try refreshing in a moment.</p>
          </motion.div>
        )}
      </div>
    </PageTransition>
  )
}
