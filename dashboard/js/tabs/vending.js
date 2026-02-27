// PokeAgent - Vending Machine Map Tab
// =============================================================================
// Leaflet-based map showing Pokemon vending machine locations across the US.
// Depends on globals: settings (from state.js), L (Leaflet library, lazy-loaded)
// =============================================================================

// Pokemon Vending Machine Database (sourced from pokevend.us)
const VENDING_MACHINES = [
    // California
    { id: 1, name: 'Walmart Supercenter', address: '1601 N Victory Pl, Burbank, CA 91502', zip: '91502', lat: 34.1808, lng: -118.3090, type: 'Retail' },
    { id: 2, name: 'Walmart Supercenter', address: '2770 E Carson St, Lakewood, CA 90712', zip: '90712', lat: 33.8317, lng: -118.1170, type: 'Retail' },
    { id: 3, name: 'Walmart Supercenter', address: '8500 Washington Blvd, Pico Rivera, CA 90660', zip: '90660', lat: 33.9831, lng: -118.0967, type: 'Retail' },
    { id: 4, name: 'Walmart Supercenter', address: '4101 Crenshaw Blvd, Los Angeles, CA 90008', zip: '90008', lat: 34.0083, lng: -118.3304, type: 'Retail' },
    { id: 5, name: 'Target', address: '7100 Santa Monica Blvd, West Hollywood, CA 90046', zip: '90046', lat: 34.0906, lng: -118.3445, type: 'Retail' },
    { id: 6, name: 'Walmart Supercenter', address: '1827 W Katella Ave, Orange, CA 92867', zip: '92867', lat: 33.8011, lng: -117.8756, type: 'Retail' },
    { id: 7, name: 'Target', address: '2626 E Chapman Ave, Orange, CA 92869', zip: '92869', lat: 33.7870, lng: -117.8282, type: 'Retail' },
    // Texas
    { id: 8, name: 'Walmart Supercenter', address: '2727 N Grandview Ave, Odessa, TX 79761', zip: '79761', lat: 31.8778, lng: -102.3677, type: 'Retail' },
    { id: 9, name: 'Target', address: '4200 Westheimer Rd, Houston, TX 77027', zip: '77027', lat: 29.7369, lng: -95.4347, type: 'Retail' },
    { id: 10, name: 'Walmart Supercenter', address: '6425 N Mesa St, El Paso, TX 79912', zip: '79912', lat: 31.8456, lng: -106.5341, type: 'Retail' },
    { id: 11, name: 'Walmart Supercenter', address: '9300 N Central Expy, Dallas, TX 75231', zip: '75231', lat: 32.8786, lng: -96.7701, type: 'Retail' },
    { id: 12, name: 'Walmart Supercenter', address: '5501 S MoPac Expy, Austin, TX 78749', zip: '78749', lat: 30.2148, lng: -97.8012, type: 'Retail' },
    // Florida
    { id: 13, name: 'Walmart Supercenter', address: '8501 S Orange Blossom Trl, Orlando, FL 32809', zip: '32809', lat: 28.4566, lng: -81.3933, type: 'Retail' },
    { id: 14, name: 'Target', address: '3250 Airport-Pulling Rd N, Naples, FL 34105', zip: '34105', lat: 26.1789, lng: -81.7654, type: 'Retail' },
    { id: 15, name: 'Walmart Supercenter', address: '8745 NW 13th Terrace, Miami, FL 33172', zip: '33172', lat: 25.7865, lng: -80.3567, type: 'Retail' },
    { id: 16, name: 'Walmart Supercenter', address: '3101 W Hillsborough Ave, Tampa, FL 33614', zip: '33614', lat: 27.9987, lng: -82.5012, type: 'Retail' },
    // New York
    { id: 17, name: 'Walmart Supercenter', address: '100 Thruway Plaza, Cheektowaga, NY 14225', zip: '14225', lat: 42.9145, lng: -78.7456, type: 'Retail' },
    { id: 18, name: 'Target', address: '517 E 117th St, New York, NY 10035', zip: '10035', lat: 40.7982, lng: -73.9341, type: 'Retail' },
    { id: 19, name: 'Walmart', address: '5765 Transit Rd, Depew, NY 14043', zip: '14043', lat: 42.9012, lng: -78.7123, type: 'Retail' },
    // Ohio
    { id: 20, name: 'Walmart Supercenter', address: '3615 Soldano Blvd, Columbus, OH 43228', zip: '43228', lat: 39.9651, lng: -83.1456, type: 'Retail' },
    { id: 21, name: 'Target', address: '3100 W Henderson Rd, Columbus, OH 43220', zip: '43220', lat: 40.0567, lng: -83.0654, type: 'Retail' },
    { id: 22, name: 'Walmart Supercenter', address: '13255 Shaker Blvd, Cleveland, OH 44120', zip: '44120', lat: 41.4764, lng: -81.5678, type: 'Retail' },
    // Arizona
    { id: 23, name: 'Walmart Supercenter', address: '7575 W Lower Buckeye Rd, Phoenix, AZ 85043', zip: '85043', lat: 33.4312, lng: -112.1987, type: 'Retail' },
    { id: 24, name: 'Target', address: '1515 N 75th Ave, Phoenix, AZ 85035', zip: '85035', lat: 33.4534, lng: -112.2145, type: 'Retail' },
    { id: 25, name: 'Walmart Supercenter', address: '5803 E Broadway Blvd, Tucson, AZ 85711', zip: '85711', lat: 32.2212, lng: -110.8567, type: 'Retail' },
    // Illinois
    { id: 26, name: 'Target', address: '1 S State St, Chicago, IL 60603', zip: '60603', lat: 41.8814, lng: -87.6278, type: 'Retail' },
    { id: 27, name: 'Walmart Supercenter', address: '4650 W North Ave, Chicago, IL 60639', zip: '60639', lat: 41.9103, lng: -87.7456, type: 'Retail' },
    { id: 28, name: 'Walmart Supercenter', address: '4005 167th St, Country Club Hills, IL 60478', zip: '60478', lat: 41.5567, lng: -87.7234, type: 'Retail' },
    // Georgia
    { id: 29, name: 'Walmart Supercenter', address: '2427 Gresham Rd SE, Atlanta, GA 30316', zip: '30316', lat: 33.7234, lng: -84.3145, type: 'Retail' },
    { id: 30, name: 'Target', address: '3535 Peachtree Rd NE, Atlanta, GA 30326', zip: '30326', lat: 33.8512, lng: -84.3623, type: 'Retail' },
    // Washington
    { id: 31, name: 'Walmart Supercenter', address: '18330 E Valley Hwy, Kent, WA 98032', zip: '98032', lat: 47.4123, lng: -122.2245, type: 'Retail' },
    { id: 32, name: 'Target', address: '1401 2nd Ave, Seattle, WA 98101', zip: '98101', lat: 47.6092, lng: -122.3371, type: 'Retail' },
    // Nevada
    { id: 33, name: 'Walmart Supercenter', address: '3615 S Rainbow Blvd, Las Vegas, NV 89103', zip: '89103', lat: 36.1234, lng: -115.2345, type: 'Retail' },
    { id: 34, name: 'Target', address: '2189 N Rainbow Blvd, Las Vegas, NV 89108', zip: '89108', lat: 36.1987, lng: -115.2456, type: 'Retail' },
    // Pennsylvania
    { id: 35, name: 'Walmart Supercenter', address: '1675 S Christopher Columbus Blvd, Philadelphia, PA 19148', zip: '19148', lat: 39.9145, lng: -75.1467, type: 'Retail' },
    { id: 36, name: 'Target', address: '2501 E Allegheny Ave, Philadelphia, PA 19134', zip: '19134', lat: 39.9945, lng: -75.1123, type: 'Retail' },
    // New Jersey
    { id: 37, name: 'Walmart Supercenter', address: '1 Pond Rd, Freehold, NJ 07728', zip: '07728', lat: 40.2345, lng: -74.2867, type: 'Retail' },
    { id: 38, name: 'Target', address: '101 Town Center Blvd, Sewell, NJ 08080', zip: '08080', lat: 39.7512, lng: -75.0834, type: 'Retail' },
    // Michigan
    { id: 39, name: 'Walmart Supercenter', address: '29555 Plymouth Rd, Livonia, MI 48150', zip: '48150', lat: 42.3723, lng: -83.4267, type: 'Retail' },
    { id: 40, name: 'Target', address: '3749 28th St SE, Grand Rapids, MI 49512', zip: '49512', lat: 42.9234, lng: -85.5523, type: 'Retail' },
    // Colorado
    { id: 41, name: 'Walmart Supercenter', address: '9400 E Hampden Ave, Denver, CO 80231', zip: '80231', lat: 39.6512, lng: -104.8923, type: 'Retail' },
    { id: 42, name: 'Target', address: '8000 E Quincy Ave, Denver, CO 80237', zip: '80237', lat: 39.6345, lng: -104.8987, type: 'Retail' },
    // Minnesota
    { id: 43, name: 'Target', address: '900 Nicollet Mall, Minneapolis, MN 55403', zip: '55403', lat: 44.9742, lng: -93.2711, type: 'Retail' },
    { id: 44, name: 'Walmart Supercenter', address: '5800 Shingle Creek Pkwy, Brooklyn Center, MN 55430', zip: '55430', lat: 45.0734, lng: -93.3145, type: 'Retail' },
    // North Carolina
    { id: 45, name: 'Walmart Supercenter', address: '3475 Apex Peakway, Apex, NC 27502', zip: '27502', lat: 35.7323, lng: -78.8534, type: 'Retail' },
    { id: 46, name: 'Target', address: '8120 Renaissance Pkwy, Durham, NC 27713', zip: '27713', lat: 35.9234, lng: -78.9456, type: 'Retail' },
];

// Vending Map State
let vendingMap = null;
let vendingMarkers = [];
let pokemonIcon = null;

// ---------------------------------------------------------------------------
// Map initialization
// ---------------------------------------------------------------------------
function initVendingMap() {
    if (vendingMap) return;
    if (typeof L === 'undefined') {
        console.log('Leaflet not loaded yet');
        return;
    }

    const mapContainer = document.getElementById('vendingMap');
    if (!mapContainer) return;

    // Custom Pokemon-themed marker icon
    if (!pokemonIcon) {
        pokemonIcon = L.divIcon({
            className: 'pokemon-marker',
            html: `<div style="
                width: 32px; height: 32px;
                background: linear-gradient(135deg, #ffcb05 0%, #3466af 100%);
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                border: 3px solid white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                display: flex; align-items: center; justify-content: center;
            "><div style="
                transform: rotate(45deg);
                font-size: 14px;
                font-weight: bold;
            ">V</div></div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32]
        });
    }

    vendingMap = L.map('vendingMap').setView([39.8283, -98.5795], 4);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(vendingMap);

    // Add all vending machine markers
    VENDING_MACHINES.forEach(machine => {
        const marker = L.marker([machine.lat, machine.lng], { icon: pokemonIcon })
            .addTo(vendingMap)
            .bindPopup(`
                <div style="font-family: 'Outfit', sans-serif; min-width: 200px;">
                    <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #333;">${machine.name}</div>
                    <div style="font-size: 12px; color: #666; margin-bottom: 8px;">${machine.address}</div>
                    <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(machine.address)}"
                       target="_blank" rel="noopener"
                       style="display: inline-block; padding: 6px 12px; background: #3466af; color: white;
                              border-radius: 4px; text-decoration: none; font-size: 12px; font-weight: 500;">
                       Get Directions
                    </a>
                </div>
            `);
        vendingMarkers.push({ marker, machine });
    });

    // Machine count indicator
    const countDiv = L.control({ position: 'topright' });
    countDiv.onAdd = function() {
        const div = L.DomUtil.create('div', 'machine-count');
        div.innerHTML = `
            <div style="background: rgba(0,0,0,0.8); color: white; padding: 8px 12px; border-radius: 6px; font-family: 'Outfit', sans-serif; font-size: 12px;">
                <strong>${VENDING_MACHINES.length}</strong> vending machines
            </div>
        `;
        return div;
    };
    countDiv.addTo(vendingMap);
}

// ---------------------------------------------------------------------------
// Search by ZIP code
// ---------------------------------------------------------------------------
function searchVendingMap() {
    const zipInput = document.getElementById('vendingZip');
    const zip = zipInput?.value || settings.zip || '90210';
    const resultsDiv = document.getElementById('vendingResults');

    if (!zip || zip.length < 5) {
        alert('Please enter a valid 5-digit ZIP code');
        return;
    }

    // Find machines in the same zip code area (first 3 digits)
    const zipPrefix = zip.substring(0, 3);
    let nearbyMachines = VENDING_MACHINES.filter(m => m.zip.startsWith(zipPrefix));

    // Expand search if none found
    if (nearbyMachines.length === 0) {
        const zipPrefix2 = zip.substring(0, 2);
        nearbyMachines = VENDING_MACHINES.filter(m => m.zip.startsWith(zipPrefix2));
    }

    if (nearbyMachines.length === 0) {
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = `
            <div class="card" style="background: var(--bg-card); margin-top: 1rem;">
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 0.9rem; margin-bottom: 0.5rem; color: var(--text);">No vending machines found near ${zip}</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Showing all ${VENDING_MACHINES.length} locations on map</div>
                </div>
            </div>
        `;
        if (vendingMap) vendingMap.setView([39.8283, -98.5795], 4);
        return;
    }

    // Center map on found machines
    if (vendingMap && nearbyMachines.length > 0) {
        const bounds = L.latLngBounds(nearbyMachines.map(m => [m.lat, m.lng]));
        vendingMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
        const firstMachine = nearbyMachines[0];
        vendingMarkers.find(vm => vm.machine.id === firstMachine.id)?.marker.openPopup();
    }

    // Show results list
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `
        <div class="card" style="background: var(--bg-card); margin-top: 1rem;">
            <h3 style="font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--text);">
                ${nearbyMachines.length} vending machine${nearbyMachines.length > 1 ? 's' : ''} near ${zip}
            </h3>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                ${nearbyMachines.map(m => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--bg); border-radius: 6px; gap: 0.75rem;" onclick="focusVendingMarker(${m.id})" class="vending-item">
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-weight: 500; font-size: 0.85rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${m.name}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${m.address}</div>
                        </div>
                        <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(m.address)}"
                           target="_blank" rel="noopener"
                           class="btn btn-sm"
                           onclick="event.stopPropagation()"
                           style="white-space: nowrap; font-size: 0.7rem;">
                           Directions
                        </a>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function focusVendingMarker(machineId) {
    const vm = vendingMarkers.find(v => v.machine.id === machineId);
    if (vm && vendingMap) {
        vendingMap.setView([vm.machine.lat, vm.machine.lng], 14);
        vm.marker.openPopup();
    }
}

function initVendingOnSwitch() {
    setTimeout(() => {
        initVendingMap();
        if (vendingMap) vendingMap.invalidateSize();
    }, 100);
}
