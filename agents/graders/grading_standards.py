#!/usr/bin/env python3
"""
Official Grading Standards Reference

This module contains the official grading criteria for:
- PSA (Professional Sports Authenticator)
- CGC (Certified Guaranty Company)
- BGS/Beckett (Beckett Grading Services)

Used by the AI grading agent to evaluate card condition.
"""

# =============================================================================
# PSA GRADING SCALE (1-10)
# =============================================================================

PSA_GRADES = {
    10: {
        "name": "Gem Mint",
        "description": "A virtually perfect card. Four perfectly sharp corners, sharp focus, full original gloss, free of any staining. Centering must be 55/45 or better on front and 75/25 or better on back.",
        "criteria": {
            "centering_front": {"min": 55, "max": 45},  # 55/45 or better
            "centering_back": {"min": 75, "max": 25},   # 75/25 or better
            "corners": "All four corners must be perfectly sharp",
            "edges": "No chips, no whitening, perfectly clean",
            "surface": "No scratches, no print defects, full original gloss",
            "focus": "Sharp, clear printing throughout",
        },
        "value_multiplier": 10.0,
    },
    9: {
        "name": "Mint",
        "description": "A superb condition card with only one minor flaw. Centering must be 60/40 or better on front and 90/10 or better on back.",
        "criteria": {
            "centering_front": {"min": 60, "max": 40},
            "centering_back": {"min": 90, "max": 10},
            "corners": "Sharp corners with one minor imperfection allowed",
            "edges": "Virtually perfect edges, tiny flaw allowed",
            "surface": "Excellent gloss, one minor print spot allowed",
            "focus": "Clear, sharp image",
        },
        "value_multiplier": 4.0,
    },
    8: {
        "name": "Near Mint-Mint",
        "description": "A super high-end card with only minor wear. Centering must be 65/35 or better on front and 90/10 or better on back.",
        "criteria": {
            "centering_front": {"min": 65, "max": 35},
            "centering_back": {"min": 90, "max": 10},
            "corners": "Corners show minor wear",
            "edges": "Minor edge wear, slight whitening allowed",
            "surface": "Good gloss, minor print spots allowed",
            "focus": "Clear image with minor imperfections",
        },
        "value_multiplier": 2.5,
    },
    7: {
        "name": "Near Mint",
        "description": "A card with slight surface wear, minor corner wear, and centering of 70/30 or better on front.",
        "criteria": {
            "centering_front": {"min": 70, "max": 30},
            "centering_back": {"min": 90, "max": 10},
            "corners": "Slight corner wear visible",
            "edges": "Light edge wear, whitening visible",
            "surface": "Minor surface wear, slight loss of gloss",
            "focus": "Clear but may show minor issues",
        },
        "value_multiplier": 1.8,
    },
    6: {
        "name": "Excellent-Mint",
        "description": "Card shows visible wear. Corners may show moderate wear, edges have chipping.",
        "criteria": {
            "centering_front": {"min": 75, "max": 25},
            "centering_back": {"min": 90, "max": 10},
            "corners": "Moderate corner wear",
            "edges": "Moderate edge wear and chipping",
            "surface": "Some surface wear, reduced gloss",
            "focus": "May show some focus issues",
        },
        "value_multiplier": 1.4,
    },
    5: {
        "name": "Excellent",
        "description": "Card with obvious wear but still retains appeal. Corners are rounded.",
        "criteria": {
            "centering_front": {"min": 80, "max": 20},
            "centering_back": {"min": 90, "max": 10},
            "corners": "Rounded corners",
            "edges": "Significant edge wear",
            "surface": "Noticeable wear, scratching possible",
            "focus": "May be slightly out of focus",
        },
        "value_multiplier": 1.2,
    },
    4: {
        "name": "Very Good-Excellent",
        "description": "Significant wear. May have light creases or staining.",
        "criteria": {
            "corners": "Heavy corner wear",
            "edges": "Heavy edge wear",
            "surface": "Light creases, staining possible",
            "focus": "Focus issues acceptable",
        },
        "value_multiplier": 1.1,
    },
    3: {
        "name": "Very Good",
        "description": "Well-worn card with creases and staining visible.",
        "criteria": {
            "corners": "Very rounded corners",
            "edges": "Significant edge damage",
            "surface": "Creases, staining, scuffing",
            "focus": "Blurry or miscut acceptable",
        },
        "value_multiplier": 1.0,
    },
    2: {
        "name": "Good",
        "description": "Significant damage. Heavy creases, writing, or tears.",
        "criteria": {
            "overall": "Heavy wear, possible writing, small tears",
        },
        "value_multiplier": 0.8,
    },
    1: {
        "name": "Poor",
        "description": "Card may be missing pieces, have holes, or be heavily damaged.",
        "criteria": {
            "overall": "Severe damage, missing pieces possible",
        },
        "value_multiplier": 0.5,
    },
}

# =============================================================================
# CGC GRADING SCALE (1-10)
# =============================================================================

CGC_GRADES = {
    10: {
        "name": "Pristine",
        "description": "Perfect card in every way. Flawless corners, edges, surface, and centering.",
        "subgrades": {
            "centering": 10,
            "corners": 10,
            "edges": 10,
            "surface": 10,
        },
        "criteria": {
            "centering": "60/40 or better front and back",
            "corners": "Perfectly sharp, no wear",
            "edges": "Flawless, no chips or whitening",
            "surface": "No scratches, perfect gloss, no print defects",
        },
        "value_multiplier": 12.0,
    },
    9.5: {
        "name": "Gem Mint",
        "description": "Virtually perfect with one very minor flaw.",
        "subgrades": {
            "centering": 9.5,
            "corners": 9.5,
            "edges": 9.5,
            "surface": 9.5,
        },
        "value_multiplier": 8.0,
    },
    9: {
        "name": "Mint",
        "description": "Superb condition with minor imperfections.",
        "subgrades": {
            "centering": 9,
            "corners": 9,
            "edges": 9,
            "surface": 9,
        },
        "value_multiplier": 4.0,
    },
    8.5: {
        "name": "Near Mint/Mint+",
        "description": "Outstanding condition with slight wear.",
        "value_multiplier": 3.0,
    },
    8: {
        "name": "Near Mint/Mint",
        "description": "Excellent condition with minor wear visible.",
        "value_multiplier": 2.5,
    },
    7.5: {
        "name": "Near Mint+",
        "description": "Near Mint with slight additional wear.",
        "value_multiplier": 2.0,
    },
    7: {
        "name": "Near Mint",
        "description": "Light wear on corners and edges.",
        "value_multiplier": 1.8,
    },
}

# =============================================================================
# BGS/BECKETT GRADING SCALE (1-10 with subgrades)
# =============================================================================

BGS_GRADES = {
    10: {
        "name": "Pristine",
        "label": "Black Label",
        "description": "Flawless card. All four subgrades must be 10. Extremely rare.",
        "subgrades_required": {
            "centering": 10,
            "corners": 10,
            "edges": 10,
            "surface": 10,
        },
        "centering_requirement": "50/50 front and back",
        "value_multiplier": 15.0,
    },
    9.5: {
        "name": "Gem Mint",
        "label": "Gold Label",
        "description": "Virtually perfect. No subgrade below 9.",
        "subgrades_required": {
            "min_subgrade": 9,
            "average": 9.5,
        },
        "centering_requirement": "55/45 or better",
        "value_multiplier": 6.0,
    },
    9: {
        "name": "Mint",
        "label": "Silver Label",
        "description": "Outstanding condition. No subgrade below 8.5.",
        "subgrades_required": {
            "min_subgrade": 8.5,
        },
        "value_multiplier": 3.5,
    },
    8.5: {
        "name": "Near Mint-Mint+",
        "description": "Excellent card with minor flaws.",
        "value_multiplier": 2.5,
    },
    8: {
        "name": "Near Mint-Mint",
        "description": "Very good condition with slight wear.",
        "value_multiplier": 2.0,
    },
}

# =============================================================================
# GRADING CRITERIA DEFINITIONS
# =============================================================================

GRADING_CRITERIA = {
    "centering": {
        "description": "How well centered the image is within the card borders",
        "measurement": "Left-Right / Top-Bottom percentage",
        "perfect": "50/50",
        "psa10_threshold": "55/45 or better",
        "evaluation_points": [
            "Measure border width on all sides",
            "Compare left vs right border",
            "Compare top vs bottom border",
            "Calculate percentage ratio",
        ],
    },
    "corners": {
        "description": "Sharpness and condition of all four corners",
        "evaluation_points": [
            "Check for whitening (exposed cardboard)",
            "Look for rounding or softness",
            "Inspect for dings or dents",
            "Examine for peeling or fraying",
            "All four corners must be evaluated",
        ],
        "defects": [
            "Corner whitening",
            "Soft/rounded corners",
            "Corner dings",
            "Corner peeling",
            "Bent corners",
        ],
    },
    "edges": {
        "description": "Condition of the card edges between corners",
        "evaluation_points": [
            "Check for edge whitening (chipping)",
            "Look for nicks or cuts",
            "Inspect for rough cutting",
            "Examine for peeling layers",
        ],
        "defects": [
            "Edge whitening/chipping",
            "Rough/jagged edges",
            "Edge peeling",
            "Edge nicks",
        ],
    },
    "surface": {
        "description": "Condition of the card's front and back surfaces",
        "evaluation_points": [
            "Check for scratches",
            "Look for print defects (dots, lines, missing ink)",
            "Inspect for staining",
            "Examine gloss quality",
            "Check for indentations",
            "Look for roller lines (factory defect)",
        ],
        "defects": [
            "Surface scratches",
            "Print dots/spots",
            "Print lines",
            "Staining",
            "Loss of gloss",
            "Indentations",
            "Roller lines",
            "Silvering (holofoil)",
        ],
    },
}

# =============================================================================
# POKEMON-SPECIFIC GRADING NOTES
# =============================================================================

POKEMON_SPECIFIC = {
    "holofoil_cards": {
        "note": "Holofoil cards are more prone to surface scratches and silvering",
        "common_issues": [
            "Holo scratches (visible under light)",
            "Silvering (silver spots on holo pattern)",
            "Holo bleed (holo pattern bleeding into border)",
        ],
    },
    "reverse_holo": {
        "note": "Reverse holo cards often have surface issues from the holo pattern",
        "common_issues": [
            "Pattern scratches",
            "Uneven holo application",
        ],
    },
    "full_art": {
        "note": "Full art cards show wear more easily due to texture",
        "common_issues": [
            "Texture wear",
            "Edge silvering",
            "Print lines more visible",
        ],
    },
    "vintage_cards": {
        "note": "Vintage cards (WOTC era) have different quality standards",
        "common_issues": [
            "More centering issues from era",
            "Different cardstock shows wear differently",
            "Yellowing from age",
        ],
    },
}


def get_grade_info(grade: float, company: str = "PSA") -> dict:
    """Get grade information for a specific company and grade."""
    if company.upper() == "PSA":
        return PSA_GRADES.get(int(grade), {})
    elif company.upper() == "CGC":
        return CGC_GRADES.get(grade, {})
    elif company.upper() in ["BGS", "BECKETT"]:
        return BGS_GRADES.get(grade, {})
    return {}


def get_value_multiplier(grade: float, company: str = "PSA") -> float:
    """Get the value multiplier for a graded card."""
    info = get_grade_info(grade, company)
    return info.get("value_multiplier", 1.0)
