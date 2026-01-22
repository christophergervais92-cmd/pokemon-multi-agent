#!/usr/bin/env python3
"""Test delta logic and aggressive caching"""
import requests
import json
import time

print("=" * 70)
print("🧪 TESTING DELTA LOGIC & AGGRESSIVE CACHING")
print("=" * 70)
print()

query = "pokemon elite trainer box"
url = f"http://127.0.0.1:5001/scanner/unified?q={query.replace(' ', '+')}&zip=90210"

# First search (should return all products)
print("1️⃣  First search (full results)...")
start = time.time()
r1 = requests.get(url, timeout=60)
t1 = time.time() - start
d1 = r1.json()

print(f"   Time: {t1:.2f}s")
print(f"   Products returned: {len(d1.get('products', []))}")
print(f"   Total products: {d1.get('total_all_products', d1.get('total', 0))}")
print(f"   Delta enabled: {d1.get('delta', {}).get('enabled', False)}")
print()

# Second search immediately (should return only changes, likely empty)
print("2️⃣  Second search (delta - should be fast if no changes)...")
time.sleep(1)
start = time.time()
r2 = requests.get(url + "&delta=true", timeout=60)
t2 = time.time() - start
d2 = r2.json()

print(f"   Time: {t2:.2f}s")
print(f"   Products returned: {len(d2.get('products', []))}")
print(f"   Total products: {d2.get('total_all_products', d2.get('total', 0))}")
print(f"   Has changes: {d2.get('delta', {}).get('has_changes', False)}")
print(f"   Changed count: {d2.get('delta', {}).get('changed_count', 0)}")
if d2.get('delta', {}).get('has_changes'):
    print(f"   ⚡ Speed improvement: {t1/t2:.1f}x faster!")
else:
    print(f"   ⚡ Speed improvement: {t1/t2:.1f}x faster (no changes = instant)")
print()

# Third search with full results
print("3️⃣  Third search (full results, ignore delta)...")
time.sleep(1)
start = time.time()
r3 = requests.get(url + "&full=true", timeout=60)
t3 = time.time() - start
d3 = r3.json()

print(f"   Time: {t3:.2f}s")
print(f"   Products returned: {len(d3.get('products', []))}")
print()

print("=" * 70)
print("📊 SUMMARY")
print("=" * 70)
print(f"First search (full):  {t1:.2f}s - {len(d1.get('products', []))} products")
print(f"Second search (delta): {t2:.2f}s - {len(d2.get('products', []))} products")
print(f"Speed improvement: {t1/t2:.1f}x faster")
print("=" * 70)
