export interface Monitor {
  id: string
  query: string
  retailer: string
  zip?: string
  interval: number
  active: boolean
  lastRun?: string
  lastResult?: string
  createdAt: string
}

export interface MonitorGroup {
  id: string
  name: string
  webhookUrl?: string
  tasks: Monitor[]
}
