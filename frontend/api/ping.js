// Vercel serverless function — called by cron every 14 min to keep Render awake
export default async function handler(req, res) {
  try {
    const response = await fetch('https://pokemon-multi-agent.onrender.com/health', {
      method: 'GET',
      signal: AbortSignal.timeout(10000),
    })
    const status = response.ok ? 'ok' : 'degraded'
    res.status(200).json({ pinged: true, backend: status, ts: new Date().toISOString() })
  } catch (err) {
    res.status(200).json({ pinged: false, backend: 'offline', error: err.message })
  }
}
