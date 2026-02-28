import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Search, SlidersHorizontal, Package, CreditCard, AlertCircle, Loader2 } from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { staggerContainer, staggerItem } from '@/lib/animations'
import { formatPrice } from '@/lib/utils'
import { useCardSearch } from '@/hooks/useApi'

type SearchType = 'cards' | 'products'

const POPULAR_SETS = ['Prismatic Evolutions', 'Surging Sparks', '151', 'Paldean Fates', 'Evolving Skies', 'Obsidian Flames']

export default function Cards() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [searchType, setSearchType] = useState<SearchType>('cards')
  const [activeQuery, setActiveQuery] = useState(searchParams.get('q') || '')

  // Wire to real API via React Query
  const { data, isLoading, isError, error } = useCardSearch(activeQuery)
  const results = data?.data ?? []

  // If navigated here with ?q= param, auto-search
  useEffect(() => {
    const q = searchParams.get('q')
    if (q) {
      setQuery(q)
      setActiveQuery(q)
    }
  }, [searchParams])

  const handleSearch = () => {
    if (!query.trim()) return
    setActiveQuery(query.trim())
  }

  const rarityColor = (rarity: string) => {
    if (rarity.includes('Special Art') || rarity.includes('Hyper')) return 'accent'
    if (rarity.includes('Illustration') || rarity.includes('Secret')) return 'info'
    if (rarity.includes('Ultra') || rarity.includes('Full Art')) return 'warning'
    if (rarity.includes('Holo') || rarity.includes('Rare')) return 'success'
    return 'default'
  }

  const hasSearched = activeQuery.length >= 2

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Card Lookup</h1>
          <p className="text-muted-foreground/60 text-sm mt-1">Search cards, view prices, and find the best deals</p>
        </div>

        {/* Search Section */}
        <Card>
          <CardContent className="p-4">
            <div className="flex gap-3">
              {/* Search Type Toggle */}
              <div className="flex bg-surface rounded-lg p-1 shrink-0">
                <button
                  onClick={() => setSearchType('cards')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    searchType === 'cards' ? 'bg-accent text-white' : 'text-muted hover:text-foreground'
                  }`}
                >
                  <CreditCard className="w-4 h-4" /> Cards
                </button>
                <button
                  onClick={() => setSearchType('products')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    searchType === 'products' ? 'bg-accent text-white' : 'text-muted hover:text-foreground'
                  }`}
                >
                  <Package className="w-4 h-4" /> Products
                </button>
              </div>

              {/* Search Input */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder={searchType === 'cards' ? 'Search by card name, set, or number...' : 'Search sealed products...'}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full h-10 pl-10 pr-4 bg-surface border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none transition"
                />
              </div>

              <Button onClick={handleSearch} isLoading={isLoading}>
                Search
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="aspect-[2.5/3.5] w-full rounded-xl" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <EmptyState
            icon={<AlertCircle className="w-16 h-16" />}
            title="Search failed"
            description={error instanceof Error ? error.message : 'Failed to search cards. Make sure the backend is running.'}
          />
        ) : results.length > 0 ? (
          <>
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted">{data?.count ?? results.length} results found</p>
              <Button variant="ghost" size="sm">
                <SlidersHorizontal className="w-4 h-4 mr-1" /> Filters
              </Button>
            </div>

            <motion.div
              variants={staggerContainer}
              initial="initial"
              animate="animate"
              className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
            >
              {results.map((card) => (
                <motion.div key={card.id} variants={staggerItem}>
                  <Card
                    hover
                    className="cursor-pointer overflow-hidden group"
                    onClick={() => navigate(`/cards/${card.id}`)}
                  >
                    {/* Card Image */}
                    <div className="aspect-[2.5/3.5] bg-gradient-to-br from-surface-hover to-surface relative overflow-hidden">
                      {card.image ? (
                        <img
                          src={card.image}
                          alt={card.name}
                          className="absolute inset-0 w-full h-full object-contain"
                          loading="lazy"
                        />
                      ) : (
                        <div className="absolute inset-0 flex items-center justify-center">
                          <CreditCard className="w-12 h-12 text-border-light opacity-50" />
                        </div>
                      )}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>

                    {/* Card Info */}
                    <CardContent className="p-3 space-y-1.5">
                      <h3 className="text-sm font-semibold truncate">{card.name}</h3>
                      <p className="text-xs text-muted truncate">{card.set} · {card.number}</p>
                      <div className="flex items-center justify-between">
                        <Badge variant={rarityColor(card.rarity)} className="text-[10px]">
                          {card.rarity}
                        </Badge>
                        {card.price != null && (
                          <span className="text-sm font-mono-numbers font-bold text-accent">
                            ${formatPrice(card.price)}
                          </span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </>
        ) : hasSearched ? (
          <EmptyState
            icon={<Search className="w-16 h-16" />}
            title="No cards found"
            description="Try adjusting your search query or filters"
          />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {POPULAR_SETS.map((set) => (
              <Card
                key={set}
                hover
                className="cursor-pointer"
                onClick={() => { setQuery(set); setActiveQuery(set) }}
              >
                <CardContent className="p-4 text-center">
                  <div className="w-16 h-16 mx-auto mb-3 rounded-xl bg-gradient-to-br from-accent/20 to-pokemon-pink/20 flex items-center justify-center">
                    <CreditCard className="w-8 h-8 text-accent" />
                  </div>
                  <p className="text-sm font-semibold">{set}</p>
                  <p className="text-xs text-muted mt-1">Browse cards</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </PageTransition>
  )
}
