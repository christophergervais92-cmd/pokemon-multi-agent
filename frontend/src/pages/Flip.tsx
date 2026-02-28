import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Calculator, Search, TrendingUp, TrendingDown,
  CheckCircle, XCircle, DollarSign, ArrowRight,
  Scale, Truck, Shield, BarChart3, Info,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { fadeInUp, staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { GRADING_COMPANIES } from '@/lib/constants'
import { useGradeCostEstimate } from '@/hooks/useApi'

/* ═══════════════════════════════════════════════════════
   Comprehensive Grading Company Data
   ═══════════════════════════════════════════════════════ */

interface ServiceTier {
  name: string
  cost: number
  turnaround: string
  maxValue?: number
}

interface GradeOutcome {
  grade: string
  label: string
  probability: number
  multiplier: number
  color: 'success' | 'warning' | 'danger' | 'accent' | 'info'
}

interface CompanyData {
  name: string
  key: string
  color: string
  bgColor: string
  tiers: ServiceTier[]
  grades: GradeOutcome[]
  shippingCost: number
  insuranceRate: number
  populationNotes: string
}

const COMPANY_DATA: Record<string, CompanyData> = {
  PSA: {
    name: 'PSA',
    key: 'PSA',
    color: '#ef4444',
    bgColor: 'bg-red-500/10 border-red-500/20',
    shippingCost: 15,
    insuranceRate: 0.01,
    populationNotes: 'Largest population reports — highest liquidity on eBay & TCGPlayer',
    tiers: [
      { name: 'Value', cost: 22, turnaround: '65 business days', maxValue: 499 },
      { name: 'Regular', cost: 50, turnaround: '30 business days', maxValue: 999 },
      { name: 'Express', cost: 100, turnaround: '15 business days', maxValue: 4999 },
      { name: 'Super Express', cost: 200, turnaround: '5 business days', maxValue: 9999 },
      { name: 'Walk-Through', cost: 600, turnaround: '1 business day' },
    ],
    grades: [
      { grade: '10', label: 'Gem Mint', probability: 12, multiplier: 3.2, color: 'accent' },
      { grade: '9', label: 'Mint', probability: 35, multiplier: 1.8, color: 'success' },
      { grade: '8', label: 'NM-MT', probability: 30, multiplier: 1.3, color: 'success' },
      { grade: '7', label: 'NM', probability: 15, multiplier: 1.05, color: 'warning' },
      { grade: '6 or below', label: 'EX or lower', probability: 8, multiplier: 0.7, color: 'danger' },
    ],
  },
  BGS: {
    name: 'BGS (Beckett)',
    key: 'BGS',
    color: '#a855f7',
    bgColor: 'bg-purple-500/10 border-purple-500/20',
    shippingCost: 18,
    insuranceRate: 0.01,
    populationNotes: 'Sub-grades (centering, edges, corners, surface) — Black Label 10 commands massive premiums',
    tiers: [
      { name: 'Economy', cost: 22, turnaround: '60 business days', maxValue: 249 },
      { name: 'Standard', cost: 40, turnaround: '45 business days', maxValue: 999 },
      { name: 'Express', cost: 100, turnaround: '10 business days', maxValue: 4999 },
      { name: 'Premium', cost: 250, turnaround: '5 business days' },
    ],
    grades: [
      { grade: 'Black Label 10', label: 'Pristine (all 10s)', probability: 2, multiplier: 5.0, color: 'accent' },
      { grade: '10', label: 'Pristine', probability: 8, multiplier: 3.5, color: 'accent' },
      { grade: '9.5', label: 'Gem Mint', probability: 25, multiplier: 2.2, color: 'success' },
      { grade: '9', label: 'Mint', probability: 35, multiplier: 1.5, color: 'success' },
      { grade: '8.5', label: 'NM-MT+', probability: 18, multiplier: 1.15, color: 'warning' },
      { grade: '8 or below', label: 'NM-MT or lower', probability: 12, multiplier: 0.8, color: 'danger' },
    ],
  },
  CGC: {
    name: 'CGC',
    key: 'CGC',
    color: '#3b82f6',
    bgColor: 'bg-blue-500/10 border-blue-500/20',
    shippingCost: 12,
    insuranceRate: 0.01,
    populationNotes: 'Growing market share — sub-grades available — often faster turnaround than PSA',
    tiers: [
      { name: 'Economy', cost: 15, turnaround: '85 business days', maxValue: 249 },
      { name: 'Standard', cost: 25, turnaround: '45 business days', maxValue: 499 },
      { name: 'Express', cost: 65, turnaround: '10 business days', maxValue: 999 },
      { name: 'Walk-Through', cost: 250, turnaround: '2 business days' },
    ],
    grades: [
      { grade: '10 Perfect', label: 'Perfect', probability: 3, multiplier: 4.0, color: 'accent' },
      { grade: '10', label: 'Pristine', probability: 10, multiplier: 2.8, color: 'accent' },
      { grade: '9.5', label: 'Gem Mint', probability: 28, multiplier: 1.9, color: 'success' },
      { grade: '9', label: 'Mint', probability: 32, multiplier: 1.4, color: 'success' },
      { grade: '8.5', label: 'NM-MT+', probability: 17, multiplier: 1.1, color: 'warning' },
      { grade: '8 or below', label: 'NM-MT or lower', probability: 10, multiplier: 0.75, color: 'danger' },
    ],
  },
}

/* ═══════════════════════════════════════════════════════ */

export default function Flip() {
  const [cardName, setCardName] = useState('')
  const [rawPrice, setRawPrice] = useState('')
  const [company, setCompany] = useState('PSA')
  const [tierIdx, setTierIdx] = useState(0)
  const [showResults, setShowResults] = useState(false)
  const [isCalculating, setIsCalculating] = useState(false)

  const costEstimate = useGradeCostEstimate()

  const companyInfo = COMPANY_DATA[company]
  const selectedTier = companyInfo.tiers[tierIdx] || companyInfo.tiers[0]
  const rawPriceNum = parseFloat(rawPrice) || 0

  // Build tier options
  const tierOptions = companyInfo.tiers.map((t, i) => ({
    value: String(i),
    label: `${t.name} — $${t.cost} (${t.turnaround})${t.maxValue ? ` · Max $${t.maxValue}` : ''}`,
  }))

  // Calculations
  const gradingCost = selectedTier.cost
  const shippingCost = companyInfo.shippingCost
  const insuranceCost = rawPriceNum > 100 ? Math.ceil(rawPriceNum * companyInfo.insuranceRate) : 0
  const totalCost = rawPriceNum + gradingCost + shippingCost + insuranceCost

  const gradeOutcomes = useMemo(() => {
    return companyInfo.grades.map((g) => {
      const gradedValue = rawPriceNum * g.multiplier
      const profit = gradedValue - totalCost
      return { ...g, gradedValue, profit }
    })
  }, [companyInfo, rawPriceNum, totalCost])

  const expectedValue = gradeOutcomes.reduce(
    (sum, g) => sum + (g.gradedValue * g.probability) / 100,
    0
  )
  const expectedROI = expectedValue - totalCost
  const roiPercent = totalCost > 0 ? (expectedROI / totalCost) * 100 : 0

  const breakEvenGrade = gradeOutcomes.find((g) => g.profit > 0)

  // Cross-company comparison
  const crossCompanyComparison = useMemo(() => {
    if (rawPriceNum <= 0) return []
    return Object.values(COMPANY_DATA).map((co) => {
      const cheapestTier = co.tiers[0]
      const total = rawPriceNum + cheapestTier.cost + co.shippingCost
      const ev = co.grades.reduce(
        (sum, g) => sum + (rawPriceNum * g.multiplier * g.probability) / 100,
        0
      )
      const roi = ev - total
      const roiPct = total > 0 ? (roi / total) * 100 : 0
      const topGrade = co.grades[0]
      return {
        name: co.name,
        key: co.key,
        color: co.color,
        bgColor: co.bgColor,
        cheapestCost: cheapestTier.cost,
        turnaround: cheapestTier.turnaround,
        shippingCost: co.shippingCost,
        totalCost: total,
        expectedValue: ev,
        roi,
        roiPercent: roiPct,
        topGradeMultiplier: topGrade.multiplier,
        topGradeLabel: `${co.key} ${topGrade.grade}`,
        topGradeProbability: topGrade.probability,
      }
    })
  }, [rawPriceNum])

  const handleCalculate = () => {
    if (rawPriceNum <= 0) return
    setIsCalculating(true)
    // Also call real API for cost estimate
    costEstimate.mutate(
      { cardValue: rawPriceNum, estimatedGrade: 9 },
      {
        onSettled: () => {
          setShowResults(true)
          setIsCalculating(false)
        },
      }
    )
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">
            Flip Calculator
          </h1>
          <p className="text-muted-foreground/60 text-sm mt-1">
            Calculate your ROI for grading cards — full PSA, BGS &amp; CGC analysis
          </p>
        </div>

        {/* ── Input Form ── */}
        <Card variant="elevated">
          <CardContent className="p-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="sm:col-span-2 lg:col-span-1">
                <Input
                  label="Card Name"
                  placeholder="e.g. Charizard ex"
                  value={cardName}
                  onChange={(e) => setCardName(e.target.value)}
                  icon={<Search className="w-4 h-4" />}
                />
              </div>
              <div>
                <Input
                  label="Raw Price ($)"
                  type="number"
                  placeholder="89.50"
                  value={rawPrice}
                  onChange={(e) => setRawPrice(e.target.value)}
                  icon={<DollarSign className="w-4 h-4" />}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1.5">Grading Company</label>
                <div className="flex gap-1.5">
                  {Object.values(COMPANY_DATA).map((co) => (
                    <button
                      key={co.key}
                      onClick={() => { setCompany(co.key); setTierIdx(0) }}
                      className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all border ${
                        company === co.key
                          ? `${co.bgColor} text-foreground`
                          : 'border-transparent bg-surface text-muted hover:text-foreground'
                      }`}
                      style={company === co.key ? { borderColor: co.color + '40' } : undefined}
                    >
                      {co.key}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <Select
                  label="Service Tier"
                  value={String(tierIdx)}
                  onChange={(e) => setTierIdx(Number(e.target.value))}
                  options={tierOptions}
                />
              </div>
            </div>

            <div className="flex items-end gap-3">
              <Button className="w-full sm:w-auto" onClick={handleCalculate} isLoading={isCalculating}>
                <Calculator className="w-4 h-4 mr-1" /> Calculate ROI
              </Button>
              {rawPriceNum > 0 && (
                <p className="text-xs text-muted">
                  Total investment: <span className="font-mono-numbers text-foreground">${formatPrice(totalCost)}</span>
                  {' '}(Card ${formatPrice(rawPriceNum)} + Grading ${gradingCost} + Shipping ${shippingCost}{insuranceCost > 0 ? ` + Insurance $${insuranceCost}` : ''})
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* ── Results ── */}
        <AnimatePresence>
          {showResults && rawPriceNum > 0 && (
            <motion.div
              variants={fadeInUp}
              initial="initial"
              animate="animate"
              exit="exit"
              className="space-y-6"
            >
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Card variant="elevated">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-muted mb-1">Grading Cost</p>
                    <p className="text-xl font-mono-numbers font-bold">${gradingCost}</p>
                    <p className="text-[10px] text-muted mt-1">{companyInfo.name} · {selectedTier.name}</p>
                  </CardContent>
                </Card>
                <Card variant="elevated">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-muted mb-1">Total Investment</p>
                    <p className="text-xl font-mono-numbers font-bold">${formatPrice(totalCost)}</p>
                    <p className="text-[10px] text-muted mt-1">Card + grading + shipping</p>
                  </CardContent>
                </Card>
                <Card variant="elevated">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-muted mb-1">Expected Value</p>
                    <p className="text-xl font-mono-numbers font-bold text-accent">${formatPrice(expectedValue)}</p>
                    <p className="text-[10px] text-muted mt-1">Weighted avg</p>
                  </CardContent>
                </Card>
                <Card variant={expectedROI >= 0 ? 'accent' : 'danger'}>
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-muted mb-1">Expected ROI</p>
                    <p className={`text-xl font-mono-numbers font-bold ${expectedROI >= 0 ? 'text-success' : 'text-danger'}`}>
                      {expectedROI >= 0 ? '+' : ''}${formatPrice(expectedROI)}
                    </p>
                    <p className={`text-[10px] mt-1 ${roiPercent >= 0 ? 'text-success' : 'text-danger'}`}>
                      {roiPercent >= 0 ? '+' : ''}{roiPercent.toFixed(1)}%
                    </p>
                  </CardContent>
                </Card>
                <Card variant="elevated">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-muted mb-1">Break-Even</p>
                    <p className="text-xl font-mono-numbers font-bold">
                      {breakEvenGrade ? `${companyInfo.key} ${breakEvenGrade.grade}` : 'N/A'}
                    </p>
                    <p className="text-[10px] text-muted mt-1">Min profitable grade</p>
                  </CardContent>
                </Card>
              </div>

              {/* Grade Distribution */}
              <Card variant="elevated">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" style={{ color: companyInfo.color }} />
                    {companyInfo.name} Grade Distribution &amp; Outcomes
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {gradeOutcomes.map((g) => (
                    <div key={g.grade} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <Badge variant={g.color}>
                            {companyInfo.key} {g.grade}
                          </Badge>
                          <span className="text-xs text-muted hidden sm:inline">{g.label}</span>
                          <span className="text-muted text-xs">{g.probability}% chance</span>
                        </div>
                        <div className="flex items-center gap-4 font-mono-numbers text-xs sm:text-sm">
                          <span className="text-muted hidden sm:inline">
                            {g.multiplier}x
                          </span>
                          <span className="text-muted">
                            ${formatPrice(g.gradedValue)}
                          </span>
                          <span className={`font-bold ${g.profit >= 0 ? 'text-success' : 'text-danger'}`}>
                            {g.profit >= 0 ? '+' : ''}${formatPrice(g.profit)}
                          </span>
                        </div>
                      </div>
                      <Progress value={g.probability} color={g.color} />
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Cost Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Detailed Cost Breakdown */}
                <Card variant="elevated">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-accent" /> Cost Breakdown
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Raw Card Price</span>
                      <span className="font-mono-numbers">${formatPrice(rawPriceNum)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Grading ({selectedTier.name})</span>
                      <span className="font-mono-numbers">${gradingCost}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <div className="flex items-center gap-1 text-muted">
                        <Truck className="h-3.5 w-3.5" /> Shipping
                      </div>
                      <span className="font-mono-numbers">${companyInfo.shippingCost}</span>
                    </div>
                    {insuranceCost > 0 && (
                      <div className="flex justify-between text-sm">
                        <div className="flex items-center gap-1 text-muted">
                          <Shield className="h-3.5 w-3.5" /> Insurance ({(companyInfo.insuranceRate * 100).toFixed(0)}%)
                        </div>
                        <span className="font-mono-numbers">${insuranceCost}</span>
                      </div>
                    )}
                    <div className="border-t border-border pt-2 flex justify-between text-sm font-bold">
                      <span>Total Investment</span>
                      <span className="font-mono-numbers">${formatPrice(totalCost)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Turnaround</span>
                      <span className="text-foreground">{selectedTier.turnaround}</span>
                    </div>
                    {selectedTier.maxValue && (
                      <div className="flex justify-between text-sm">
                        <span className="text-muted">Max Declared Value</span>
                        <span className="text-foreground">${selectedTier.maxValue.toLocaleString()}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Service Tiers Comparison */}
                <Card variant="elevated">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Scale className="h-4 w-4 text-accent" /> {companyInfo.name} Service Tiers
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {companyInfo.tiers.map((t, i) => {
                        const tierTotal = rawPriceNum + t.cost + companyInfo.shippingCost
                        const tierEV = companyInfo.grades.reduce(
                          (sum, g) => sum + (rawPriceNum * g.multiplier * g.probability) / 100, 0
                        )
                        const tierROI = tierEV - tierTotal
                        const isSelected = i === tierIdx
                        return (
                          <button
                            key={t.name}
                            onClick={() => setTierIdx(i)}
                            className={`w-full text-left p-3 rounded-lg border transition-all text-sm ${
                              isSelected
                                ? `${companyInfo.bgColor} border-current`
                                : 'border-transparent hover:bg-surface-hover'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <span className="font-semibold">{t.name}</span>
                                <span className="text-xs text-muted ml-2">{t.turnaround}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="font-mono-numbers font-bold">${t.cost}</span>
                                {rawPriceNum > 0 && (
                                  <span className={`text-xs font-mono-numbers ${tierROI >= 0 ? 'text-success' : 'text-danger'}`}>
                                    {tierROI >= 0 ? '+' : ''}${formatPrice(tierROI)}
                                  </span>
                                )}
                              </div>
                            </div>
                            {t.maxValue && (
                              <p className="text-[10px] text-muted mt-0.5">Max declared value: ${t.maxValue.toLocaleString()}</p>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Cross-Company Comparison */}
              {crossCompanyComparison.length > 0 && (
                <Card variant="elevated">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <ArrowRight className="h-4 w-4 text-accent" /> Cross-Company Comparison
                      <span className="text-xs font-normal text-muted ml-1">(cheapest tier)</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <motion.div
                      className="grid grid-cols-1 md:grid-cols-3 gap-4"
                      variants={staggerContainer}
                      initial="initial"
                      animate="animate"
                    >
                      {crossCompanyComparison.map((co) => (
                        <motion.div key={co.key} variants={staggerItem}>
                          <div
                            className={`p-4 rounded-xl border space-y-3 ${co.bgColor} ${co.key === company ? 'ring-2 ring-offset-2 ring-offset-background' : ''}`}
                            style={co.key === company ? { ringColor: co.color } : undefined}
                          >
                            <div className="flex items-center justify-between">
                              <h4 className="font-bold text-foreground" style={{ color: co.color }}>{co.name}</h4>
                              {co.key === company && (
                                <Badge variant="accent" className="text-[10px]">Selected</Badge>
                              )}
                            </div>
                            <div className="space-y-1.5 text-sm">
                              <div className="flex justify-between">
                                <span className="text-muted">Grading</span>
                                <span className="font-mono-numbers">${co.cheapestCost}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted">Shipping</span>
                                <span className="font-mono-numbers">${co.shippingCost}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted">Total Cost</span>
                                <span className="font-mono-numbers font-bold">${formatPrice(co.totalCost)}</span>
                              </div>
                              <div className="border-t border-white/10 pt-1.5 flex justify-between">
                                <span className="text-muted">Expected Value</span>
                                <span className="font-mono-numbers text-accent">${formatPrice(co.expectedValue)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted">ROI</span>
                                <span className={`font-mono-numbers font-bold ${co.roi >= 0 ? 'text-success' : 'text-danger'}`}>
                                  {co.roi >= 0 ? '+' : ''}${formatPrice(co.roi)} ({co.roiPercent.toFixed(1)}%)
                                </span>
                              </div>
                            </div>
                            <div className="pt-1 text-xs text-muted">
                              <p>Top grade: {co.topGradeLabel} ({co.topGradeMultiplier}x, {co.topGradeProbability}% odds)</p>
                              <p className="mt-0.5">Turnaround: {co.turnaround}</p>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  </CardContent>
                </Card>
              )}

              {/* API Cost Estimate (if available) */}
              {costEstimate.data && (
                <Card variant="elevated">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Info className="h-4 w-4 text-accent" /> AI Cost Analysis
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                      {costEstimate.data.worth_grading !== undefined && (
                        <div className="text-center">
                          <p className="text-xs text-muted mb-1">Worth Grading?</p>
                          <Badge variant={costEstimate.data.worth_grading ? 'success' : 'danger'}>
                            {costEstimate.data.worth_grading ? 'Yes' : 'No'}
                          </Badge>
                        </div>
                      )}
                      {costEstimate.data.estimated_value != null && (
                        <div className="text-center">
                          <p className="text-xs text-muted mb-1">Estimated Graded Value</p>
                          <p className="font-mono-numbers font-bold text-accent">${formatPrice(costEstimate.data.estimated_value)}</p>
                        </div>
                      )}
                      {costEstimate.data.grading_cost != null && (
                        <div className="text-center">
                          <p className="text-xs text-muted mb-1">Grading Cost</p>
                          <p className="font-mono-numbers font-bold">${formatPrice(costEstimate.data.grading_cost)}</p>
                        </div>
                      )}
                      {costEstimate.data.roi != null && (
                        <div className="text-center">
                          <p className="text-xs text-muted mb-1">AI ROI Estimate</p>
                          <p className={`font-mono-numbers font-bold ${costEstimate.data.roi >= 0 ? 'text-success' : 'text-danger'}`}>
                            {costEstimate.data.roi >= 0 ? '+' : ''}{costEstimate.data.roi.toFixed(1)}%
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Recommendation */}
              <Card variant={expectedROI >= 0 ? 'accent' : 'danger'}>
                <CardContent className="p-6 flex items-center gap-4">
                  {expectedROI >= 0 ? (
                    <CheckCircle className="w-10 h-10 text-success shrink-0" />
                  ) : (
                    <XCircle className="w-10 h-10 text-danger shrink-0" />
                  )}
                  <div>
                    <h3 className="text-lg font-bold">
                      {expectedROI >= 0 ? 'Grade This Card' : 'Sell Raw'}
                    </h3>
                    <p className="text-sm text-muted mt-1">
                      {expectedROI >= 0
                        ? `With ${companyInfo.name} ${selectedTier.name} service, you have a positive expected ROI of $${formatPrice(expectedROI)} (${roiPercent.toFixed(1)}%). Break-even at ${companyInfo.key} ${breakEvenGrade?.grade || 'top grade'}. Consider ${crossCompanyComparison.reduce((best, co) => co.roi > best.roi ? co : best, crossCompanyComparison[0]).name} for best value.`
                        : `Grading with ${companyInfo.name} ${selectedTier.name} would result in an expected loss of $${formatPrice(Math.abs(expectedROI))}. Consider selling raw, trying a cheaper service tier, or waiting for price appreciation.`
                      }
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Quick Tips */}
              <Card>
                <CardContent className="p-5">
                  <h4 className="text-sm font-semibold mb-3">Grading Tips</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-muted">
                    <div>
                      <p className="font-medium text-foreground mb-1">PSA</p>
                      <p>{COMPANY_DATA.PSA.populationNotes}</p>
                    </div>
                    <div>
                      <p className="font-medium text-foreground mb-1">BGS</p>
                      <p>{COMPANY_DATA.BGS.populationNotes}</p>
                    </div>
                    <div>
                      <p className="font-medium text-foreground mb-1">CGC</p>
                      <p>{COMPANY_DATA.CGC.populationNotes}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  )
}
