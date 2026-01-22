# Scanner Improvements Plan

## Current Issues

1. **Sequential Scanning** - Scans retailers one at a time (slow)
2. **No Retry Logic** - Single failure = no results
3. **Fragile Scraping** - Breaks when HTML changes
4. **Inaccurate Stock** - Pokemon Center showing wrong status
5. **Limited Error Handling** - Errors are silent
6. **Demo Data** - Walmart, Costco, Barnes & Noble use fake data

## Proposed Improvements

### 1. Parallel Scanning (Speed: 3-5x faster)
- Scan all retailers simultaneously using `concurrent.futures`
- Current: 5-10 seconds (sequential)
- Improved: 2-3 seconds (parallel)

### 2. Retry Logic with Exponential Backoff
- Retry failed requests 3 times
- Exponential backoff: 1s, 2s, 4s
- Handle 429 (rate limit) gracefully

### 3. Use StealthSession (Better Anti-Detection)
- Replace basic `requests` with `StealthSession`
- Better headers, cookies, delays
- Reduces blocking risk

### 4. Multiple Stock Detection Methods
- Check multiple indicators:
  - "Add to Cart" button presence
  - "Out of Stock" text
  - Price availability
  - Stock status API (if available)
- Vote-based system (2+ indicators = in stock)

### 5. Fuzzy Product Matching
- Use `difflib` for better name matching
- Handle typos: "destined rivels" → "Destined Rivals"
- Set name normalization

### 6. Real-Time Stock Verification
- Double-check stock status for "in stock" items
- Verify by attempting to get product page
- Mark as "unverified" if check fails

### 7. Better Error Handling
- Log all errors with context
- Return partial results (don't fail completely)
- Show which retailers succeeded/failed

### 8. Add More Retailers
- Walmart (real scraper)
- Amazon (API or scraper)
- Barnes & Noble (real scraper)
- Costco (real scraper)

### 9. Caching Improvements
- Cache successful results longer (5 min)
- Cache failures shorter (30 sec)
- Invalidate cache on errors

### 10. Stock Confidence Score
- Rate stock status confidence (0-100%)
- Based on:
  - Number of indicators checked
  - API vs scrape (API = higher confidence)
  - Recent verification timestamp

## Implementation Priority

**High Priority (Immediate Impact):**
1. Parallel scanning
2. Retry logic
3. Use StealthSession
4. Better error handling

**Medium Priority (Accuracy):**
5. Multiple stock detection
6. Fuzzy matching
7. Stock confidence score

**Low Priority (Nice to Have):**
8. More retailers
9. Real-time verification
10. Advanced caching

## Expected Results

- **Speed:** 3-5x faster (5-10s → 2-3s)
- **Accuracy:** 20-30% improvement
- **Reliability:** 50% fewer failures
- **Coverage:** More retailers with real data
