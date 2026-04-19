import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MapPin, Search, Navigation, ExternalLink, Loader2 } from 'lucide-react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import type { LatLngExpression } from 'leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { PageTransition } from '@/components/layout/PageTransition'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { staggerContainer, staggerItem, fadeInUp } from '@/lib/animations'
import { useVendingLocations } from '@/hooks/useApi'
import type { VendingLocation } from '@/lib/api'

// Fix default-marker icons under Vite (Leaflet assumes a /static path by default)
const DefaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
})
L.Marker.prototype.options.icon = DefaultIcon

const FALLBACK_CENTER: LatLngExpression = [39.5, -98.35] // geographic USA center

function MapCenterUpdater({ center }: { center: LatLngExpression | null }) {
  const map = useMap()
  if (center) {
    map.flyTo(center, 10, { duration: 0.8 })
  }
  return null
}

export default function Vending() {
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState<{ zip?: string; city?: string; state?: string; radius?: number }>({})
  const [selectedLocation, setSelectedLocation] = useState<VendingLocation | null>(null)

  const { data, isPending, isError, error } = useVendingLocations({
    ...query,
    radius: query.zip ? 50 : undefined,
  })

  const locations = data?.data ?? []
  const stats = data?.stats

  const handleSearch = () => {
    const s = searchInput.trim()
    if (!s) { setQuery({}); return }
    if (/^\d{5}$/.test(s)) {
      setQuery({ zip: s })
    } else if (/^[A-Za-z]{2}$/.test(s)) {
      setQuery({ state: s.toUpperCase() })
    } else {
      setQuery({ city: s })
    }
  }

  const clearSearch = () => { setSearchInput(''); setQuery({}) }

  const mapCenter: LatLngExpression = selectedLocation
    ? [selectedLocation.lat, selectedLocation.lng]
    : locations.length > 0
      ? [locations[0].lat, locations[0].lng]
      : FALLBACK_CENTER

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <h1 className="font-display text-4xl sm:text-5xl leading-none tracking-tight-er text-foreground">Vending Machine Map</h1>
          <p className="text-muted-foreground/60 text-sm mt-1">
            Find Pokemon TCG vending machines near you
            {stats && ` · ${stats.total_locations} locations · ${stats.verified} verified · ${stats.states_covered} states`}
          </p>
        </div>

        {/* Search */}
        <Card variant="elevated">
          <CardContent className="p-4">
            <div className="flex gap-3">
              <Input
                placeholder="Search by ZIP code, city, or state..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                icon={<Search className="w-4 h-4" />}
                className="flex-1"
              />
              <Button onClick={handleSearch}>
                <Navigation className="w-4 h-4 mr-1" /> Search
              </Button>
              {(query.zip || query.city || query.state) && (
                <Button variant="ghost" onClick={clearSearch}>Clear</Button>
              )}
            </div>
          </CardContent>
        </Card>

        {isPending ? (
          <div className="flex items-center justify-center py-16 text-muted text-sm gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading locations…
          </div>
        ) : isError ? (
          <EmptyState
            icon={<MapPin />}
            title="Couldn't load vending locations"
            description={error instanceof Error ? error.message : 'Unknown error'}
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Live Map */}
            <div className="lg:col-span-2">
              <Card variant="elevated" className="overflow-hidden">
                <div className="h-[500px] relative">
                  <MapContainer
                    center={mapCenter}
                    zoom={locations.length > 0 ? 5 : 4}
                    style={{ height: '100%', width: '100%' }}
                    scrollWheelZoom
                  >
                    <TileLayer
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    />
                    {selectedLocation && <MapCenterUpdater center={[selectedLocation.lat, selectedLocation.lng]} />}
                    {locations.map((loc) => (
                      <Marker
                        key={loc.id}
                        position={[loc.lat, loc.lng]}
                        eventHandlers={{ click: () => setSelectedLocation(loc) }}
                      >
                        <Popup>
                          <div style={{ minWidth: 180 }}>
                            <strong>{loc.name}</strong>
                            <div style={{ fontSize: 12, color: '#555' }}>
                              {loc.address}<br />
                              {loc.city}, {loc.state} {loc.zip}
                            </div>
                            {loc.products.length > 0 && (
                              <div style={{ fontSize: 11, marginTop: 4 }}>
                                {loc.products.join(', ')}
                              </div>
                            )}
                          </div>
                        </Popup>
                      </Marker>
                    ))}
                  </MapContainer>
                </div>
              </Card>
            </div>

            {/* Location List */}
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
              <p className="text-sm text-muted font-medium">{locations.length} locations</p>
              {locations.length === 0 ? (
                <p className="text-xs text-muted">No locations match your search.</p>
              ) : (
                <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
                  {locations.map((loc) => (
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
                            {loc.distance_miles != null && (
                              <span className="ml-auto font-mono-numbers text-accent">
                                {loc.distance_miles} mi
                              </span>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {loc.products.map((p) => (
                              <span key={p} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-hover text-muted">
                                {p}
                              </span>
                            ))}
                          </div>
                          <p className="text-[10px] text-muted-foreground mt-2">
                            Verified {loc.last_verified}
                          </p>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </div>
          </div>
        )}

        {/* Selected Location Detail */}
        <AnimatePresence>
          {selectedLocation && (
            <motion.div variants={fadeInUp} initial="initial" animate="animate" exit={{ opacity: 0, y: 10 }}>
              <Card variant="accent">
                <CardContent className="p-4 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{selectedLocation.name}</h3>
                    <p className="text-sm text-muted">
                      {selectedLocation.address}, {selectedLocation.city}, {selectedLocation.state} {selectedLocation.zip}
                    </p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {selectedLocation.products.map((p) => (
                        <Badge key={p} variant="default">{p}</Badge>
                      ))}
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      window.open(
                        `https://maps.google.com/?q=${selectedLocation.lat},${selectedLocation.lng}`,
                        '_blank'
                      )
                    }
                  >
                    <ExternalLink className="w-4 h-4 mr-1" /> Directions
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  )
}
