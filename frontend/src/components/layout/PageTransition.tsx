import { motion, AnimatePresence } from 'framer-motion'
import { pageVariants, pageTransition } from '@/lib/animations'
import { cn } from '@/lib/utils'
import { useLocation } from 'react-router-dom'

interface PageTransitionProps {
  children: React.ReactNode
  className?: string
}

export function PageTransition({ children, className }: PageTransitionProps) {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={pageTransition}
        className={cn('w-full', className)}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
