import { motion } from 'framer-motion'
import { LogIn, Shield, Zap, Bell } from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { fadeInUp } from '@/lib/animations'

export default function Login() {
  return (
    <PageTransition>
      <div className="flex items-center justify-center min-h-[70vh]">
        <motion.div variants={fadeInUp} initial="initial" animate="animate" className="max-w-md w-full">
          <Card variant="elevated" className="overflow-hidden">
            {/* Hero */}
            <div className="gradient-accent p-8 text-center">
              <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm">
                <img src="/pokeball.svg" alt="PokeAgent" className="w-12 h-12" />
              </div>
              <h1 className="text-2xl font-bold text-white">Welcome to PokeAgent</h1>
              <p className="text-white/80 text-sm mt-2">Pokemon TCG Market Intelligence</p>
            </div>

            <CardContent className="p-6 space-y-6">
              <div className="space-y-3">
                {[
                  { icon: Bell, text: 'Real-time stock alerts with Discord webhooks' },
                  { icon: Zap, text: 'Create automated stock monitors' },
                  { icon: Shield, text: 'Save your portfolio and settings' },
                ].map((feature) => (
                  <div key={feature.text} className="flex items-center gap-3 text-sm text-muted">
                    <feature.icon className="w-4 h-4 text-accent shrink-0" />
                    {feature.text}
                  </div>
                ))}
              </div>

              <Button className="w-full h-12 text-base">
                <svg className="w-6 h-6 mr-2" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z" />
                </svg>
                Login with Discord
              </Button>

              <p className="text-xs text-muted-foreground text-center">
                Most features work without login. Sign in to unlock monitors and sync.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </PageTransition>
  )
}
