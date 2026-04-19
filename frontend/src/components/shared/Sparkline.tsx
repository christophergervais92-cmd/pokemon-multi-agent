/**
 * Minimal inline sparkline — no axes, no labels. Just a data shape.
 * Auto-detects up/down trend and colors accordingly.
 */
import { useMemo } from 'react'

interface SparklineProps {
  data: Array<{ date?: string; price: number } | number>
  width?: number
  height?: number
  color?: 'auto' | 'accent' | 'muted'
  strokeWidth?: number
  className?: string
}

export default function Sparkline({
  data,
  width = 80,
  height = 24,
  color = 'auto',
  strokeWidth = 1.25,
  className = '',
}: SparklineProps) {
  const path = useMemo(() => {
    if (!data || data.length === 0) return { d: '', trend: 0 }
    const values = data.map(d => (typeof d === 'number' ? d : d.price))
    const min = Math.min(...values)
    const max = Math.max(...values)
    const range = max - min || 1
    const stepX = width / (values.length - 1 || 1)

    const pts = values.map((v, i) => {
      const x = i * stepX
      const y = height - ((v - min) / range) * height
      return { x, y }
    })

    const d = pts
      .map((p, i) => (i === 0 ? `M ${p.x.toFixed(1)} ${p.y.toFixed(1)}` : `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`))
      .join(' ')

    const trend = values[values.length - 1] - values[0]
    return { d, trend }
  }, [data, width, height])

  if (!path.d) {
    return (
      <svg width={width} height={height} className={className}>
        <line
          x1={0} y1={height / 2} x2={width} y2={height / 2}
          stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="2 3"
        />
      </svg>
    )
  }

  const stroke =
    color === 'accent' ? 'var(--color-accent)' :
    color === 'muted'  ? 'var(--color-muted)' :
    path.trend > 0 ? 'var(--color-success)' :
    path.trend < 0 ? 'var(--color-danger)' :
    'var(--color-muted)'

  const fill =
    color === 'accent' ? 'rgba(255,107,26,0.08)' :
    path.trend > 0 ? 'rgba(34,197,94,0.08)' :
    path.trend < 0 ? 'rgba(239,68,68,0.08)' :
    'rgba(255,255,255,0.04)'

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      preserveAspectRatio="none"
    >
      <path
        d={`${path.d} L ${width} ${height} L 0 ${height} Z`}
        fill={fill}
        stroke="none"
      />
      <path d={path.d} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
