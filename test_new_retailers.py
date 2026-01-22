#!/usr/bin/env python3
"""Test the new retailers (Costco, Barnes & Noble, Amazon)"""
import requests
import json

response = requests.get("http://127.0.0.1:5001/scanner/unified?q=pokemon+elite+trainer+box&zip=90210")
data = response.json()

print("=" * 70)
print("📊 NEW RETAILERS TEST")
print("=" * 70)
print(f"Total products: {data.get('total', 0)}")
print(f"In stock: {data.get('in_stock_count', 0)}")
print()

retailers = data.get('by_retailer', {})
print("Retailers checked:")
for k, v in sorted(retailers.items()):
    count = v.get('count', 0)
    in_stock = v.get('in_stock', 0)
    if count > 0:
        print(f"  ✅ {k}: {count} products ({in_stock} in stock)")
    else:
        print(f"  ⚠️  {k}: 0 products (may be blocked)")

print()
print("=" * 70)
