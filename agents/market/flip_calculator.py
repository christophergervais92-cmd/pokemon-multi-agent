#!/usr/bin/env python3
"""
Flip Calculator - Grading ROI Analysis

Calculates whether a card is worth grading based on:
- Current raw price
- Grading costs (PSA, CGC, BGS tiers)
- Expected graded values
- Break-even analysis
- Risk assessment

Author: LO TCG Bot
"""
import json
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    from market.graded_prices import get_card_prices
except ImportError:
    get_card_prices = None


# =============================================================================
# GRADING COSTS (2026 prices)
# =============================================================================

GRADING_COSTS = {
    "PSA": {
        "economy": {"cost": 25, "days": 150, "name": "Economy"},
        "regular": {"cost": 50, "days": 65, "name": "Regular"},
        "express": {"cost": 100, "days": 20, "name": "Express"},
        "super_express": {"cost": 200, "days": 10, "name": "Super Express"},
        "walk_through": {"cost": 600, "days": 2, "name": "Walk-Through"},
    },
    "CGC": {
        "economy": {"cost": 20, "days": 120, "name": "Economy"},
        "standard": {"cost": 30, "days": 50, "name": "Standard"},
        "express": {"cost": 65, "days": 15, "name": "Express"},
        "walk_through": {"cost": 150, "days": 3, "name": "Walk-Through"},
    },
    "BGS": {
        "economy": {"cost": 25, "days": 100, "name": "Economy"},
        "standard": {"cost": 40, "days": 45, "name": "Standard"},
        "express": {"cost": 100, "days": 10, "name": "Express"},
        "premium": {"cost": 250, "days": 5, "name": "Premium"},
    },
}

# Shipping costs
SHIPPING_COSTS = {
    "to_grader": 15,  # Insured shipping to grading company
    "from_grader": 0,  # Usually included in grading fee
    "insurance_rate": 0.02,  # 2% of declared value
}

# Grade probability estimates based on card condition
# These are rough estimates - actual rates vary by card
GRADE_PROBABILITIES = {
    "mint": {  # Pack-fresh, perfect handling
        "PSA 10": 0.30,
        "PSA 9": 0.45,
        "PSA 8": 0.20,
        "PSA 7": 0.05,
    },
    "near_mint": {  # Light handling, minor issues
        "PSA 10": 0.10,
        "PSA 9": 0.40,
        "PSA 8": 0.35,
        "PSA 7": 0.15,
    },
    "lightly_played": {  # Some wear visible
        "PSA 10": 0.02,
        "PSA 9": 0.15,
        "PSA 8": 0.40,
        "PSA 7": 0.43,
    },
    "played": {  # Obvious wear
        "PSA 10": 0.00,
        "PSA 9": 0.05,
        "PSA 8": 0.25,
        "PSA 7": 0.70,
    },
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GradeScenario:
    """Profit/loss scenario for a specific grade."""
    grade: str
    graded_value: float
    profit: float
    roi_percent: float
    verdict: str  # "profitable", "break_even", "loss"
    emoji: str


@dataclass
class FlipAnalysis:
    """Complete flip/grade analysis for a card."""
    card_name: str
    set_name: str
    raw_price: float
    grading_company: str
    grading_tier: str
    grading_cost: float
    shipping_cost: float
    total_cost: float
    scenarios: List[GradeScenario]
    expected_value: float
    expected_profit: float
    expected_roi: float
    recommendation: str
    confidence: str
    break_even_grade: str
    best_case: GradeScenario
    worst_case: GradeScenario
    calculated_at: str
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result["scenarios"] = [asdict(s) for s in self.scenarios]
        result["best_case"] = asdict(self.best_case)
        result["worst_case"] = asdict(self.worst_case)
        return result


# =============================================================================
# CALCULATOR
# =============================================================================

class FlipCalculator:
    """
    Calculates whether grading a card is profitable.
    """
    
    def __init__(self):
        self.grading_costs = GRADING_COSTS
        self.shipping = SHIPPING_COSTS
    
    def calculate(
        self,
        card_name: str,
        set_name: str = "",
        raw_price: float = None,
        grading_company: str = "PSA",
        grading_tier: str = "economy",
        condition: str = "mint",
    ) -> FlipAnalysis:
        """
        Calculate flip profitability.
        
        Args:
            card_name: Name of the card
            set_name: Set name (helps with price accuracy)
            raw_price: Override raw price (otherwise fetched from API)
            grading_company: PSA, CGC, or BGS
            grading_tier: economy, regular, express, etc.
            condition: mint, near_mint, lightly_played, played
        
        Returns:
            FlipAnalysis with complete breakdown
        """
        # Normalize inputs
        company = grading_company.upper()
        tier = grading_tier.lower().replace(" ", "_")
        
        if company not in self.grading_costs:
            company = "PSA"
        
        if tier not in self.grading_costs[company]:
            tier = "economy"
        
        # Get grading cost
        grading_info = self.grading_costs[company][tier]
        grading_cost = grading_info["cost"]
        
        # Get card prices
        prices = self._get_prices(card_name, set_name)
        
        # Use provided raw price or fetched
        if raw_price is None:
            raw_price = prices.get("raw", {}).get("price", 0)
        
        if raw_price <= 0:
            raw_price = 10  # Default fallback
        
        # Calculate shipping (includes insurance for high-value cards)
        shipping_cost = self.shipping["to_grader"]
        if raw_price > 100:
            shipping_cost += raw_price * self.shipping["insurance_rate"]
        
        total_cost = raw_price + grading_cost + shipping_cost
        
        # Build scenarios for each grade
        scenarios = []
        graded_prices = prices.get("graded", {})
        
        grades_to_check = self._get_grades_for_company(company)
        
        for grade in grades_to_check:
            grade_data = graded_prices.get(grade, {})
            graded_value = grade_data.get("price", 0)
            
            if graded_value <= 0:
                # Estimate if no data
                graded_value = self._estimate_graded_value(raw_price, grade)
            
            profit = graded_value - total_cost
            roi = (profit / total_cost) * 100 if total_cost > 0 else 0
            
            if profit > 50:
                verdict = "profitable"
                emoji = "🚀" if roi > 100 else "✅"
            elif profit > -10:
                verdict = "break_even"
                emoji = "⚠️"
            else:
                verdict = "loss"
                emoji = "❌"
            
            scenarios.append(GradeScenario(
                grade=grade,
                graded_value=round(graded_value, 2),
                profit=round(profit, 2),
                roi_percent=round(roi, 1),
                verdict=verdict,
                emoji=emoji,
            ))
        
        # Calculate expected value based on condition probabilities
        probs = GRADE_PROBABILITIES.get(condition, GRADE_PROBABILITIES["mint"])
        expected_value = 0
        
        for scenario in scenarios:
            prob = probs.get(scenario.grade, 0)
            expected_value += scenario.graded_value * prob
        
        expected_profit = expected_value - total_cost
        expected_roi = (expected_profit / total_cost) * 100 if total_cost > 0 else 0
        
        # Find best and worst cases
        best_case = max(scenarios, key=lambda s: s.profit)
        worst_case = min(scenarios, key=lambda s: s.profit)
        
        # Find break-even grade
        break_even_grade = "None"
        for scenario in scenarios:
            if scenario.profit >= 0:
                break_even_grade = scenario.grade
                break
        
        # Generate recommendation
        recommendation, confidence = self._generate_recommendation(
            expected_profit, expected_roi, scenarios, condition
        )
        
        return FlipAnalysis(
            card_name=card_name,
            set_name=set_name,
            raw_price=round(raw_price, 2),
            grading_company=company,
            grading_tier=grading_info["name"],
            grading_cost=grading_cost,
            shipping_cost=round(shipping_cost, 2),
            total_cost=round(total_cost, 2),
            scenarios=scenarios,
            expected_value=round(expected_value, 2),
            expected_profit=round(expected_profit, 2),
            expected_roi=round(expected_roi, 1),
            recommendation=recommendation,
            confidence=confidence,
            break_even_grade=break_even_grade,
            best_case=best_case,
            worst_case=worst_case,
            calculated_at=datetime.now().isoformat(),
        )
    
    def _get_prices(self, card_name: str, set_name: str) -> Dict:
        """Get card prices from the graded_prices module."""
        if get_card_prices:
            try:
                return get_card_prices(card_name, set_name, include_ebay=False)
            except:
                pass
        
        # Fallback demo prices
        return {
            "raw": {"price": 50, "low": 40, "high": 60},
            "graded": {
                "PSA 10": {"price": 250},
                "PSA 9": {"price": 100},
                "PSA 8": {"price": 70},
                "PSA 7": {"price": 55},
                "CGC 10": {"price": 200},
                "CGC 9.5": {"price": 120},
                "CGC 9": {"price": 80},
                "BGS 10": {"price": 400},
                "BGS 9.5": {"price": 150},
                "BGS 9": {"price": 85},
            }
        }
    
    def _get_grades_for_company(self, company: str) -> List[str]:
        """Get relevant grades for a grading company."""
        if company == "PSA":
            return ["PSA 10", "PSA 9", "PSA 8", "PSA 7"]
        elif company == "CGC":
            return ["CGC 10", "CGC 9.5", "CGC 9"]
        elif company == "BGS":
            return ["BGS 10", "BGS 9.5", "BGS 9"]
        return ["PSA 10", "PSA 9", "PSA 8"]
    
    def _estimate_graded_value(self, raw_price: float, grade: str) -> float:
        """Estimate graded value if no data available."""
        multipliers = {
            "PSA 10": 5.0, "PSA 9": 2.0, "PSA 8": 1.4, "PSA 7": 1.1,
            "CGC 10": 4.0, "CGC 9.5": 2.5, "CGC 9": 1.7,
            "BGS 10": 8.0, "BGS 9.5": 3.5, "BGS 9": 1.6,
        }
        return raw_price * multipliers.get(grade, 1.5)
    
    def _generate_recommendation(
        self, expected_profit: float, expected_roi: float,
        scenarios: List[GradeScenario], condition: str
    ) -> tuple:
        """Generate recommendation and confidence level."""
        
        profitable_scenarios = len([s for s in scenarios if s.profit > 0])
        total_scenarios = len(scenarios)
        
        # High confidence recommendations
        if expected_roi > 100 and profitable_scenarios >= 3:
            return "🚀 STRONG BUY - Grade this card!", "HIGH"
        
        if expected_roi > 50 and profitable_scenarios >= 2:
            return "✅ RECOMMENDED - Good grading candidate", "MEDIUM-HIGH"
        
        if expected_roi > 20 and condition in ["mint", "near_mint"]:
            return "📈 WORTH CONSIDERING - If confident in condition", "MEDIUM"
        
        if expected_roi > 0:
            return "⚠️ MARGINAL - Only if high confidence in PSA 10", "LOW"
        
        if expected_roi > -20:
            return "❌ NOT RECOMMENDED - Keep raw unless PSA 10 certain", "LOW"
        
        return "🚫 AVOID - Grading would lose money", "HIGH"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_flip(
    card_name: str,
    set_name: str = "",
    raw_price: float = None,
    company: str = "PSA",
    tier: str = "economy",
    condition: str = "mint",
) -> Dict:
    """
    Quick function to calculate flip profitability.
    
    Returns dict with all analysis data.
    """
    calc = FlipCalculator()
    result = calc.calculate(
        card_name=card_name,
        set_name=set_name,
        raw_price=raw_price,
        grading_company=company,
        grading_tier=tier,
        condition=condition,
    )
    return result.to_dict()


def get_grading_costs() -> Dict:
    """Get all grading company costs."""
    return GRADING_COSTS


def format_flip_discord(analysis: Dict) -> str:
    """Format flip analysis for Discord message."""
    msg = f"📊 **FLIP CALCULATOR** - {analysis['card_name']}\n\n"
    
    msg += f"💵 **Raw Price:** ${analysis['raw_price']}\n"
    msg += f"🏢 **Grading:** {analysis['grading_company']} {analysis['grading_tier']}\n"
    msg += f"💰 **Total Cost:** ${analysis['total_cost']} "
    msg += f"(Grade: ${analysis['grading_cost']} + Ship: ${analysis['shipping_cost']})\n\n"
    
    msg += "📈 **GRADE SCENARIOS:**\n"
    for s in analysis['scenarios']:
        profit_str = f"+${s['profit']}" if s['profit'] >= 0 else f"-${abs(s['profit'])}"
        msg += f"{s['emoji']} **{s['grade']}:** ${s['graded_value']} → {profit_str} ({s['roi_percent']}% ROI)\n"
    
    msg += f"\n📊 **Expected Value:** ${analysis['expected_value']}\n"
    msg += f"💰 **Expected Profit:** ${analysis['expected_profit']} ({analysis['expected_roi']}% ROI)\n"
    msg += f"⚖️ **Break-Even:** {analysis['break_even_grade']}\n\n"
    
    msg += f"💡 **{analysis['recommendation']}**\n"
    msg += f"📊 Confidence: {analysis['confidence']}"
    
    return msg


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    card = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Charizard VMAX"
    
    print(f"Calculating flip for: {card}")
    print("-" * 50)
    
    result = calculate_flip(card)
    
    print(format_flip_discord(result))
