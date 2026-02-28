import { useState } from 'react'
import { motion } from 'framer-motion'
import { MapPin, Search, Navigation, ExternalLink } from 'lucide-react'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { staggerContainer, staggerItem, fadeInUp } from '@/lib/animations'

interface VendingLocation {
  id: string
  name: string
  address: string
  city: string
  state: string
  zip: string
  lat: number
  lng: number
  verified: boolean
  lastVerified: string
  products: string[]
}

const LOCATIONS: VendingLocation[] = [
  { id: '1', name: 'Westfield Mall', address: '1 Westfield Pl', city: 'San Francisco', state: 'CA', zip: '94103', lat: 37.7849, lng: -122.4094, verified: true, lastVerified: '2 days ago', products: ['Booster Packs', 'Promo Cards', 'Pin Collections'] },
  { id: '2', name: 'South Coast Plaza', address: '3333 Bristol St', city: 'Costa Mesa', state: 'CA', zip: '92626', lat: 33.6914, lng: -117.8827, verified: true, lastVerified: '1 week ago', products: ['Booster Packs', 'ETBs', 'Tins'] },
  { id: '3', name: 'King of Prussia Mall', address: '160 N Gulph Rd', city: 'King of Prussia', state: 'PA', zip: '19406', lat: 40.0878, lng: -75.3930, verified: true, lastVerified: '3 days ago', products: ['Booster Packs', 'Promo Cards'] },
  { id: '4', name: 'Mall of America', address: '60 E Broadway', city: 'Bloomington', state: 'MN', zip: '55425', lat: 44.8549, lng: -93.2422, verified: true, lastVerified: '5 days ago', products: ['Booster Packs', 'Mini Tins', 'Promo Cards'] },
  { id: '5', name: 'Galleria Dallas', address: '13350 Dallas Pkwy', city: 'Dallas', state: 'TX', zip: '75240', lat: 32.9309, lng: -96.8220, verified: false, lastVerified: '2 weeks ago', products: ['Booster Packs'] },
  { id: '6', name: 'Aventura Mall', address: '19501 Biscayne Blvd', city: 'Aventura', state: 'FL', zip: '33180', lat: 25.9569, lng: -80.1421, verified: true, lastVerified: '1 day ago', products: ['Booster Packs', 'ETBs', 'Promo Cards', 'Blister Packs'] },
  { id: '7', name: 'Fashion Show Mall', address: '3200 Las Vegas Blvd', city: 'Las Vegas', state: 'NV', zip: '89109', lat: 36.1280, lng: -115.1710, verified: true, lastVerified: '4 days ago', products: ['Booster Packs', 'Tins', 'Pin Collections'] },
  { id: '8', name: 'Tysons Corner Center', address: '1961 Chain Bridge Rd', city: 'McLean', state: 'VA', zip: '22102', lat: 38.9187, lng: -77.2271, verified: false, lastVerified: '3 weeks ago', products: ['Booster Packs'] },
]

export default function Vending() {
  const [searchZip, setSearchZip] = useState('')
  const [filteredLocations, setFilteredLocations] = useState(LOCATIONS)
  const [selectedLocation, setSelectedLocation] = useState<VendingLocation | null>(null)

  const handleSearch = () => {
    if (!searchZip.trim()) {
      setFilteredLocations(LOCATIONS)
      return
    }
    const filtered = LOCATIONS.filter(l =>
      l.zip.startsWith(searchZip) || l.state.toLowerCase().includes(searchZip.toLowerCase()) || l.city.toLowerCase().includes(searchZip.toLowerCase())
    )
    setFilteredLocations(filtered.length > 0 ? filtered : LOCATIONS)
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-[-0.02em] text-foreground">Vending Machine Map</h1>
          <p className="text-muted-foreground/60 text-sm mt-1">Find Pokemon TCG vending machines near you</p>
        </div>

        {/* Search */}
        <Card variant="elevated">
          <CardContent className="p-4">
            <div className="flex gap-3">
              <Input
                placeholder="Search by ZIP code, city, or state..."
                value={searchZip}
                onChange={(e) => setSearchZip(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                icon={<Search className="w-4 h-4" />}
                className="flex-1"
              />
              <Button onClick={handleSearch}>
                <Navigation className="w-4 h-4 mr-1" /> Search
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Map Placeholder */}
          <div className="lg:col-span-2">
            <Card variant="elevated" className="overflow-hidden">
              <div className="h-[500px] bg-gradient-to-br from-surface-hover to-surface relative flex items-center justify-center">
                <div className="text-center">
                  <MapPin className="w-16 h-16 mx-auto text-accent/30 mb-4" />
                  <p className="text-muted text-sm">Interactive map loads with React-Leaflet</p>
                  <p className="text-muted-foreground text-xs mt-1">{filteredLocations.length} locations found</p>
                </div>
                {/* Map dots visualization */}
                <div className="absolute inset-0">
                  {filteredLocations.map((loc, i) => (
                    <motion.button
                      key={loc.id}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: i * 0.05 }}
                      onClick={() => setSelectedLocation(loc)}
                      className={`absolute w-4 h-4 rounded-full border-2 border-background cursor-pointer transition-transform hover:scale-150 ${
                        selectedLocation?.id === loc.id ? 'bg-accent scale-150' : loc.verified ? 'bg-success' : 'bg-warning'
                      }`}
                      style={{
                        left: `${20 + Math.random() * 60}%`,
                        top: `${15 + Math.random() * 70}%`,
                      }}
                    />
                  ))}
                </div>
              </div>
            </Card>
          </div>

          {/* Location List */}
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            <p className="text-sm text-muted font-medium">{filteredLocations.length} locations</p>
            <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
              {filteredLocations.map((loc) => (
                <motion.div key={loc.id} variants={staggerItem}>
                  <Card
                    hover
                    className={`cursor-pointer transition-all ${selectedLocation?.id === loc.id ? 'border-accent' : ''}`}
                    onClick={() => setSelectedLocation(loc)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between mb-1">
                        <h3 className="text-sm font-semibold">{loc.name}</h3>
                        <Badge variant={loc.verified ? 'success' : 'warning'} className="text-[10px] shrink-0">
                          {loc.verified ? 'Verified' : 'Unverified'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-muted mb-2">
                        <MapPin className="w-3 h-3" />
                        {loc.city}, {loc.state} {loc.zip}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {loc.products.map((p) => (
                          <span key={p} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-hover text-muted">{p}</span>
                        ))}
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-2">Verified {loc.lastVerified}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>

        {/* Selected Location Detail */}
        {selectedLocation && (
          <motion.div variants={fadeInUp} initial="initial" animate="animate">
            <Card variant="accent">
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{selectedLocation.name}</h3>
                  <p className="text-sm text-muted">{selectedLocation.address}, {selectedLocation.city}, {selectedLocation.state} {selectedLocation.zip}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {selectedLocation.products.map((p) => (
                      <Badge key={p} variant="default">{p}</Badge>
                    ))}
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={() => window.open(`https://maps.google.com/?q=${selectedLocation.lat},${selectedLocation.lng}`, '_blank')}>
                  <ExternalLink className="w-4 h-4 mr-1" /> Directions
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </PageTransition>
  )
}
