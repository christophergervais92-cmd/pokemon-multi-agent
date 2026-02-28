import React, { useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toastVariants } from '@/lib/animations'
import { useUIStore } from '@/store/uiStore'
import type { Toast as ToastItem } from '@/types/common'

type ToastType = ToastItem['type']

const iconMap: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle className="h-5 w-5" />,
  error: <AlertCircle className="h-5 w-5" />,
  warning: <AlertTriangle className="h-5 w-5" />,
  info: <Info className="h-5 w-5" />,
}

const colorMap: Record<ToastType, string> = {
  success: 'border-success/30 bg-success-muted text-success',
  error: 'border-danger/30 bg-danger-muted text-danger',
  warning: 'border-warning/30 bg-warning-muted text-warning',
  info: 'border-info/30 bg-info-muted text-info',
}

interface ToastItemComponentProps {
  toast: ToastItem
}

const ToastItemComponent: React.FC<ToastItemComponentProps> = ({ toast }) => {
  const removeToast = useUIStore((s) => s.removeToast)
  const duration = toast.duration ?? 4000

  useEffect(() => {
    if (duration <= 0) return
    const timer = setTimeout(() => {
      removeToast(toast.id)
    }, duration)
    return () => clearTimeout(timer)
  }, [toast.id, duration, removeToast])

  return (
    <motion.div
      layout
      variants={toastVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={cn(
        'flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg',
        'min-w-[320px] max-w-md',
        colorMap[toast.type],
      )}
    >
      <span className="mt-0.5 shrink-0">{iconMap[toast.type]}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold">{toast.title}</p>
        {toast.message && (
          <p className="mt-0.5 text-xs opacity-80">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        className="shrink-0 rounded-md p-0.5 opacity-70 hover:opacity-100 transition-opacity"
      >
        <X className="h-4 w-4" />
      </button>
    </motion.div>
  )
}

export const ToastContainer: React.FC = () => {
  const toasts = useUIStore((s) => s.toasts)

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItemComponent key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  )
}

ToastContainer.displayName = 'ToastContainer'

export function useToast() {
  const addToast = useUIStore((s) => s.addToast)
  const removeToast = useUIStore((s) => s.removeToast)
  const clearToasts = useUIStore((s) => s.clearToasts)

  const toast = useCallback(
    (type: ToastType, title: string, message?: string, duration?: number) => {
      addToast({ type, title, message, duration })
    },
    [addToast],
  )

  const success = useCallback(
    (title: string, message?: string, duration?: number) =>
      toast('success', title, message, duration),
    [toast],
  )

  const error = useCallback(
    (title: string, message?: string, duration?: number) =>
      toast('error', title, message, duration),
    [toast],
  )

  const warning = useCallback(
    (title: string, message?: string, duration?: number) =>
      toast('warning', title, message, duration),
    [toast],
  )

  const info = useCallback(
    (title: string, message?: string, duration?: number) =>
      toast('info', title, message, duration),
    [toast],
  )

  return { toast, success, error, warning, info, removeToast, clearToasts }
}

export default ToastContainer
