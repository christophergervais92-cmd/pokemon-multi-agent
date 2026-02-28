"""
Improved grading estimator based on condition keywords and industry standards.
"""
from __future__ import annotations

import re
from typing import Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class Grade(Enum):
    GEM_MINT_10 = (10, "Gem Mint")
    MINT_9 = (9, "Mint")
    NM_MT_8 = (8, "NM-MT")
    NM_7 = (7, "Near Mint")
    EX_MT_6 = (6, "EX-MT")
    EX_5 = (5, "Excellent")
    VG_EX_4 = (4, "VG-EX")
    VG_3 = (3, "Very Good")
    GOOD_2 = (2, "Good")
    FAIR_1_5 = (1.5, "Fair")
    POOR_1 = (1, "Poor")
    
    def __init__(self, numeric: float, label: str):
        self.numeric = numeric
        self.label = label


# Condition keywords and their impact on grade
CONDITION_KEYWORDS = {
    # Negative indicators (reduce grade)
    "scratch": -2,
    "scratched": -2,
    "indent": -2,
    "indented": -2,
    "crease": -4,
    "creased": -4,
    "tear": -5,
    "torn": -5,
    "bend": -3,
    "bent": -3,
    "warp": -3,
    "warped": -3,
    "water": -4,
    "water damage": -5,
    "stain": -3,
    "stained": -3,
    "discolor": -2,
    "discolored": -2,
    "yellow": -2,
    "yellowing": -2,
    "faded": -2,
    "fade": -2,
    "chipped": -3,
    "chip": -3,
    "peeling": -3,
    "peel": -3,
    "heavy": -3,
    "major": -3,
    "significant": -3,
    "serious": -4,
    "severe": -5,
    "extensive": -4,
    "edge wear": -2,
    "corner wear": -2,
    "surface wear": -2,
    "whitening": -1,
    "foxing": -2,
    "mold": -5,
    "mildew": -4,
    "hole": -5,
    "punched": -4,
    "written": -2,
    "writing": -2,
    "mark": -2,
    "marked": -2,
    "ink": -2,
    "pen": -2,
    "pencil": -1,
    
    # Positive indicators (confirm grade)
    "gem": 2,
    "gem mint": 3,
    "pristine": 2,
    "perfect": 2,
    "flawless": 2,
    "pack fresh": 1,
    "packfresh": 1,
    "mint": 1,
    "near mint": 0,
    "nm": 0,
    "excellent": -1,
    "ex": -1,
    "very good": -2,
    "vg": -2,
    "good": -3,
    "played": -4,
    "heavily played": -5,
    "hp": -4,
    "poor": -5,
    "damaged": -5,
}


def _analyze_condition_notes(notes: str) -> Tuple[float, Dict[str, any]]:
    """
    Analyze condition notes and return estimated grade and analysis.
    
    Returns:
        Tuple of (grade_score, analysis_dict)
    """
    notes_lower = notes.lower()
    score_adjustment = 0
    factors_found = []
    
    # Check for explicit grade mentions
    explicit_grade = None
    grade_patterns = [
        (r'\bpsa\s*(10|9|8|7|6|5|4|3|2|1)\b', lambda m: float(m.group(1))),
        (r'\bcgc\s*(10|9|8|7|6|5|4|3|2|1)\b', lambda m: float(m.group(1))),
        (r'\bbgs?\s*(10|9\.5|9|8\.5|8|7\.5|7|6|5|4|3|2|1)\b', lambda m: float(m.group(1))),
        (r'\bgrade\s*:?\s*(10|9|8|7|6|5|4|3|2|1)\b', lambda m: float(m.group(1))),
    ]
    
    for pattern, extractor in grade_patterns:
        match = re.search(pattern, notes_lower)
        if match:
            explicit_grade = extractor(match)
            factors_found.append(f"Explicit grade mention: {explicit_grade}")
            break
    
    # Analyze keywords
    for keyword, impact in CONDITION_KEYWORDS.items():
        if keyword in notes_lower:
            score_adjustment += impact
            if impact < -2:
                severity = "major"
            elif impact < 0:
                severity = "minor"
            else:
                severity = "positive"
            factors_found.append(f"{severity}: '{keyword}' ({impact:+d})")
    
    # Base grade starts at 10
    base_grade = 10.0
    
    # If explicit grade mentioned, use that as base
    if explicit_grade:
        base_grade = explicit_grade
    
    final_score = max(1.0, min(10.0, base_grade + score_adjustment))
    
    return final_score, {
        "factors": factors_found,
        "score_adjustment": score_adjustment,
        "base_grade": base_grade,
        "explicit_grade": explicit_grade
    }


def _score_to_grade(score: float) -> Grade:
    """Convert numeric score to Grade enum."""
    if score >= 9.5:
        return Grade.GEM_MINT_10
    elif score >= 8.5:
        return Grade.MINT_9
    elif score >= 7.5:
        return Grade.NM_MT_8
    elif score >= 6.5:
        return Grade.NM_7
    elif score >= 5.5:
        return Grade.EX_MT_6
    elif score >= 4.5:
        return Grade.EX_5
    elif score >= 3.5:
        return Grade.VG_EX_4
    elif score >= 2.5:
        return Grade.VG_3
    elif score >= 1.75:
        return Grade.GOOD_2
    elif score >= 1.25:
        return Grade.FAIR_1_5
    else:
        return Grade.POOR_1


def estimate_grade(condition_notes: str) -> str:
    """
    Estimate card grade from condition notes.
    
    Args:
        condition_notes: Text description of card condition
        
    Returns:
        Estimated grade string (e.g., "PSA 9 (Mint)")
    """
    if not condition_notes or not condition_notes.strip():
        return "Unable to estimate - no condition notes provided"
    
    score, analysis = _analyze_condition_notes(condition_notes)
    grade = _score_to_grade(score)
    
    # Format response
    result = f"PSA {grade.numeric} ({grade.label})"
    
    # Add confidence indicator
    if len(analysis["factors"]) == 0:
        result += " - Low confidence: no condition indicators found"
    elif analysis["explicit_grade"]:
        result += " - High confidence: explicit grade mentioned"
    elif len([f for f in analysis["factors"] if "major" in f]) > 0:
        result += " - Moderate confidence: major defects noted"
    else:
        result += " - Moderate confidence: based on condition keywords"
    
    return result


def assess_condition(notes: str) -> dict:
    """
    Return detailed condition assessment.
    
    Returns:
        Dict with grade, confidence, factors, and recommendations
    """
    if not notes or not notes.strip():
        return {
            "grade": None,
            "label": "Unknown",
            "confidence": "none",
            "factors": [],
            "recommendation": "Provide condition notes for assessment"
        }
    
    score, analysis = _analyze_condition_notes(notes)
    grade = _score_to_grade(score)
    
    # Determine confidence
    if analysis["explicit_grade"]:
        confidence = "high"
    elif len(analysis["factors"]) >= 3:
        confidence = "high"
    elif len(analysis["factors"]) >= 1:
        confidence = "moderate"
    else:
        confidence = "low"
    
    # Generate recommendation
    major_defects = [f for f in analysis["factors"] if "major" in f]
    if major_defects:
        # Rough heuristic: each major defect tends to reduce value materially.
        impact_low = 20 * len(major_defects)
        impact_high = 40 * len(major_defects)
        recommendation = (
            "Card has major defects. Professional grading may not be worthwhile. "
            f"Estimated value impact: -{impact_low}% to -{impact_high}%"
        )
    elif score >= 9:
        recommendation = "Excellent condition! Consider professional grading for valuable cards."
    elif score >= 7:
        recommendation = "Good condition. Grade-worthy if card value > $50."
    elif score >= 5:
        recommendation = "Moderate wear. Only grade if card is rare/valuable."
    else:
        recommendation = "Significant wear. Grading likely not recommended unless very rare."
    
    return {
        "grade": grade.numeric,
        "label": grade.label,
        "confidence": confidence,
        "factors": analysis["factors"],
        "score_breakdown": {
            "base": analysis["base_grade"],
            "adjustment": analysis["score_adjustment"],
            "final": round(score, 1)
        },
        "recommendation": recommendation
    }


def get_grading_cost_estimate(card_value: float, estimated_grade: float) -> dict:
    """
    Estimate grading costs vs potential value increase.
    
    Args:
        card_value: Raw card value
        estimated_grade: Expected PSA grade (1-10)
        
    Returns:
        Dict with cost breakdown and recommendation
    """
    # Typical grading costs
    psa_cost = 25  # PSA standard
    cgc_cost = 20  # CGC standard
    bgs_cost = 30  # BGS standard
    shipping_insurance = 15
    
    # Value multiplier by grade (rough estimates)
    multipliers = {
        10: 5.0,
        9: 2.5,
        8: 1.5,
        7: 1.2,
        6: 1.0,
        5: 0.9,
        4: 0.8,
        3: 0.7,
        2: 0.6,
        1: 0.5
    }
    
    grade_int = int(estimated_grade)
    multiplier = multipliers.get(grade_int, 0.5)
    graded_value = card_value * multiplier
    
    total_cost_psa = psa_cost + shipping_insurance
    total_cost_cgc = cgc_cost + shipping_insurance
    total_cost_bgs = bgs_cost + shipping_insurance
    
    net_gain_psa = graded_value - card_value - total_cost_psa
    net_gain_cgc = graded_value - card_value - total_cost_cgc
    net_gain_bgs = graded_value - card_value - total_cost_bgs
    
    return {
        "current_value": card_value,
        "estimated_graded_value": round(graded_value, 2),
        "grading_costs": {
            "psa": total_cost_psa,
            "cgc": total_cost_cgc,
            "bgs": total_cost_bgs
        },
        "potential_net_gain": {
            "psa": round(net_gain_psa, 2),
            "cgc": round(net_gain_cgc, 2),
            "bgs": round(net_gain_bgs, 2)
        },
        "recommendation": "Grade" if net_gain_psa > 20 else "Consider" if net_gain_psa > 0 else "Don't grade"
    }
