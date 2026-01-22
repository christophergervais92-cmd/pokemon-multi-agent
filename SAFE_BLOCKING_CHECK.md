# Safe Blocking Status Check

## ✅ Safe Method (No HTTP Requests)

Use `check_blocking_status.py` - it only reads the local file, no HTTP requests:

```bash
# Check all retailers
python3 check_blocking_status.py

# Check specific retailer
python3 check_blocking_status.py target
python3 check_blocking_status.py bestbuy
```

**Or use the API endpoint:**
```bash
curl http://localhost:5001/scanner/blocked
```

## ⚠️ Unsafe Methods (Make HTTP Requests)

**DO NOT USE** if you're already blocked:
- `test_blocking.py` - Makes HTTP requests to check blocking
- `test_blocking_detailed.py` - Makes multiple HTTP requests

These can make blocking worse by adding more requests.

## How It Works

The safe checker:
1. Reads `.stock_cache/blocked_retailers.json` (local file only)
2. Checks timestamps to see if blocks have expired
3. Calculates time remaining until unblock
4. **Never makes HTTP requests**

## Example Output

```
======================================================================
🔍 SAFE BLOCKING STATUS CHECK
======================================================================
(No HTTP requests made - only reads local file)

Total in Blocked List: 2
Currently Blocked: 1
Unblocked (expired): 1

Retailer Status:
----------------------------------------------------------------------

target:
  Status: 🚫 BLOCKED
  Blocked At: 2026-01-21T04:00:00
  Hours Since Block: 0.5
  Hours Remaining: 0.5

bestbuy:
  Status: ✅ UNBLOCKED
  Blocked At: 2026-01-21T02:00:00
  Hours Since Block: 2.5
```

## When to Use

✅ **Safe to use anytime:**
- `check_blocking_status.py`
- `/scanner/blocked` endpoint
- Checking blocked_retailers.json directly

❌ **Only use for initial diagnosis:**
- `test_blocking.py` (makes HTTP requests)
- `test_blocking_detailed.py` (makes HTTP requests)

## Recommendation

**Always use the safe method** unless you need to verify actual HTTP responses for initial setup. Once you know you're blocked, use the safe checker to monitor when blocks expire.
