import { useState, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload, Globe, Sparkles, AlertTriangle, X, AlertCircle,
  DollarSign, TrendingUp, Shield, Info, CheckCircle2,
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { DropZone } from '@/components/ui/DropZone'
import { EmptyState } from '@/components/ui/EmptyState'
import { Progress } from '@/components/ui/Progress'
import { Badge } from '@/components/ui/Badge'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { useGradeEstimate, useGradeCostEstimate } from '@/hooks/useApi'
import type { GradeEstimate } from '@/lib/api'

/* ═══════════════════════════════════════════════════════
   Grading reference data — comprehensive PSA/BGS/CGC
   ═══════════════════════════════════════════════════════ */

const GRADING_COMPANIES = [
  {
    id: 'PSA',
    name: 'PSA (Professional Sports Authenticator)',
    scale: '1–10',
    tiers: [
      { name: 'Value', cost: 22, turnaround: '65 business days', minValue: 0 },
      { name: 'Regular', cost: 50, turnaround: '30 business days', minValue: 100 },
      { name: 'Express', cost: 100, turnaround: '15 business days', minValue: 200 },
      { name: 'Super Express', cost: 200, turnaround: '5 business days', minValue: 500 },
      { name: 'Walk-Through', cost: 600, turnaround: '1 business day', minValue: 2500 },
    ],
    grades: ['10 (Gem Mint)', '9 (Mint)', '8 (NM-MT)', '7 (NM)', '6 (EX-MT)', '5 (Excellent)', '4 (VG-EX)', '3 (VG)', '2 (Good)', '1 (Poor)'],
    color: '#ef4444',
    multipliers: { '10': 3.2, '9': 2.1, '8': 1.4, '7': 1.0, '6': 0.8 },
  },
  {
    id: 'BGS',
    name: 'BGS (Beckett Grading Services)',
    scale: '1–10 with .5 increments',
    tiers: [
      { name: 'Economy', cost: 22, turnaround: '60+ business days', minValue: 0 },
      { name: 'Standard', cost: 40, turnaround: '45 business days', minValue: 0 },
      { name: 'Express', cost: 100, turnaround: '10 business days', minValue: 0 },
      { name: 'Premium', cost: 250, turnaround: '5 business days', minValue: 500 },
    ],
    grades: ['10 (Pristine)', '10 Black Label', '9.5 (Gem Mint)', '9 (Mint)', '8.5 (NM-MT+)', '8 (NM-MT)', '7.5 (NM+)', '7 (NM)'],
    color: '#a855f7',
    multipliers: { 'Black Label': 5.0, '10': 3.8, '9.5': 2.8, '9': 1.8, '8.5': 1.3, '8': 1.0 },
  },
  {
    id: 'CGC',
    name: 'CGC (Certified Guaranty Company)',
    scale: '1–10 with .5 increments',
    tiers: [
      { name: 'Economy', cost: 15, turnaround: '85 business days', minValue: 0 },
      { name: 'Standard', cost: 25, turnaround: '45 business days', minValue: 0 },
      { name: 'Express', cost: 65, turnaround: '10 business days', minValue: 0 },
      { name: 'Walk-Through', cost: 250, turnaround: '2 business days', minValue: 500 },
    ],
    grades: ['10 (Pristine)', '9.5 (Gem Mint)', '9 (Mint)', '8.5 (NM-MT+)', '8 (NM-MT)', '7.5 (NM+)', '7 (NM)'],
    color: '#22c55e',
    multipliers: { '10': 2.4, '9.5': 1.9, '9': 1.4, '8.5': 1.1, '8': 0.9 },
  },
]

const CONDITION_CHECKLIST = [
  { id: 'centering', label: 'Centering', description: 'Front and back borders are even and well-centered' },
  { id: 'corners', label: 'Corners', description: 'All four corners are sharp with no wear, dings, or peeling' },
  { id: 'edges', label: 'Edges', description: 'Clean edges with no whitening, chipping, or nicks' },
  { id: 'surface', label: 'Surface', description: 'No scratches, print lines, dents, or ink errors' },
]

const CENTERING_GUIDE = [
  { label: 'PSA 10 Centering', desc: '60/40 or better on front, 75/25 or better on back', badge: 'Gem Mint' },
  { label: 'PSA 9 Centering', desc: '65/35 or better on front, 90/10 or better on back', badge: 'Mint' },
  { label: 'PSA 8 Centering', desc: '70/30 or better on front, 90/10 or better on back', badge: 'NM-MT' },
]

function getGradeBorderColor(grade: number): string {
  if (grade >= 9.5) return 'border-emerald-400'
  if (grade >= 9.0) return 'border-accent'
  if (grade >= 8.0) return 'border-blue-400'
  if (grade >= 7.0) return 'border-amber-400'
  return 'border-rose-400'
}

function getGradeTextColor(grade: number): string {
  if (grade >= 9.5) return 'text-emerald-400'
  if (grade >= 9.0) return 'text-accent'
  if (grade >= 8.0) return 'text-blue-400'
  if (grade >= 7.0) return 'text-amber-400'
  return 'text-rose-400'
}

function getSubgradeColor(score: number): 'success' | 'accent' | 'warning' | 'danger' {
  if (score >= 9.5) return 'success'
  if (score >= 9.0) return 'accent'
  if (score >= 8.0) return 'warning'
  return 'danger'
}

function getGradeLabel(grade: number): string {
  if (grade >= 9.5) return 'Gem Mint'
  if (grade >= 9.0) return 'Mint'
  if (grade >= 8.0) return 'Near Mint'
  if (grade >= 7.0) return 'Near Mint'
  if (grade >= 6.0) return 'Excellent'
  return 'Good or Below'
}

export default function Grading() {
  const [imageUrl, setImageUrl] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [conditionNotes, setConditionNotes] = useState('')
  const [selectedCompany, setSelectedCompany] = useState('PSA')
  const [rawCardValue, setRawCardValue] = useState('')
  const [checklist, setChecklist] = useState<Record<string, boolean>>({})

  // Wire to real API
  const gradeEstimate = useGradeEstimate()
  const costEstimate = useGradeCostEstimate()
  const result = gradeEstimate.data as GradeEstimate | undefined
  const isAnalyzing = gradeEstimate.isPending

  const companyData = GRADING_COMPANIES.find(c => c.id === selectedCompany) ?? GRADING_COMPANIES[0]

  // Build comprehensive condition notes from checklist + free text
  const buildConditionNotes = useCallback(() => {
    const parts: string[] = []
    for (const item of CONDITION_CHECKLIST) {
      if (checklist[item.id]) {
        parts.push(`${item.label}: Good condition`)
      } else {
        parts.push(`${item.label}: May have issues`)
      }
    }
    if (conditionNotes.trim()) parts.push(`Additional notes: ${conditionNotes.trim()}`)
    return parts.join('. ')
  }, [checklist, conditionNotes])

  const handleFileDrop = useCallback((files: File[]) => {
    const file = files[0]
    if (file && file.type.startsWith('image/')) {
      setImageFile(file)
      setImagePreview(URL.createObjectURL(file))
      setImageUrl('')
      gradeEstimate.reset()
      costEstimate.reset()
    }
  }, [gradeEstimate, costEstimate])

  const handleUrlChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setImageUrl(e.target.value)
    if (e.target.value) {
      setImagePreview(e.target.value)
      setImageFile(null)
    } else {
      setImagePreview(null)
    }
    gradeEstimate.reset()
    costEstimate.reset()
  }, [gradeEstimate, costEstimate])

  const handleRemoveImage = useCallback(() => {
    setImageFile(null)
    setImagePreview(null)
    setImageUrl('')
    setConditionNotes('')
    setChecklist({})
    gradeEstimate.reset()
    costEstimate.reset()
  }, [gradeEstimate, costEstimate])

  const handleAnalyze = useCallback(() => {
    if (!imagePreview && !conditionNotes && Object.keys(checklist).length === 0) return
    const notes = buildConditionNotes()
    gradeEstimate.mutate(notes)

    // Also get cost estimate if we have a raw value
    const val = parseFloat(rawCardValue)
    if (val > 0 && result?.estimated_grade) {
      costEstimate.mutate({ cardValue: val, estimatedGrade: result.estimated_grade })
    }
  }, [imagePreview, conditionNotes, checklist, buildConditionNotes, gradeEstimate, costEstimate, rawCardValue, result])

  // After getting grade estimate, auto-fetch cost estimate if we have raw value
  const handleCostCheck = useCallback(() => {
    const val = parseFloat(rawCardValue)
    if (val > 0 && result?.estimated_grade) {
      costEstimate.mutate({ cardValue: val, estimatedGrade: result.estimated_grade })
    }
  }, [rawCardValue, result, costEstimate])

  // Value projections based on grade
  const valueProjections = useMemo(() => {
    const rawVal = parseFloat(rawCardValue) || 0
    if (rawVal <= 0) return []
    return Object.entries(companyData.multipliers).map(([grade, mult]) => ({
      grade: `${companyData.id} ${grade}`,
      value: rawVal * mult,
      profit: rawVal * mult - rawVal - (companyData.tiers[0]?.cost ?? 20),
    }))
  }, [rawCardValue, companyData])

  const toggleChecklist = (id: string) => {
    setChecklist(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">AI Card Grading</h1>
          <p className="mt-1 text-muted-foreground/60 text-sm">
            Get instant AI-powered condition analysis with PSA, BGS, and CGC grading standards
          </p>
        </div>

        {/* Grading Company Selector */}
        <div className="flex gap-2 flex-wrap">
          {GRADING_COMPANIES.map(c => (
            <button
              key={c.id}
              onClick={() => setSelectedCompany(c.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-all duration-200 ${
                selectedCompany === c.id
                  ? 'border-white/[0.12] bg-white/[0.04] text-foreground'
                  : 'border-white/[0.04] text-muted-foreground/50 hover:text-foreground/80 hover:border-white/[0.08]'
              }`}
            >
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: c.color }} />
              {c.id}
            </button>
          ))}
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Image Upload + Condition Checklist */}
          <div className="space-y-4">
            {!imagePreview ? (
              <>
                <DropZone onDrop={handleFileDrop} accept="image/*">
                  <div className="flex flex-col items-center gap-3 text-muted-foreground py-4">
                    <Upload className="h-12 w-12" />
                    <p className="text-base font-medium text-foreground">Drag &amp; drop your card image</p>
                    <p className="text-sm">or click to browse</p>
                    <p className="text-xs text-muted">Supports JPG, PNG, WebP · Front and back recommended</p>
                  </div>
                </DropZone>
                <div className="flex items-center gap-4">
                  <div className="h-px flex-1 bg-border" />
                  <span className="text-sm text-muted">OR</span>
                  <div className="h-px flex-1 bg-border" />
                </div>
                <Input
                  icon={<Globe className="h-4 w-4" />}
                  placeholder="Paste image URL..."
                  value={imageUrl}
                  onChange={handleUrlChange}
                />
              </>
            ) : (
              <div className="relative rounded-2xl border-2 border-border overflow-hidden">
                <img src={imagePreview} alt="Card preview" className="w-full h-auto max-h-[500px] object-contain bg-black/20" />
                <button
                  onClick={handleRemoveImage}
                  className="absolute top-3 right-3 flex items-center gap-1.5 rounded-lg bg-black/70 px-3 py-1.5 text-sm text-white hover:bg-black/90 transition-colors"
                >
                  <X className="h-4 w-4" /> Remove
                </button>
              </div>
            )}

            {/* Condition Checklist */}
            <Card variant="elevated">
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Shield className="w-4 h-4 text-accent" /> Condition Checklist
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {CONDITION_CHECKLIST.map(item => (
                  <button
                    key={item.id}
                    onClick={() => toggleChecklist(item.id)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl border text-left transition-all duration-200 ${
                      checklist[item.id]
                        ? 'border-emerald-500/20 bg-emerald-500/[0.05]'
                        : 'border-white/[0.04] hover:border-white/[0.08]'
                    }`}
                  >
                    <div className={`h-5 w-5 rounded-md border-2 flex items-center justify-center transition-all ${
                      checklist[item.id] ? 'border-emerald-400 bg-emerald-400/20' : 'border-white/[0.12]'
                    }`}>
                      {checklist[item.id] && <CheckCircle2 className="h-3 w-3 text-emerald-400" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-[11px] text-muted-foreground/50">{item.description}</p>
                    </div>
                  </button>
                ))}
              </CardContent>
            </Card>

            {/* Raw Card Value */}
            <Input
              label="Raw Card Value ($)"
              placeholder="e.g. 85.00"
              value={rawCardValue}
              onChange={(e) => setRawCardValue(e.target.value)}
              icon={<DollarSign className="h-4 w-4" />}
              type="number"
            />

            {/* Condition Notes */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Additional Condition Notes</label>
              <textarea
                placeholder="Describe any specific defects, whitening, scratches, print lines, etc."
                value={conditionNotes}
                onChange={(e) => setConditionNotes(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 bg-surface border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none transition resize-none"
              />
            </div>

            {/* Analyze Button */}
            <Button
              size="lg"
              className="w-full bg-gradient-to-r from-accent to-accent/80"
              onClick={handleAnalyze}
              disabled={(!imagePreview && !conditionNotes.trim() && Object.keys(checklist).length === 0) || isAnalyzing}
              isLoading={isAnalyzing}
            >
              <Sparkles className="h-5 w-5" />
              {isAnalyzing ? 'Analyzing...' : `Analyze for ${companyData.id} Grading`}
            </Button>

            {gradeEstimate.isError && (
              <div className="flex items-center gap-2 text-sm text-rose-400 bg-rose-400/10 rounded-lg px-4 py-3">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{gradeEstimate.error instanceof Error ? gradeEstimate.error.message : 'Grading failed. Backend may be offline.'}</span>
              </div>
            )}
          </div>

          {/* Right Column - Results + Reference Data */}
          <div className="space-y-4">
            {!result ? (
              <>
                {/* Centering Guide */}
                <Card variant="elevated">
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Info className="w-4 h-4 text-accent" /> Centering Standards
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {CENTERING_GUIDE.map(g => (
                      <div key={g.label} className="flex items-start gap-3 p-3 rounded-xl border border-white/[0.04]">
                        <Badge variant="accent" className="shrink-0 text-[10px]">{g.badge}</Badge>
                        <div>
                          <p className="text-sm font-medium">{g.label}</p>
                          <p className="text-[11px] text-muted-foreground/50">{g.desc}</p>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                {/* Service Tiers */}
                <Card variant="elevated">
                  <CardHeader>
                    <CardTitle className="text-sm">{companyData.name} — Service Tiers</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {companyData.tiers.map(t => (
                        <div key={t.name} className="flex items-center justify-between p-3 rounded-xl border border-white/[0.04] hover:border-white/[0.08] transition">
                          <div>
                            <p className="text-sm font-medium">{t.name}</p>
                            <p className="text-[11px] text-muted-foreground/50">{t.turnaround}</p>
                          </div>
                          <span className="text-sm font-mono-numbers font-bold text-accent">${t.cost}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Value Projections */}
                {valueProjections.length > 0 && (
                  <Card variant="elevated">
                    <CardHeader>
                      <CardTitle className="text-sm flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-accent" /> Value Projections
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {valueProjections.map(v => (
                          <div key={v.grade} className="flex items-center justify-between p-3 rounded-xl border border-white/[0.04]">
                            <span className="text-sm font-medium">{v.grade}</span>
                            <div className="flex items-center gap-3">
                              <span className="text-sm font-mono-numbers">${formatPrice(v.value)}</span>
                              <span className={`text-xs font-mono-numbers font-bold ${v.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {v.profit >= 0 ? '+' : ''}${formatPrice(v.profit)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <motion.div
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="space-y-4"
              >
                {/* Overall Grade Card */}
                {result.estimated_grade != null && (
                  <motion.div variants={staggerItem}>
                    <Card variant="elevated">
                      <CardContent className="flex flex-col items-center py-8">
                        <div className={`w-36 h-36 rounded-full border-4 ${getGradeBorderColor(result.estimated_grade)} flex flex-col items-center justify-center`}>
                          <span className={`text-4xl font-bold font-mono-numbers ${getGradeTextColor(result.estimated_grade)}`}>
                            {result.estimated_grade.toFixed(1)}
                          </span>
                          <span className={`text-[10px] font-medium mt-0.5 ${getGradeTextColor(result.estimated_grade)} opacity-70`}>
                            {getGradeLabel(result.estimated_grade)}
                          </span>
                        </div>
                        <p className="mt-4 text-lg font-semibold text-foreground">
                          {companyData.id} Estimated Grade
                        </p>
                        {result.confidence != null && (
                          <div className="mt-2 flex items-center gap-2">
                            <Progress value={result.confidence} color={result.confidence >= 80 ? 'success' : result.confidence >= 60 ? 'accent' : 'warning'} className="w-24 h-1.5" />
                            <span className="text-xs text-muted">{result.confidence}% confidence</span>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {/* Subgrades */}
                {result.subgrades && (
                  <motion.div variants={staggerItem}>
                    <Card variant="elevated">
                      <CardHeader>
                        <CardTitle className="text-sm">Subgrade Breakdown</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-4">
                          {(Object.entries(result.subgrades) as [string, number | undefined][])
                            .filter(([, score]) => score != null)
                            .map(([key, score]) => (
                              <div key={key} className="space-y-1.5">
                                <div className="flex items-center justify-between">
                                  <span className="text-sm capitalize text-muted">{key}</span>
                                  <span className="font-mono-numbers text-sm font-semibold text-foreground">
                                    {(score as number).toFixed(1)}
                                  </span>
                                </div>
                                <Progress value={(score as number) * 10} color={getSubgradeColor(score as number)} />
                              </div>
                            ))}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {/* Defects */}
                {result.defects && result.defects.length > 0 && (
                  <motion.div variants={staggerItem}>
                    <Card variant="elevated">
                      <CardHeader>
                        <CardTitle className="text-sm">Defects Found</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {result.defects.map((defect, i) => (
                            <div key={i} className="flex gap-2">
                              <AlertTriangle className="h-5 w-5 shrink-0 text-amber-400" />
                              <span className="text-sm text-foreground">{defect}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {/* Value Projections after grade */}
                {result.estimated_grade != null && valueProjections.length > 0 && (
                  <motion.div variants={staggerItem}>
                    <Card variant="elevated">
                      <CardHeader>
                        <CardTitle className="text-sm flex items-center gap-2">
                          <DollarSign className="w-4 h-4 text-accent" /> Graded Value Estimates
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {valueProjections.map(v => (
                            <div key={v.grade} className="flex items-center justify-between p-3 rounded-xl border border-white/[0.04]">
                              <span className="text-sm font-medium">{v.grade}</span>
                              <div className="flex items-center gap-3">
                                <span className="text-sm font-mono-numbers">${formatPrice(v.value)}</span>
                                <span className={`text-xs font-mono-numbers font-bold ${v.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                  {v.profit >= 0 ? '+' : ''}${formatPrice(v.profit)}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {/* Cross-company comparison */}
                <motion.div variants={staggerItem}>
                  <Card variant="elevated">
                    <CardHeader>
                      <CardTitle className="text-sm">Service Tier Costs — {companyData.id}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {companyData.tiers.map(t => {
                          const rawVal = parseFloat(rawCardValue) || 0
                          const estimatedGradedValue = rawVal * (companyData.multipliers[Object.keys(companyData.multipliers)[0]] || 2)
                          const roi = rawVal > 0 ? estimatedGradedValue - rawVal - t.cost : 0
                          return (
                            <div key={t.name} className="flex items-center justify-between p-3 rounded-xl border border-white/[0.04]">
                              <div>
                                <p className="text-sm font-medium">{t.name}</p>
                                <p className="text-[11px] text-muted-foreground/50">{t.turnaround}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-sm font-mono-numbers font-bold">${t.cost}</span>
                                {rawVal > 0 && (
                                  <span className={`text-xs font-mono-numbers ${roi >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    ROI: {roi >= 0 ? '+' : ''}${formatPrice(roi)}
                                  </span>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </PageTransition>
  )
}
