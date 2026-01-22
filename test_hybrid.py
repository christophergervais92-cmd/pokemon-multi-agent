#!/usr/bin/env python3
"""Test the hybrid approach (requests + browser fallback)"""
import requests
import json
import time

print("=" * 70)
print("🧪 TESTING HYBRID APPROACH")
print("=" * 70)
print()

start_time = time.time()

response = requests.get("http://127.0.0.1:5001/scanner/unified?q=pokemon+elite+trainer+box&zip=90210", timeout=120)
data = response.json()

elapsed = time.time() - start_time

print(f"⏱️  Total time: {elapsed:.1f} seconds")
print()

retailers = data.get('by_retailer', {})
print("Retailers checked:")
print()

for k, v in sorted(retailers.items()):
    count = v.get('count', 0)
    in_stock = v.get('in_stock', 0)
    method = v.get('method', 'requests')
    
    if count > 0:
        method_icon = "🌐" if method == "browser" else "⚡"
        print(f"  {method_icon} {k}: {count} products ({in_stock} in stock) - {method}")
    else:
        error = v.get('error', '')
        if 'blocked' in error.lower() or 'skip' in error.lower():
            print(f"  ⏭️  {k}: Skipped (blocked)")
        else:
            print(f"  ⚠️  {k}: 0 products - {error[:50]}")

print()
print("=" * 70)
print(f"Total products: {data.get('total', 0)}")
print(f"In stock: {data.get('in_stock_count', 0)}")
print("=" * 70)
