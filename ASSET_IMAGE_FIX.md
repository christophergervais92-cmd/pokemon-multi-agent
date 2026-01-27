# Asset Image Fix - Umbreon VMAX Alt Art (Moonbreon)

## Problem
The "Umbreon VMAX Alt Art PSA 10" asset was displaying the wrong card image (Flannery trainer card instead of the moonbreon).

## Solution

### Backend Asset Configuration Updated
Added `image_url` and `card_number` fields to asset configs in `agents/agents_server.py`:

**`umbreon-vmax-alt-psa10`:**
- `card_name`: "Umbreon VMAX"
- `set_name`: "Evolving Skies"
- `card_number`: "215/203" (Alt Art Secret Rare - the moonbreon)
- `image_url`: `https://images.pokemontcg.io/swsh6/215_hires.png`

**Other assets also updated:**
- `charizard-base-psa10`: Added image URL for Base Set Charizard
- `moonbreon-raw`: Added image URL for Umbreon V (regular, not VMAX)

### API Endpoint
The `/market/asset/<asset_id>` endpoint now returns `image_url`:

```bash
curl http://127.0.0.1:5001/market/asset/umbreon-vmax-alt-psa10
```

Returns:
```json
{
  "success": true,
  "asset_id": "umbreon-vmax-alt-psa10",
  "card_name": "Umbreon VMAX",
  "set_name": "Evolving Skies",
  "card_number": "215/203",
  "image_url": "https://images.pokemontcg.io/swsh6/215_hires.png",
  "category": "slabs",
  "grade": "PSA 10"
}
```

## Frontend Updates

### Dashboard (`dashboard.html`) – **DONE**
- Added `ASSET_IMAGE_OVERRIDES` and `getAssetImageOverride(card)`.
- Override used in: Card Lookup detail, chase cards grid, search results grid, quick search dropdown, flip calculator grid, variation select.
- **Umbreon VMAX** from **Evolving Skies** (including 215/203) now always uses the moonbreon image.

### Other frontends (e.g. `preview.html` in `pokemon_perp_dex`)
- Fetch `/market/asset/<asset_id>` and use `image_url` when displaying that asset.

## Card Reference

**Moonbreon (Umbreon VMAX Alt Art):**
- Set: Evolving Skies (SWSH6)
- Card Number: 215/203
- Image URL: `https://images.pokemontcg.io/swsh6/215_hires.png`
- This is the Alt Art Secret Rare version (the popular "moonbreon")

**Note:** There's also a regular Umbreon V (189/203) in Evolving Skies, but the moonbreon is the VMAX Alt Art at 215/203.
