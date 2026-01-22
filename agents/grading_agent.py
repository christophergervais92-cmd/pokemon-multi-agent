#!/usr/bin/env python3
import json
import sys
from typing import Any, Dict, List


def evaluate_product(product: Dict[str, Any]) -> Dict[str, Any]:
    pricing = product.get("pricing", {})
    delta_pct = float(pricing.get("delta_pct", 0.0))
    confidence = float(pricing.get("confidence", 0.0))

    # Very simple logic:
    # - Strong buy if price is 20%+ under market and confidence is high
    # - Otherwise neutral
    should_buy = delta_pct <= -0.2 and confidence >= 0.75
    roi_estimate = 1.0 - delta_pct if should_buy else 1.0

    reason_parts: List[str] = []
    if should_buy:
        reason_parts.append("Listed significantly under market")
    if confidence >= 0.8:
        reason_parts.append("High price estimate confidence")

    if not reason_parts:
        reason_parts.append("No strong edge detected")

    evaluation = {
        "grade_expectation": "PSA 10",  # placeholder for a real grading model
        "roi_estimate": round(roi_estimate, 2),
        "should_buy": should_buy,
        "reason": "; ".join(reason_parts),
    }

    return evaluation


input_data = sys.stdin.read() or "{}"
data = json.loads(input_data)

alerts: List[Dict[str, Any]] = []

for p in data.get("products", []):
    p["evaluation"] = evaluate_product(p)

    # Generate a simple stock/price alert if the card looks attractive and is in stock
    if p.get("evaluation", {}).get("should_buy") and p.get("stock"):
        alerts.append(
            {
                "type": "BUY_SIGNAL",
                "set_name": data.get("set_name"),
                "product_name": p.get("name"),
                "retailer": p.get("retailer"),
                "price": p.get("price"),
                "market_price": p.get("pricing", {}).get("market_price"),
                "delta_pct": p.get("pricing", {}).get("delta_pct"),
                "reason": p.get("evaluation", {}).get("reason"),
            }
        )

data["decision"] = {
    "approved": any(a["type"] == "BUY_SIGNAL" for a in alerts),
    "max_quantity": 2,
    "risk_score": 0.2 if alerts else 0.6,
}

if alerts:
    data["alerts"] = alerts

print(json.dumps(data))
