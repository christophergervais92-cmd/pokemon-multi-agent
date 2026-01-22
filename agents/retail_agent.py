#!/usr/bin/env python3
import argparse
import json

from db import get_or_create_product


parser = argparse.ArgumentParser(description="Retail scan agent for Pokemon products")
parser.add_argument("--set-name", required=True, help="Pokemon set name to scan")
args = parser.parse_args()

# NOTE: This is still a static example list of products.
# In a real deployment you would replace this with live retailer/API calls.
products = [
    {
        "name": "Elite Trainer Box",
        "retailer": "Target",
        "price": 49.99,
        "url": "https://example.com/paldean-fates-etb",
        "stock": True,
    }
]

for p in products:
    product_id = get_or_create_product(
        set_name=args.set_name,
        name=p["name"],
        retailer=p["retailer"],
        url=p.get("url"),
    )
    p["product_id"] = product_id

result = {
    "success": True,
    "set_name": args.set_name,
    "products": products,
}

print(json.dumps(result))
