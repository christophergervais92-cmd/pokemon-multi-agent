import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Bot, User, Sparkles, TrendingUp, Shield, Zap, Star,
  AlertCircle, RotateCcw, Loader2, ExternalLink
} from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { fadeInUp, staggerContainer, staggerItem } from '@/lib/animations'
import { useAssistantChat } from '@/hooks/useApi'
import type { ChatMessage } from '@/lib/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isError?: boolean
  toolResults?: Record<string, unknown>[]
}

const QUICK_QUESTIONS = [
  { label: 'Best Sets to Buy', icon: Star, query: 'What are the best Pokemon TCG sets to invest in right now?' },
  { label: 'Grade or Sell Raw?', icon: Shield, query: 'Should I grade my cards or sell them raw? What are the general rules?' },
  { label: 'Top Chase Cards', icon: Zap, query: 'What are the top chase cards this month with current prices?' },
  { label: 'Market Trends', icon: TrendingUp, query: 'What are the current Pokemon TCG market trends for February 2026?' },
]

const MARKET_INSIGHTS = [
  { title: 'Prismatic Evolutions', subtitle: 'ETB prices up 15% this week', trend: 'up', badge: 'Hot' },
  { title: 'Surging Sparks', subtitle: 'Booster boxes restocked at Target', trend: 'neutral', badge: 'Restock' },
  { title: 'Evolving Skies', subtitle: 'Moonbreon hitting new highs', trend: 'up', badge: 'Investment' },
]

// Offline fallback responses
function getOfflineResponse(query: string): string {
  const q = query.toLowerCase()
  if (q.includes('best set') || q.includes('invest')) {
    return "**Top sets to consider right now:**\n\n1. **Prismatic Evolutions** — Eeveelution SARs are driving massive demand. ETBs appreciating fast.\n2. **Surging Sparks** — Strong chase cards and good pull rates make this a solid value play.\n3. **Evolving Skies** — The Umbreon VMAX Alt Art alone drives demand. Sealed product continues climbing.\n\n*Note: I'm currently in offline mode. Connect to the API for real-time data and personalized analysis.*"
  }
  if (q.includes('grade') || q.includes('raw')) {
    return "**General grading rules of thumb:**\n\n- **Grade if the card is worth $50+ raw** and in near-mint condition\n- PSA 10 multipliers are typically 2-4x raw price for modern cards\n- Cards under $30 raw are usually more profitable sold raw after grading fees\n- Use the Flip Calculator tab for exact ROI calculations\n\n*Connect to the API for card-specific grading recommendations.*"
  }
  if (q.includes('chase') || q.includes('top card')) {
    return "**Current top chase cards:**\n\n1. **Umbreon VMAX Alt Art** (Evolving Skies) — $350+\n2. **Charizard ex SAR** (Obsidian Flames) — $195\n3. **Pikachu ex SAR** (Prismatic Evolutions) — $180\n4. **Rayquaza ex SAR** (Prismatic Evolutions) — $275\n\n*Prices are approximate. Connect to the API for real-time pricing.*"
  }
  if (q.includes('trend') || q.includes('market')) {
    return "**Current market trends:**\n\n- Modern sealed product appreciating 10-20% monthly\n- PSA grading turnaround improving, driving more submissions\n- Japanese products gaining western market share\n- Vintage Base Set continues steady growth\n\n*Connect to the API for live market analysis.*"
  }
  return "I'd be happy to help with that! Try asking about:\n\n- **Pricing** — Current card values and trends\n- **Investing** — Best sets and products to buy\n- **Grading** — Whether to grade or sell raw\n- **Market** — Latest trends and news\n\n*I'm currently in offline mode. The AI backend may need to be configured.*"
}

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hey! I'm your PokeAgent AI assistant powered by Claude. Ask me anything about Pokemon TCG — market prices, investment advice, grading tips, card lookups, or where to find products. I can search cards, check prices, and analyze the market for you.",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const chatMutation = useAssistantChat()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = useCallback((text: string) => {
    if (!text.trim() || chatMutation.isPending) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')

    // Build history for context
    const history: ChatMessage[] = messages
      .filter(m => m.id !== '1') // skip initial greeting
      .map(m => ({ role: m.role, content: m.content }))

    chatMutation.mutate(
      { message: text, history },
      {
        onSuccess: (data) => {
          const response: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: data.response,
            timestamp: new Date(),
            toolResults: data.tool_results,
          }
          setMessages(prev => [...prev, response])
        },
        onError: () => {
          // Fallback to offline responses
          const response: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: getOfflineResponse(text),
            timestamp: new Date(),
          }
          setMessages(prev => [...prev, response])
        },
      }
    )
  }, [chatMutation, messages])

  const clearChat = () => {
    setMessages([{
      id: Date.now().toString(),
      role: 'assistant',
      content: "Chat cleared! What would you like to know about Pokemon TCG?",
      timestamp: new Date(),
    }])
  }

  // Render markdown-like bold text
  const renderContent = (content: string) => {
    const parts = content.split(/(\*\*[^*]+\*\*)/g)
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-bold text-foreground">{part.slice(2, -2)}</strong>
      }
      return <span key={i}>{part}</span>
    })
  }

  return (
    <PageTransition>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-8rem)]">
        {/* Chat Area */}
        <div className="lg:col-span-3 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="font-display text-4xl sm:text-5xl leading-none tracking-tight-er text-foreground">AI Assistant</h1>
              <p className="text-muted-foreground/60 text-sm mt-1">
                Pokemon TCG market intelligence powered by Claude
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={clearChat}>
              <RotateCcw className="w-3.5 h-3.5 mr-1" /> Clear
            </Button>
          </div>

          {/* Messages */}
          <Card variant="elevated" className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <AnimatePresence>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                  >
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring', stiffness: 400, damping: 15, delay: 0.1 }}
                      className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                        msg.role === 'assistant' ? 'bg-accent-muted' : 'bg-surface-hover'
                      }`}
                    >
                      {msg.role === 'assistant' ? (
                        <Bot className="w-4 h-4 text-accent" />
                      ) : (
                        <User className="w-4 h-4 text-muted" />
                      )}
                    </motion.div>
                    <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user'
                        ? 'bg-accent text-white rounded-br-sm'
                        : msg.isError
                          ? 'bg-danger-muted text-foreground rounded-bl-sm border border-danger/20'
                          : 'bg-surface-hover text-foreground rounded-bl-sm'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{renderContent(msg.content)}</p>
                      {msg.toolResults && msg.toolResults.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-border/50">
                          <p className="text-[10px] text-muted uppercase tracking-wide mb-1">Tools Used</p>
                          <div className="flex flex-wrap gap-1">
                            {msg.toolResults.map((tool, i) => (
                              <Badge key={i} variant="default" className="text-[10px]">
                                {String(tool.tool || tool.type || 'tool')}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Typing indicator */}
              {chatMutation.isPending && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3"
                >
                  <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center">
                    <Bot className="w-4 h-4 text-accent" />
                  </div>
                  <div className="bg-surface-hover rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />
                      <span className="text-xs text-muted">Thinking...</span>
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Questions */}
            {messages.length <= 1 && (
              <div className="px-4 pb-3">
                <motion.div variants={staggerContainer} initial="initial" animate="animate" className="flex flex-wrap gap-2">
                  {QUICK_QUESTIONS.map((q) => (
                    <motion.button
                      key={q.label}
                      variants={staggerItem}
                      onClick={() => sendMessage(q.query)}
                      whileHover={{ scale: 1.05, y: -2 }}
                      whileTap={{ scale: 0.95 }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border text-xs font-medium text-muted hover:text-foreground hover:border-accent/50 hover:bg-accent-muted transition"
                    >
                      <q.icon className="w-3 h-3" /> {q.label}
                    </motion.button>
                  ))}
                </motion.div>
              </div>
            )}

            {/* Input */}
            <div className="p-4 border-t border-border">
              <div className="flex gap-3">
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Ask about prices, investing, grading, or market trends..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
                  disabled={chatMutation.isPending}
                  className="flex-1 h-10 px-4 bg-surface border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none transition disabled:opacity-50"
                />
                <Button
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || chatMutation.isPending}
                >
                  {chatMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="hidden lg:flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide">Market Insights</h2>
          {MARKET_INSIGHTS.map((insight, i) => (
            <motion.div
              key={insight.title}
              variants={fadeInUp}
              initial="initial"
              animate="animate"
              transition={{ delay: i * 0.1 }}
            >
              <Card hover className="cursor-pointer">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-1">
                    <h3 className="text-sm font-semibold">{insight.title}</h3>
                    <Badge variant={insight.trend === 'up' ? 'success' : 'default'} className="text-[10px]">
                      {insight.badge}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted">{insight.subtitle}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}

          <Card variant="gradient" className="mt-4">
            <CardContent className="p-4 text-center">
              <Sparkles className="w-8 h-8 mx-auto mb-2 text-accent" />
              <p className="text-sm font-semibold">AI-Powered</p>
              <p className="text-xs text-muted mt-1">Powered by Claude with access to card search, pricing, and market data tools</p>
            </CardContent>
          </Card>

          <div className="mt-auto">
            <p className="text-[10px] text-muted text-center leading-relaxed">
              AI responses are for informational purposes only. Always verify prices before making purchases.
            </p>
          </div>
        </div>
      </div>
    </PageTransition>
  )
}
