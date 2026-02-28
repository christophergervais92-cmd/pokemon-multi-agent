# PokeAgent v4 — Full React + Tailwind Rebuild

## Overview
Rebuild the vanilla JS dashboard (13,343 lines) into a professional React 18 + TypeScript + Tailwind CSS application with Framer Motion animations, modern data fetching, and a polished dark-theme UI. The Flask backend stays untouched — only the frontend is rebuilt.

---

## Tech Stack
- **Vite 6** — Build tool (fast HMR, optimized production builds)
- **React 18** — UI library with Suspense boundaries
- **TypeScript** — Full type safety
- **Tailwind CSS v3** — Utility-first styling with custom design tokens
- **Framer Motion 11** — Page transitions, micro-interactions, loading animations
- **TanStack Query v5** — Server state, caching, background refetching
- **Zustand** — Client state (auth, settings, UI preferences)
- **React Router v6** — Client-side routing with lazy-loaded pages
- **Recharts** — Price charts, portfolio graphs, analytics visualizations
- **React-Leaflet** — Vending machine map
- **Lucide React** — Icon system (consistent, tree-shakeable)
- **clsx + tailwind-merge** — Conditional className composition
- **date-fns** — Date formatting

---

## Project Structure
```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── vercel.json
├── public/
│   ├── favicon.ico
│   └── pokeball.svg
├── src/
│   ├── main.tsx                    # React root + providers
│   ├── App.tsx                     # Router + layout wrapper
│   ├── index.css                   # Tailwind directives + custom CSS
│   │
│   ├── api/
│   │   ├── client.ts              # Fetch wrapper (auth headers, base URL, error handling)
│   │   ├── endpoints.ts           # All API route constants
│   │   └── hooks/                 # TanStack Query hooks per domain
│   │       ├── useStock.ts
│   │       ├── useCards.ts
│   │       ├── usePrices.ts
│   │       ├── useDrops.ts
│   │       ├── useMonitors.ts
│   │       ├── useGrading.ts
│   │       ├── usePortfolio.ts
│   │       ├── useAnalytics.ts
│   │       ├── useAssistant.ts
│   │       ├── useSets.ts
│   │       └── useAuth.ts
│   │
│   ├── store/
│   │   ├── authStore.ts           # Discord OAuth state, token, user info
│   │   ├── settingsStore.ts       # API URL, notifications, ZIP, preferences
│   │   └── uiStore.ts            # Sidebar state, mobile nav, active tab
│   │
│   ├── components/
│   │   ├── ui/                    # Primitive components (shadcn-inspired)
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Tabs.tsx
│   │   │   ├── Tooltip.tsx
│   │   │   ├── Switch.tsx
│   │   │   ├── Progress.tsx
│   │   │   ├── Avatar.tsx
│   │   │   ├── DropZone.tsx
│   │   │   └── EmptyState.tsx
│   │   │
│   │   ├── layout/
│   │   │   ├── AppShell.tsx       # Main layout (sidebar + content area)
│   │   │   ├── Sidebar.tsx        # Desktop sidebar nav with icons
│   │   │   ├── TopBar.tsx         # Search bar, theme toggle, user menu
│   │   │   ├── MobileNav.tsx      # Bottom tab bar for mobile
│   │   │   └── PageTransition.tsx # Framer Motion page wrapper
│   │   │
│   │   ├── charts/
│   │   │   ├── PriceChart.tsx     # Recharts line chart for card prices
│   │   │   ├── PortfolioChart.tsx # Pie/bar chart for portfolio breakdown
│   │   │   └── StatsChart.tsx     # Sparkline mini-charts for KPIs
│   │   │
│   │   └── shared/
│   │       ├── CardGrid.tsx       # Responsive grid for Pokemon cards
│   │       ├── ProductCard.tsx    # Sealed product display card
│   │       ├── StoreResult.tsx    # Stock search result card
│   │       ├── SearchBar.tsx      # Reusable search with suggestions
│   │       ├── PriceTag.tsx       # Price display with change indicator
│   │       ├── RetailerBadge.tsx  # Colored retailer logo badge
│   │       ├── GradeDisplay.tsx   # PSA/CGC/BGS grade visual
│   │       └── LoadingScreen.tsx  # Full-page loading with Pokeball animation
│   │
│   ├── pages/
│   │   ├── Dashboard.tsx          # Home — KPIs, trending, quick actions
│   │   ├── Stock.tsx              # Stock finder with retailer filters
│   │   ├── Cards.tsx              # Card search + detail view
│   │   ├── CardDetail.tsx         # Card detail sub-page
│   │   ├── Database.tsx           # Set browser, chase cards, pull rates
│   │   ├── Drops.tsx              # Upcoming releases + intel feed
│   │   ├── Monitors.tsx           # Create/manage stock monitors
│   │   ├── Flip.tsx               # Grading ROI calculator
│   │   ├── Grading.tsx            # AI card grading from images
│   │   ├── Portfolio.tsx          # Collection tracking + P&L
│   │   ├── Analytics.tsx          # Purchase tracking + backtesting
│   │   ├── Assistant.tsx          # AI chat + market insights
│   │   ├── Vending.tsx            # Vending machine map
│   │   ├── Settings.tsx           # App configuration
│   │   └── Login.tsx              # Discord OAuth login page
│   │
│   ├── lib/
│   │   ├── utils.ts              # cn(), formatPrice(), formatDate()
│   │   ├── constants.ts          # Retailers, grade types, sealed products
│   │   └── animations.ts         # Framer Motion animation presets
│   │
│   ├── types/
│   │   ├── card.ts               # PokemonCard, CardPrice, GradedPrice
│   │   ├── stock.ts              # StoreResult, StockStats, Product
│   │   ├── drops.ts              # Drop, IntelItem, Rumor
│   │   ├── portfolio.ts          # PortfolioItem, PortfolioStats
│   │   ├── monitor.ts            # Monitor, MonitorGroup
│   │   └── common.ts             # APIResponse, PaginatedResult, User
│   │
│   └── hooks/
│       ├── useTheme.ts           # Dark/light theme toggle
│       ├── useLive.ts            # SSE connection for real-time updates
│       ├── useDebounce.ts        # Debounced search input
│       ├── useLocalStorage.ts    # Typed localStorage wrapper
│       └── useMediaQuery.ts      # Responsive breakpoint hook
```

---

## Design System

### Color Palette (Dark Theme — Default)
```
Background:     #0a0e1a (deep navy-black)
Surface:        #111827 (card backgrounds)
Surface-hover:  #1f2937 (elevated surfaces)
Border:         #1e293b (subtle borders)
Text Primary:   #f1f5f9
Text Secondary: #94a3b8
Accent:         #f97316 (orange — Charizard-inspired)
Accent-glow:    #fb923c (hover state)
Success:        #22c55e
Warning:        #eab308
Danger:         #ef4444
Info:           #3b82f6
Gradient-start: #f97316
Gradient-end:   #ec4899 (orange → pink)
```

### Typography
- Font: Inter (headings) + JetBrains Mono (prices/numbers)
- Sizes: text-xs through text-4xl with responsive scaling

### Spacing & Layout
- Sidebar: 280px (desktop), hidden (mobile)
- Content max-width: 1400px
- Card padding: p-4 to p-6
- Grid gap: gap-4 to gap-6
- Border radius: rounded-xl throughout

### Animation Presets
- Page enter: fadeInUp (0.3s ease-out)
- Card hover: scale(1.02) + shadow elevation
- Skeleton pulse: animate-pulse with gradient shimmer
- Toast: slide-in from top-right
- Number count-up: spring animation for KPI values
- Stagger children: 50ms delay per item in grids

---

## Implementation Phases

### Phase 1: Foundation (~40 files)
**Goal:** Scaffolding, design system, layout shell, core infrastructure

1. `npm create vite@latest frontend -- --template react-ts`
2. Install dependencies (tailwindcss, framer-motion, @tanstack/react-query, zustand, react-router-dom, recharts, lucide-react, clsx, tailwind-merge, date-fns)
3. Configure Tailwind with custom theme tokens
4. Build `index.css` with Tailwind directives, custom animations, font imports
5. Build all UI primitives: Button, Card, Input, Select, Badge, Modal, Skeleton, Toast, Tabs, Tooltip, Switch, Progress, Avatar, DropZone, EmptyState
6. Build layout: AppShell, Sidebar (with all nav items + icons), TopBar (search + theme + user), MobileNav (bottom tabs)
7. Build PageTransition wrapper (Framer Motion AnimatePresence)
8. Build API client (fetch wrapper with auto-detect API URL, auth headers, error handling)
9. Build Zustand stores (auth, settings, UI)
10. Build React Router config with lazy-loaded pages
11. Build shared components: SearchBar, PriceTag, RetailerBadge, LoadingScreen
12. Wire up `main.tsx` with QueryClientProvider, RouterProvider, Toaster
13. Configure `vercel.json` for SPA routing

### Phase 2: High-Impact Pages (~25 files)
**Goal:** The 4 most-used pages that demonstrate the platform's power

**Dashboard Home:**
- KPI cards (animated count-up): Total portfolio value, today's price changes, active monitors, stock alerts
- Trending products carousel (horizontal scroll)
- Recent drop alerts feed
- Quick action buttons (Search Stock, Look Up Card, Check Drops)
- Live connection status indicator

**Stock Finder:**
- Hero search section with ZIP + product + retailer quick buttons
- Animated stats bar (stores found, in-stock, total units)
- Retailer filter chips
- Store result cards with stock levels, prices, buy links
- Empty state / no results animation
- `useStock` TanStack Query hook

**Card Lookup:**
- Search bar with type toggle (cards vs sealed)
- Card grid with hover preview
- Card detail view (nested route /cards/:id):
  - Large card image with variation selector
  - Price table (raw + all grades)
  - Interactive Recharts price chart (1M/3M/6M/1Y/2Y)
  - Recent sales list
  - Buy links grid
- `useCards`, `usePrices` hooks

**Set Database:**
- Set selector with series filter
- Set info hero card (logo, name, count, value index)
- Pull rates visualization (progress bars)
- Chase cards grid with rarity filter tabs
- Set statistics cards
- `useSets` hook

### Phase 3: Core Feature Pages (~20 files)
**Goal:** Drops, monitors, flip calculator, AI grading

**Drops Intel:**
- Tab toggle: Confirmed / Rumors / Live Intel
- Drop cards with countdown timer, retailer badges, product list
- Intel feed with source attribution icons (Reddit, PokeBeach, X, etc.)
- "Check Stock" inline action
- `useDrops` hook

**Monitors:**
- Auth gate (redirect to login if not authenticated)
- Discord webhook config card
- Create monitor form (animated expand)
- Monitor list with status badges, toggle switches, delete
- Runner status indicator with pulse animation
- `useMonitors` hook

**Flip Calculator:**
- Card search with auto-complete
- Input form: raw price, grading company, service tier
- Animated results reveal:
  - Grading cost breakdown
  - Grade probability distribution (horizontal bar chart)
  - Expected ROI with color coding (green/red)
  - Break-even analysis

**AI Grading:**
- Large drop zone with drag-and-drop animation
- Image preview with zoom
- Paste from clipboard support
- URL input alternative
- Grading results with animated grade reveal:
  - Large grade number with color ring
  - Subgrade bars (centering, corners, surface, edges)
  - Defects list
  - Estimated value range

### Phase 4: User Feature Pages (~20 files)
**Goal:** Portfolio, analytics, assistant, settings

**Portfolio:**
- Stats hero: total value, gain/loss (animated), items, ROI%
- Add item form with live price lookup
- Portfolio table/grid with sortable columns
- Inline P&L indicators (green/red arrows)
- Portfolio breakdown pie chart (Recharts)
- Refresh all prices button

**Analytics:**
- Stats overview cards
- Purchase tracking form + history table
- Stock accuracy donut chart
- Spending breakdown (by retailer, by time period)
- Backtest runner with progress bar + results grid

**AI Assistant:**
- Chat interface with message bubbles
- Quick question chips
- Streaming response animation (typewriter effect)
- Market insights cards sidebar
- Alert rules management section

**Settings:**
- Grouped settings sections in cards
- Toggle switches for notifications, sounds, scanner
- API endpoint config with test button
- Address form
- Payment method cards (link to Stripe/PayPal)
- Retailer account links
- Data export/import
- Danger zone (red border card)

### Phase 5: Polish & Deploy (~10 files)
**Goal:** Vending map, auth flow, mobile refinements, deploy

**Vending Map:**
- React-Leaflet map with custom Pokeball markers
- Location search by ZIP
- Location detail cards on marker click

**Auth Flow:**
- Login page with Discord OAuth button
- Callback handler
- Protected route wrapper
- User menu dropdown (avatar, name, logout)

**Mobile Polish:**
- Bottom nav bar with 5 key tabs
- Swipe gestures between pages
- Touch-optimized card sizes
- Sheet-style modals (slide up from bottom)

**Deployment:**
- Vercel config (SPA rewrites, headers)
- Environment variables for API URL
- Build optimization (code splitting, lazy routes)
- Meta tags, OG images, favicon

---

## Total Estimated Files: ~115+ source files
## Total Estimated Lines: ~15,000-20,000 lines of TypeScript/TSX

---

## Key Architectural Decisions

1. **SPA on Vercel** — No SSR needed since all data comes from the Flask API
2. **TanStack Query for ALL API calls** — Built-in caching replaces the custom IndexedDB layer for API responses. Portfolio/purchases still use localStorage via Zustand persist
3. **Lazy-loaded routes** — Each page is code-split for fast initial load
4. **Framer Motion everywhere** — Page transitions, list animations, hover effects, loading states
5. **No component library dependency** — Custom UI primitives inspired by shadcn/ui patterns (full control, no bloat)
6. **Existing Flask backend unchanged** — Frontend just calls the same endpoints
7. **TypeScript strict mode** — Full type safety for all API responses and state
