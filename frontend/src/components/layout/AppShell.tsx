import { Outlet } from 'react-router-dom'
import TopNav from './TopNav'
import MobileNav from './MobileNav'

export default function AppShell() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="ambient-orbs" aria-hidden="true" />

      <TopNav />

      {/* Main — ticker (32) + main bar (56) = 88px top offset */}
      <main className="pt-[88px] pb-24 lg:pb-12">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>

      <MobileNav />
    </div>
  )
}
