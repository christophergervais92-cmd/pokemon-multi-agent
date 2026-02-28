export interface APIResponse<T> {
  data: T
  error?: string
  cached?: boolean
}

export interface User {
  id: string
  username: string
  discriminator?: string
  avatar?: string
  email?: string
}

export interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

export interface GradingResult {
  grade: number
  company: string
  centering: number
  corners: number
  surface: number
  edges: number
  defects: string[]
  estimatedValue?: { low: number; high: number }
  confidence: number
}

export interface FlipResult {
  gradingCost: number
  company: string
  tier: string
  rawPrice: number
  expectedValues: {
    grade: string
    probability: number
    price: number
    roi: number
  }[]
  expectedROI: number
  breakEvenGrade: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}
