import { Outlet } from 'react-router-dom'
import TopNav from './TopNav'
import MobileNav from './MobileNav'

export default function AppShell() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top navigation — premium glass header + horizontal tabs */}
      <TopNav />

      {/* Main content — generous whitespace, centered container */}
      <main className="pt-[100px] md:pt-[96px] pb-24 md:pb-16">
        <div className="max-w-[1440px] mx-auto px-5 sm:px-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom nav */}
      <MobileNav />
    </div>
  )
}
