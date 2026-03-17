import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart3, ShoppingCart, Target, Crosshair,
  TrendingUp, DollarSign, Package, Layers, ArrowUpRight, ArrowDownRight,
  PieChart as PieIcon
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, AreaChart, Area
} from 'recharts'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { CHART_COLORS } from '@/lib/constants'
import { useCollection, usePortfolio, useStats } from '@/hooks/useApi'

const PIE_COLORS = ['#ef4444', '#818cf8', '#ef4444', '#22d3ee', '#a78bfa', '#67e8f9', '#f472b6']

type TimeRange = '7d' | '30d' | '90d' | 'all'

export default function Analytics() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d')

  // Real API hooks
  const { data: collectionData, isLoading: collLoading } = useCollection('default')
  const { data: portfolioData } = usePortfolio('default', timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90)
  const { data: statsData } = useStats()

  const items = collectionData?.items ?? []
  const summary = collectionData?.summary
  const history = portfolioData?.history ?? []

  // Compute analytics from real collection data
  const analytics = useMemo(() => {
    const totalValue = summary?.total_value ?? 0
    const totalCost = summary?.total_cost ?? 0
    const totalItems = summary?.total_items ?? items.length
    const gainLoss = summary?.gain_loss ?? (totalValue - totalCost)
    const roi = totalCost > 0 ? ((gainLoss / totalCost) * 100) : 0

    // Group items by condition for distribution
    const conditionDist: Record<string, number> = {}
    items.forEach(item => {
      const cond = item.condition || 'Unknown'
      conditionDist[cond] = (conditionDist[cond] || 0) + item.quantity
    })

    const conditionPie = Object.entries(conditionDist).map(([name, value]) => ({ name, value }))

    // Price distribution buckets
    const priceBuckets = [
      { range: '$0-5', min: 0, max: 5, count: 0 },
      { range: '$5-20', min: 5, max: 20, count: 0 },
      { range: '$20-50', min: 20, max: 50, count: 0 },
      { range: '$50-100', min: 50, max: 100, count: 0 },
      { range: '$100-250', min: 100, max: 250, count: 0 },
      { range: '$250+', min: 250, max: Infinity, count: 0 },
    ]
    items.forEach(item => {
      const price = (item.tcgplayer_market as number | undefined) ?? item.current_price ?? 0
      const bucket = priceBuckets.find(b => price >= b.min && price < b.max)
      if (bucket) bucket.count += item.quantity
    })

    // Top performers
    const performers = items
      .map(item => {
        const cost = (item.purchase_price ?? 0) * item.quantity
        const current = ((item.tcgplayer_market as number | undefined) ?? item.current_price ?? 0) * item.quantity
        const gain = current - cost
        const pct = cost > 0 ? ((gain / cost) * 100) : 0
        return { ...item, gain, pct, current, cost }
      })
      .sort((a, b) => b.gain - a.gain)

    const topGainers = performers.filter(p => p.gain > 0).slice(0, 5)
    const topLosers = performers.filter(p => p.gain < 0).sort((a, b) => a.gain - b.gain).slice(0, 5)

    // Value timeline — API returns recorded_at + total_value
    const timeline = history.map((h: any) => ({
      date: new Date(((h.recorded_at ?? h.date) || '') as string).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: ((h.total_value ?? h.value) || 0) as number,
    }))

    // Most valuable single items
    const mostValuable = [...items]
      .sort((a, b) => (((b.tcgplayer_market as number | undefined) ?? b.current_price ?? 0) * b.quantity) - (((a.tcgplayer_market as number | undefined) ?? a.current_price ?? 0) * a.quantity))
      .slice(0, 5)

    return {
      totalValue, totalCost, totalItems, gainLoss, roi,
      conditionPie, priceBuckets, topGainers, topLosers, timeline,
      mostValuable,
    }
  }, [items, summary, history])

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground gradient-text">Analytics</h1>
            <p className="text-muted-foreground/60 text-sm mt-1">Portfolio insights, performance tracking, and market analysis</p>
          </div>
          <div className="flex gap-1 p-1 bg-surface rounded-xl border border-border">
            {(['7d', '30d', '90d'] as TimeRange[]).map(range => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  timeRange === range
                    ? 'bg-accent text-white shadow-lg shadow-accent/25'
                    : 'text-muted hover:text-foreground hover:bg-surface-hover'
                }`}
              >
                {range.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* KPI Cards */}
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="grid grid-cols-2 md:grid-cols-5 gap-4"
        >
          {[
            { label: 'Portfolio Value', value: `$${formatPrice(analytics.totalValue)}`, icon: DollarSign, color: 'accent' },
            { label: 'Total Cost', value: `$${formatPrice(analytics.totalCost)}`, icon: ShoppingCart, color: 'info' },
            {
              label: 'P&L',
              value: `${analytics.gainLoss >= 0 ? '+' : ''}$${formatPrice(Math.abs(analytics.gainLoss))}`,
              icon: analytics.gainLoss >= 0 ? TrendingUp : ArrowDownRight,
              color: analytics.gainLoss >= 0 ? 'success' : 'danger'
            },
            {
              label: 'ROI',
              value: `${analytics.roi >= 0 ? '+' : ''}${analytics.roi.toFixed(1)}%`,
              icon: Target,
              color: analytics.roi >= 0 ? 'success' : 'danger'
            },
            { label: 'Total Items', value: String(analytics.totalItems), icon: Package, color: 'warning' },
          ].map(stat => (
            <motion.div key={stat.label} variants={staggerItem}>
              <Card variant="elevated" className="stat-card-hover hover-lift border-beam">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`p-1.5 rounded-lg bg-${stat.color}-muted`}>
                      <stat.icon className={`w-4 h-4 text-${stat.color}`} />
                    </div>
                    <span className="text-xs text-muted">{stat.label}</span>
                  </div>
                  <p className={`text-xl font-mono-numbers font-bold kpi-value ${
                    stat.label === 'P&L' ? (analytics.gainLoss >= 0 ? 'text-glow-green' : '') :
                    stat.label === 'ROI' ? (analytics.roi >= 0 ? 'text-glow-green' : '') : ''
                  }`}>{stat.value}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Value Over Time */}
          <Card variant="elevated" className="chart-glow">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-accent" />
                Portfolio Value
              </CardTitle>
            </CardHeader>
            <CardContent>
              {analytics.timeline.length > 0 ? (
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={analytics.timeline}>
                      <defs>
                        <linearGradient id="analyticsGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                      <XAxis dataKey="date" stroke={CHART_COLORS.text} fontSize={10} tickLine={false} axisLine={false} />
                      <YAxis stroke={CHART_COLORS.text} fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v: number) => `$${v}`} />
                      <Tooltip
                        contentStyle={{ background: '#0a1228', border: '1px solid #162550', borderRadius: '12px' }}
                        itemStyle={{ color: '#f1f5f9' }}
                        formatter={(v) => [`$${formatPrice(v as number)}`, 'Value']}
                      />
                      <Area type="monotone" dataKey="value" stroke="#ef4444" fill="url(#analyticsGrad)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[260px] flex items-center justify-center text-muted text-sm">
                  <div className="text-center">
                    <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p>No history data yet</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Price Distribution */}
          <Card variant="elevated" className="chart-glow">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent" />
                Price Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analytics.priceBuckets}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                    <XAxis dataKey="range" stroke={CHART_COLORS.text} fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis stroke={CHART_COLORS.text} fontSize={10} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#0a1228', border: '1px solid #162550', borderRadius: '12px' }}
                      itemStyle={{ color: '#f1f5f9' }}
                      formatter={(v) => [v, 'Cards']}
                    />
                    <Bar dataKey="count" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Second Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Condition Distribution */}
          <Card variant="elevated" className="chart-glow hover-lift">
            <CardHeader>
              <CardTitle className="text-base">Condition Mix</CardTitle>
            </CardHeader>
            <CardContent>
              {analytics.conditionPie.length > 0 ? (
                <>
                  <div className="h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={analytics.conditionPie} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" paddingAngle={2}>
                          {analytics.conditionPie.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                        </Pie>
                        <Tooltip
                          contentStyle={{ background: '#0a1228', border: '1px solid #162550', borderRadius: '12px' }}
                          itemStyle={{ color: '#f1f5f9' }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="space-y-2">
                    {analytics.conditionPie.map((item, i) => (
                      <div key={item.name} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <div className="w-2.5 h-2.5 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                          <span className="text-muted">{item.name}</span>
                        </div>
                        <span className="font-mono-numbers font-bold">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="h-[200px] flex items-center justify-center text-muted text-sm">
                  <div className="text-center">
                    <PieIcon className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p>No items to analyze</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Top Gainers */}
          <Card variant="elevated" className="hover-lift">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <ArrowUpRight className="w-4 h-4 text-success" />
                <span className="gradient-text">Top Gainers</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {analytics.topGainers.length > 0 ? (
                <div className="space-y-3">
                  {analytics.topGainers.map((item, i) => (
                    <motion.div
                      key={item.card_id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover/50 transition"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs font-mono text-muted w-5">{i + 1}.</span>
                        <span className="text-sm font-medium truncate">{(item.card_name as string) || item.card_id}</span>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-mono-numbers font-bold text-success text-glow-green">
                          +${formatPrice(item.gain)}
                        </p>
                        <p className="text-[10px] text-success">+{item.pct.toFixed(1)}%</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="h-[200px] flex items-center justify-center text-muted text-sm">
                  <p>No gains yet</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Most Valuable */}
          <Card variant="elevated" className="hover-lift">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-accent" />
                Most Valuable
              </CardTitle>
            </CardHeader>
            <CardContent>
              {analytics.mostValuable.length > 0 ? (
                <div className="space-y-3">
                  {analytics.mostValuable.map((item, i) => (
                    <motion.div
                      key={item.card_id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-hover/50 transition"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs font-mono text-muted w-5">{i + 1}.</span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{(item.card_name as string) || item.card_id}</p>
                          <p className="text-[10px] text-muted">{item.condition} {item.quantity > 1 ? `x${item.quantity}` : ''}</p>
                        </div>
                      </div>
                      <span className="text-sm font-mono-numbers font-bold text-accent">
                        ${formatPrice(((item.tcgplayer_market as number | undefined) ?? item.current_price ?? 0) * item.quantity)}
                      </span>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="h-[200px] flex items-center justify-center text-muted text-sm">
                  <p>No items to show</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* System Stats from API */}
        {statsData && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Crosshair className="w-4 h-4 text-accent" />
                  <span className="gradient-text">System Stats</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(statsData.collections || {}).map(([key, value]) => (
                    <div key={key} className="p-3 rounded-lg bg-surface border border-border hover-lift stat-card-hover">
                      <p className="text-xs text-muted capitalize">{key.replace(/_/g, ' ')}</p>
                      <p className="text-lg font-mono-numbers font-bold mt-1 kpi-value">
                        {typeof value === 'number' ? formatPrice(value) : String(value)}
                      </p>
                    </div>
                  ))}
                  {Object.entries(statsData.alerts || {}).map(([key, value]) => (
                    <div key={key} className="p-3 rounded-lg bg-surface border border-border hover-lift stat-card-hover">
                      <p className="text-xs text-muted capitalize">{key.replace(/_/g, ' ')}</p>
                      <p className="text-lg font-mono-numbers font-bold mt-1 kpi-value">
                        {typeof value === 'number' ? formatPrice(value) : String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Empty state */}
        {!collLoading && items.length === 0 && (
          <Card variant="elevated">
            <CardContent className="p-12 text-center">
              <BarChart3 className="w-12 h-12 mx-auto mb-3 text-muted opacity-40" />
              <h3 className="text-lg font-semibold mb-1">No Data to Analyze</h3>
              <p className="text-sm text-muted">Add items to your portfolio to see analytics and performance insights</p>
            </CardContent>
          </Card>
        )}
      </div>
    </PageTransition>
  )
}
