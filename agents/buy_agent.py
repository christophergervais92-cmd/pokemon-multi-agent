#!/usr/bin/env python3
import json
import sys
from typing import Any, Dict, List


input_data = sys.stdin.read() or "{}"
data = json.loads(input_data)

purchases: List[Dict[str, Any]] = []
for p in data.get("products", [])[:2]:
    purchases.append(
        {
            "product": p["name"],
            "retailer": p["retailer"],
            "price": p["price"],
            "success": True,
            "purchase_id": "SIM12345",
        }
    )

alerts_from_grading = data.get("alerts", [])

result: Dict[str, Any] = {
    "set_name": data.get("set_name"),
    "purchase_count": len(purchases),
    "purchases": purchases,
    "simulation_mode": True,
}

if alerts_from_grading:
    result["alerts"] = alerts_from_grading

print(json.dumps(result))
