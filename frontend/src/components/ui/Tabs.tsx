import React, { createContext, useContext, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { fadeIn } from '@/lib/animations'

interface TabsContextValue {
  activeTab: string
  setActiveTab: (value: string) => void
}

const TabsContext = createContext<TabsContextValue | null>(null)

function useTabsContext(): TabsContextValue {
  const ctx = useContext(TabsContext)
  if (!ctx) {
    throw new Error('Tabs compound components must be used within a TabGroup')
  }
  return ctx
}

export interface TabGroupProps {
  defaultValue: string
  onChange?: (value: string) => void
  children: React.ReactNode
  className?: string
}

export const TabGroup: React.FC<TabGroupProps> = ({
  defaultValue,
  onChange,
  children,
  className,
}) => {
  const [activeTab, setActiveTabState] = useState(defaultValue)

  const setActiveTab = useCallback(
    (value: string) => {
      setActiveTabState(value)
      onChange?.(value)
    },
    [onChange],
  )

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

TabGroup.displayName = 'TabGroup'

export interface TabListProps {
  children: React.ReactNode
  className?: string
}

export const TabList: React.FC<TabListProps> = ({ children, className }) => {
  return (
    <div
      className={cn(
        'flex gap-1 rounded-lg bg-surface-elevated p-1',
        className,
      )}
      role="tablist"
    >
      {children}
    </div>
  )
}

TabList.displayName = 'TabList'

export interface TabProps {
  value: string
  children: React.ReactNode
  className?: string
}

export const Tab: React.FC<TabProps> = ({ value, children, className }) => {
  const { activeTab, setActiveTab } = useTabsContext()
  const isActive = activeTab === value

  return (
    <button
      role="tab"
      aria-selected={isActive}
      onClick={() => setActiveTab(value)}
      className={cn(
        'relative rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50',
        isActive
          ? 'bg-accent text-white'
          : 'text-muted hover:text-foreground',
        className,
      )}
    >
      {children}
    </button>
  )
}

Tab.displayName = 'Tab'

export interface TabPanelsProps {
  children: React.ReactNode
  className?: string
}

export const TabPanels: React.FC<TabPanelsProps> = ({ children, className }) => {
  return <div className={className}>{children}</div>
}

TabPanels.displayName = 'TabPanels'

export interface TabPanelProps {
  value: string
  children: React.ReactNode
  className?: string
}

export const TabPanel: React.FC<TabPanelProps> = ({
  value,
  children,
  className,
}) => {
  const { activeTab } = useTabsContext()

  return (
    <AnimatePresence mode="wait">
      {activeTab === value && (
        <motion.div
          key={value}
          role="tabpanel"
          variants={fadeIn}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={{ duration: 0.15 }}
          className={className}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}

TabPanel.displayName = 'TabPanel'

export default TabGroup
