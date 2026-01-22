#!/usr/bin/env python3
"""
Visual Card Grading Agent

AI-powered Pokemon card grading that analyzes images and predicts
PSA, CGC, and Beckett grades based on official grading criteria.

This agent evaluates:
- Centering (border measurements)
- Corners (sharpness, whitening)
- Edges (chipping, whitening)
- Surface (scratches, print defects, gloss)

Accepts base64-encoded images or image URLs.
"""
import base64
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

# Import grading standards
sys.path.insert(0, str(Path(__file__).parent))
from grading_standards import (
    PSA_GRADES,
    CGC_GRADES,
    BGS_GRADES,
    GRADING_CRITERIA,
    POKEMON_SPECIFIC,
    get_value_multiplier,
)

# OpenAI API for vision analysis (optional - falls back to rule-based if not set)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def analyze_image_with_ai(image_data: str, is_url: bool = False) -> Dict[str, Any]:
    """
    Use AI vision model to analyze card image.
    Supports OpenAI GPT-4 Vision or Anthropic Claude Vision.
    
    Falls back to simulated analysis if no API key is set.
    """
    
    # Build the grading prompt
    grading_prompt = """You are an expert Pokemon card grader with extensive experience at PSA, CGC, and Beckett.

Analyze this Pokemon card image and provide a detailed grading assessment.

Evaluate these criteria on a scale of 1-10:

1. CENTERING (measure the borders):
   - Compare left vs right border width
   - Compare top vs bottom border width
   - Calculate approximate percentage (e.g., 55/45)
   - PSA 10 requires 55/45 or better on front

2. CORNERS (examine all four corners):
   - Look for whitening (exposed cardboard)
   - Check for softness/rounding
   - Note any dings or damage
   - All corners must be sharp for PSA 10

3. EDGES (check all four edges):
   - Look for chipping or whitening
   - Check for rough cutting
   - Note any nicks or damage

4. SURFACE (front and back):
   - Check for scratches (especially on holofoil)
   - Look for print defects (dots, lines)
   - Assess gloss quality
   - Note any staining or indentations
   - Check for silvering on holo cards

Provide your response in this exact JSON format:
{
    "card_identified": "Card name if visible",
    "card_type": "holofoil/reverse_holo/full_art/regular",
    "subgrades": {
        "centering": 8.5,
        "corners": 9.0,
        "edges": 8.5,
        "surface": 9.0
    },
    "centering_estimate": "55/45",
    "defects_found": [
        {"type": "corner_whitening", "severity": "minor", "location": "bottom-left"},
        {"type": "surface_scratch", "severity": "light", "location": "holo area"}
    ],
    "predicted_grades": {
        "PSA": 8,
        "CGC": 8.5,
        "BGS": 8.5
    },
    "grade_confidence": 0.85,
    "notes": "Brief notes about the card condition",
    "recommendations": "Suggestions for which company to grade with"
}"""

    # Try OpenAI Vision
    if OPENAI_API_KEY:
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            
            if is_url:
                image_content = {"type": "image_url", "image_url": {"url": image_data}}
            else:
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": grading_prompt},
                            image_content,
                        ],
                    }
                ],
                "max_tokens": 1500,
            }
            
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            
            if resp.status_code == 200:
                result = resp.json()
                content = result["choices"][0]["message"]["content"]
                # Extract JSON from response
                try:
                    # Find JSON in response
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"OpenAI Vision error: {e}", file=sys.stderr)
    
    # Try Anthropic Claude Vision
    if ANTHROPIC_API_KEY:
        try:
            import requests
            
            headers = {
                "x-api-key": ANTHROPIC_API_KEY,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }
            
            if is_url:
                # Claude needs base64, would need to fetch URL first
                image_source = {"type": "url", "url": image_data}
            else:
                image_source = {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data,
                }
            
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": image_source},
                            {"type": "text", "text": grading_prompt},
                        ],
                    }
                ],
            }
            
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60,
            )
            
            if resp.status_code == 200:
                result = resp.json()
                content = result["content"][0]["text"]
                try:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"Anthropic Vision error: {e}", file=sys.stderr)
    
    # Fallback: Return simulated analysis (demo mode)
    return get_demo_analysis()


def get_demo_analysis() -> Dict[str, Any]:
    """Return a demo analysis when no AI API is available."""
    return {
        "card_identified": "Pokemon Card (AI analysis requires API key)",
        "card_type": "holofoil",
        "subgrades": {
            "centering": 9.0,
            "corners": 8.5,
            "edges": 9.0,
            "surface": 8.5,
        },
        "centering_estimate": "55/45",
        "defects_found": [
            {"type": "minor_corner_wear", "severity": "light", "location": "bottom-right corner"},
            {"type": "light_surface_scratch", "severity": "very_light", "location": "holo area"},
        ],
        "predicted_grades": {
            "PSA": 8,
            "CGC": 8.5,
            "BGS": 8.5,
        },
        "grade_confidence": 0.75,
        "notes": "Demo analysis - provide OPENAI_API_KEY or ANTHROPIC_API_KEY for real AI grading",
        "recommendations": "Consider PSA for Pokemon cards, CGC for modern sets with good centering",
        "demo_mode": True,
    }


def calculate_estimated_value(
    raw_value: float,
    predicted_grades: Dict[str, float],
) -> Dict[str, Any]:
    """Calculate estimated graded values based on predicted grades."""
    values = {}
    
    for company, grade in predicted_grades.items():
        multiplier = get_value_multiplier(grade, company)
        graded_value = raw_value * multiplier
        
        # Subtract grading cost estimate
        grading_costs = {
            "PSA": 25 if grade < 10 else 150,  # PSA 10 special tier
            "CGC": 20,
            "BGS": 30,
        }
        cost = grading_costs.get(company, 25)
        net_value = graded_value - cost
        
        values[company] = {
            "predicted_grade": grade,
            "raw_value": raw_value,
            "multiplier": multiplier,
            "graded_value": round(graded_value, 2),
            "grading_cost": cost,
            "net_value": round(net_value, 2),
            "worth_grading": net_value > raw_value,
        }
    
    # Find best option
    best_company = max(values.keys(), key=lambda k: values[k]["net_value"])
    values["recommendation"] = {
        "best_company": best_company,
        "expected_net_value": values[best_company]["net_value"],
        "roi_percent": round(
            ((values[best_company]["net_value"] - raw_value) / raw_value) * 100, 1
        ) if raw_value > 0 else 0,
    }
    
    return values


def grade_card(
    image_data: Optional[str] = None,
    image_url: Optional[str] = None,
    raw_value: float = 10.0,
    card_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main grading function.
    
    Args:
        image_data: Base64-encoded image data
        image_url: URL to card image
        raw_value: Estimated raw (ungraded) card value
        card_name: Optional card name for reference
    
    Returns:
        Complete grading analysis with predicted grades and values
    """
    
    # Analyze image
    if image_url:
        analysis = analyze_image_with_ai(image_url, is_url=True)
    elif image_data:
        analysis = analyze_image_with_ai(image_data, is_url=False)
    else:
        # No image provided - return standards info only
        return {
            "success": True,
            "mode": "info_only",
            "message": "No image provided. Returning grading standards info.",
            "grading_standards": {
                "PSA": {k: {"name": v["name"], "description": v["description"]} 
                       for k, v in PSA_GRADES.items()},
                "criteria": GRADING_CRITERIA,
                "pokemon_specific": POKEMON_SPECIFIC,
            },
        }
    
    # Calculate values
    predicted_grades = analysis.get("predicted_grades", {"PSA": 7, "CGC": 7, "BGS": 7})
    value_analysis = calculate_estimated_value(raw_value, predicted_grades)
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "card_name": card_name or analysis.get("card_identified", "Unknown"),
        "card_type": analysis.get("card_type", "unknown"),
        
        # Subgrades
        "subgrades": analysis.get("subgrades", {}),
        "centering_estimate": analysis.get("centering_estimate", "unknown"),
        
        # Defects
        "defects_found": analysis.get("defects_found", []),
        "defect_count": len(analysis.get("defects_found", [])),
        
        # Predicted grades
        "predicted_grades": predicted_grades,
        "grade_confidence": analysis.get("grade_confidence", 0.5),
        
        # Value analysis
        "value_analysis": value_analysis,
        "worth_grading": value_analysis.get("recommendation", {}).get("roi_percent", 0) > 20,
        
        # Notes
        "notes": analysis.get("notes", ""),
        "recommendations": analysis.get("recommendations", ""),
        
        # Grading criteria reference
        "grading_criteria_used": list(GRADING_CRITERIA.keys()),
        
        # Demo mode flag
        "demo_mode": analysis.get("demo_mode", False),
    }


# =============================================================================
# MAIN - Handle stdin JSON or command line
# =============================================================================

if __name__ == "__main__":
    # Read from stdin if available
    input_data = sys.stdin.read() if not sys.stdin.isatty() else "{}"
    
    try:
        data = json.loads(input_data) if input_data.strip() else {}
    except json.JSONDecodeError:
        data = {}
    
    # Extract parameters
    image_data = data.get("image_data") or data.get("image_base64")
    image_url = data.get("image_url")
    raw_value = float(data.get("raw_value", 10.0))
    card_name = data.get("card_name")
    
    # Run grading
    result = grade_card(
        image_data=image_data,
        image_url=image_url,
        raw_value=raw_value,
        card_name=card_name,
    )
    
    print(json.dumps(result))
