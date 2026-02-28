import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Sparkles, TrendingUp, Shield, Zap, Star } from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { fadeInUp, staggerContainer, staggerItem } from '@/lib/animations'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const QUICK_QUESTIONS = [
  { label: 'Best Sets to Buy', icon: Star, query: 'What are the best Pokemon TCG sets to invest in right now?' },
  { label: 'Grade or Sell Raw?', icon: Shield, query: 'Should I grade my cards or sell them raw?' },
  { label: 'Top Chase Cards', icon: Zap, query: 'What are the top chase cards this month?' },
  { label: 'Market Trends', icon: TrendingUp, query: 'What are the current Pokemon TCG market trends?' },
]

const MARKET_INSIGHTS = [
  { title: 'Prismatic Evolutions', subtitle: 'ETB prices up 15% this week', trend: 'up', badge: 'Hot' },
  { title: 'Surging Sparks', subtitle: 'Booster boxes restocked at Target', trend: 'neutral', badge: 'Restock' },
  { title: 'Evolving Skies', subtitle: 'Moonbreon hitting new highs', trend: 'up', badge: 'Investment' },
]

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hey! I'm your PokeAgent AI assistant. Ask me anything about Pokemon TCG — market prices, investment advice, grading tips, or where to find products. What can I help you with?",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = (text: string) => {
    if (!text.trim()) return
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsTyping(true)

    setTimeout(() => {
      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: getResponse(text),
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, response])
      setIsTyping(false)
    }, 1500)
  }

  const getResponse = (query: string): string => {
    const q = query.toLowerCase()
    if (q.includes('best set') || q.includes('invest')) {
      return "Right now, **Prismatic Evolutions** and **Surging Sparks** are the hottest sets. Prismatic Evolutions has incredible pull rates for Eeveelution SARs, and ETBs are appreciating fast. For long-term holds, **Evolving Skies** sealed product continues to climb. The Umbreon VMAX Alt Art alone drives massive demand."
    }
    if (q.includes('grade') || q.includes('raw')) {
      return "General rule: **Grade if the card is worth $50+ raw** and in near-mint condition. PSA 10 multipliers are typically 2-4x raw price for modern cards. Use our Flip Calculator to check the exact ROI for your card. For cards under $30 raw, selling raw is usually more profitable after grading fees."
    }
    if (q.includes('chase') || q.includes('top card')) {
      return "Top chase cards right now:\n\n1. **Umbreon VMAX Alt Art** (Evolving Skies) — $350+\n2. **Charizard ex SAR** (Obsidian Flames) — $195\n3. **Pikachu ex SAR** (Prismatic Evolutions) — $180\n4. **Rayquaza ex SAR** (Prismatic Evolutions) — $275\n5. **Moonbreon VMAX** (Evolving Skies) — $320\n\nThese are all trending upward with strong demand."
    }
    if (q.includes('trend') || q.includes('market')) {
      return "**Current Market Trends:**\n\n- Modern sealed product is appreciating 10-20% monthly (especially Prismatic Evolutions)\n- PSA grading turnaround times are improving, driving more submissions\n- Japanese products gaining popularity in Western markets\n- Vintage Base Set continues slow, steady growth\n- Watch for the next set announcement — it usually dips current set prices temporarily."
    }
    return "That's a great question! I'd recommend checking our Stock Finder for real-time availability, or the Card Lookup for current market prices. Is there something specific about pricing, investing, or product availability I can help with?"
  }

  return (
    <PageTransition>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-8rem)]">
        {/* Chat Area */}
        <div className="lg:col-span-3 flex flex-col">
          <div className="mb-4">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">AI Assistant</h1>
            <p className="text-muted-foreground/60 text-sm mt-1">Your Pokemon TCG market intelligence advisor</p>
          </div>

          {/* Messages */}
          <Card variant="elevated" className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <AnimatePresence>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                      msg.role === 'assistant' ? 'bg-accent-muted' : 'bg-surface-hover'
                    }`}>
                      {msg.role === 'assistant' ? <Bot className="w-4 h-4 text-accent" /> : <User className="w-4 h-4 text-muted" />}
                    </div>
                    <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user'
                        ? 'bg-accent text-white rounded-br-sm'
                        : 'bg-surface-hover text-foreground rounded-bl-sm'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {isTyping && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center">
                    <Bot className="w-4 h-4 text-accent" />
                  </div>
                  <div className="bg-surface-hover rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
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
                  type="text"
                  placeholder="Ask about prices, investing, grading, or market trends..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
                  className="flex-1 h-10 px-4 bg-surface border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none transition"
                />
                <Button onClick={() => sendMessage(input)} disabled={!input.trim()}>
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar — Market Insights */}
        <div className="hidden lg:flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide">Market Insights</h2>
          {MARKET_INSIGHTS.map((insight, i) => (
            <motion.div key={insight.title} variants={fadeInUp} initial="initial" animate="animate" transition={{ delay: i * 0.1 }}>
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
              <p className="text-sm font-semibold">Pro Tip</p>
              <p className="text-xs text-muted mt-1">Check the Flip Calculator before grading any card over $50</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageTransition>
  )
}
