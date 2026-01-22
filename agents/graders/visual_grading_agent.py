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

Features:
- Auto-detect image quality (blur, resolution, lighting)
- Photo template guidance for perfect card photos
- Front and back photo support
- Image preprocessing and validation

Accepts base64-encoded images or image URLs.
"""
import base64
import hashlib
import json
import os
import sys
import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
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

# Try to import image processing libraries
try:
    from PIL import Image, ImageFilter, ImageStat
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# OpenAI API for vision analysis (optional - falls back to rule-based if not set)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# =============================================================================
# IMAGE QUALITY DETECTION
# =============================================================================

# Ideal image specifications for card grading
IDEAL_SPECS = {
    "min_width": 800,           # Minimum width in pixels
    "min_height": 1100,         # Minimum height in pixels
    "ideal_width": 1500,        # Ideal width for best results
    "ideal_height": 2100,       # Ideal height for best results
    "max_file_size_mb": 10,     # Maximum file size
    "min_brightness": 80,       # Minimum average brightness (0-255)
    "max_brightness": 220,      # Maximum average brightness (0-255)
    "min_contrast": 40,         # Minimum contrast
    "blur_threshold": 100,      # Laplacian variance threshold (lower = more blur)
    "card_aspect_ratio": 0.714, # Standard Pokemon card ratio (2.5" x 3.5")
    "aspect_tolerance": 0.1,    # Tolerance for aspect ratio
}

# Photo template guidance
PHOTO_TEMPLATE = {
    "front": {
        "instructions": [
            "Place card on a dark, non-reflective surface",
            "Ensure even lighting from above (no harsh shadows)",
            "Position card straight and centered in frame",
            "Fill 70-80% of the frame with the card",
            "Keep camera parallel to card (no angle)",
            "Use macro mode if available for sharpness",
            "Avoid glare on holofoil areas",
        ],
        "checklist": [
            "All four corners visible",
            "All four edges clearly visible",
            "Card name/text readable",
            "Holofoil pattern visible (if applicable)",
            "No reflections or glare",
            "Card is in focus throughout",
        ],
    },
    "back": {
        "instructions": [
            "Same lighting setup as front",
            "Card should be in same position/orientation",
            "Ensure Pokemon ball pattern is clearly visible",
            "Check that all edges and corners are visible",
        ],
        "checklist": [
            "All four corners visible",
            "All four edges clearly visible",
            "Pokemon ball pattern clear",
            "No reflections or shadows",
            "Card is in focus throughout",
        ],
    },
}


def analyze_image_quality(image_data: str, is_url: bool = False) -> Dict[str, Any]:
    """
    Analyze image quality to determine if it's suitable for grading.
    
    Returns quality metrics and recommendations for improvement.
    """
    quality_result = {
        "is_suitable": True,
        "quality_score": 100,
        "issues": [],
        "recommendations": [],
        "metrics": {},
    }
    
    if not PIL_AVAILABLE:
        quality_result["warning"] = "PIL not available - basic quality check only"
        return quality_result
    
    try:
        # Load image
        if is_url:
            import requests
            response = requests.get(image_data, timeout=10)
            img = Image.open(io.BytesIO(response.content))
        else:
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        quality_result["metrics"]["width"] = width
        quality_result["metrics"]["height"] = height
        quality_result["metrics"]["aspect_ratio"] = round(width / height, 3)
        
        # Check resolution
        if width < IDEAL_SPECS["min_width"] or height < IDEAL_SPECS["min_height"]:
            quality_result["issues"].append("Resolution too low")
            quality_result["recommendations"].append(
                f"Increase resolution to at least {IDEAL_SPECS['min_width']}x{IDEAL_SPECS['min_height']} pixels"
            )
            quality_result["quality_score"] -= 25
        elif width < IDEAL_SPECS["ideal_width"] or height < IDEAL_SPECS["ideal_height"]:
            quality_result["recommendations"].append(
                f"For best results, use {IDEAL_SPECS['ideal_width']}x{IDEAL_SPECS['ideal_height']} pixels"
            )
            quality_result["quality_score"] -= 10
        
        # Check aspect ratio (should be close to card ratio)
        aspect_ratio = width / height
        expected_ratio = IDEAL_SPECS["card_aspect_ratio"]
        if abs(aspect_ratio - expected_ratio) > IDEAL_SPECS["aspect_tolerance"]:
            # Card might be rotated or not filling frame properly
            if abs((1/aspect_ratio) - expected_ratio) < IDEAL_SPECS["aspect_tolerance"]:
                quality_result["recommendations"].append("Consider rotating image 90 degrees")
            else:
                quality_result["issues"].append("Card not filling frame properly")
                quality_result["recommendations"].append("Position card to fill 70-80% of the frame")
                quality_result["quality_score"] -= 15
        
        # Analyze brightness
        stat = ImageStat.Stat(img)
        brightness = sum(stat.mean) / 3
        quality_result["metrics"]["brightness"] = round(brightness, 1)
        
        if brightness < IDEAL_SPECS["min_brightness"]:
            quality_result["issues"].append("Image too dark")
            quality_result["recommendations"].append("Increase lighting or camera exposure")
            quality_result["quality_score"] -= 20
        elif brightness > IDEAL_SPECS["max_brightness"]:
            quality_result["issues"].append("Image too bright/overexposed")
            quality_result["recommendations"].append("Reduce lighting or camera exposure")
            quality_result["quality_score"] -= 20
        
        # Analyze contrast
        contrast = max(stat.stddev)
        quality_result["metrics"]["contrast"] = round(contrast, 1)
        
        if contrast < IDEAL_SPECS["min_contrast"]:
            quality_result["issues"].append("Low contrast - image may be washed out")
            quality_result["recommendations"].append("Adjust lighting for better contrast")
            quality_result["quality_score"] -= 15
        
        # Check for blur (Laplacian variance)
        if NUMPY_AVAILABLE:
            gray = img.convert('L')
            # Apply Laplacian filter
            laplacian = gray.filter(ImageFilter.FIND_EDGES)
            laplacian_var = ImageStat.Stat(laplacian).var[0]
            quality_result["metrics"]["sharpness"] = round(laplacian_var, 1)
            
            if laplacian_var < IDEAL_SPECS["blur_threshold"]:
                quality_result["issues"].append("Image appears blurry")
                quality_result["recommendations"].append(
                    "Ensure camera is steady and card is in focus. Use a tripod if possible."
                )
                quality_result["quality_score"] -= 30
        
        # Check for potential glare (very bright spots)
        if NUMPY_AVAILABLE:
            img_array = np.array(img)
            bright_pixels = np.sum(img_array > 250) / img_array.size
            quality_result["metrics"]["glare_percentage"] = round(bright_pixels * 100, 2)
            
            if bright_pixels > 0.05:  # More than 5% very bright pixels
                quality_result["issues"].append("Possible glare detected")
                quality_result["recommendations"].append(
                    "Adjust lighting angle to reduce reflections, especially on holofoil"
                )
                quality_result["quality_score"] -= 15
        
        # Determine if suitable
        quality_result["quality_score"] = max(0, quality_result["quality_score"])
        quality_result["is_suitable"] = quality_result["quality_score"] >= 60
        
        # Quality rating
        score = quality_result["quality_score"]
        if score >= 90:
            quality_result["rating"] = "Excellent"
        elif score >= 75:
            quality_result["rating"] = "Good"
        elif score >= 60:
            quality_result["rating"] = "Acceptable"
        elif score >= 40:
            quality_result["rating"] = "Poor"
        else:
            quality_result["rating"] = "Unusable"
        
    except Exception as e:
        quality_result["error"] = str(e)
        quality_result["is_suitable"] = False
        quality_result["quality_score"] = 0
    
    return quality_result


def get_photo_template(side: str = "front") -> Dict[str, Any]:
    """
    Get the photo template/guide for taking card photos.
    
    Args:
        side: "front" or "back"
    
    Returns:
        Template with instructions, checklist, and ideal specifications
    """
    template = PHOTO_TEMPLATE.get(side, PHOTO_TEMPLATE["front"]).copy()
    template["ideal_specs"] = {
        "resolution": f"{IDEAL_SPECS['ideal_width']}x{IDEAL_SPECS['ideal_height']} pixels",
        "min_resolution": f"{IDEAL_SPECS['min_width']}x{IDEAL_SPECS['min_height']} pixels",
        "file_format": "JPEG or PNG",
        "max_file_size": f"{IDEAL_SPECS['max_file_size_mb']} MB",
        "lighting": "Even, diffused lighting from above",
        "background": "Dark, non-reflective surface (black felt ideal)",
        "camera_position": "Directly above card, parallel to surface",
        "fill_frame": "Card should fill 70-80% of the image",
    }
    template["tips"] = [
        "Use natural daylight or soft white LEDs",
        "Avoid direct sunlight or harsh overhead lights",
        "Turn off camera flash",
        "Use a phone stand or tripod for stability",
        "Clean the card gently before photographing",
        "Take multiple photos and choose the best one",
    ]
    return template


def validate_card_photos(
    front_image: str,
    back_image: str = None,
    front_is_url: bool = False,
    back_is_url: bool = False,
) -> Dict[str, Any]:
    """
    Validate front and back card photos for grading.
    
    Returns validation results for both images with combined suitability.
    """
    result = {
        "front": analyze_image_quality(front_image, front_is_url),
        "back": None,
        "combined_suitable": False,
        "combined_score": 0,
        "ready_for_grading": False,
    }
    
    if back_image:
        result["back"] = analyze_image_quality(back_image, back_is_url)
        # Combined score is weighted average (front matters more for grading)
        result["combined_score"] = int(
            result["front"]["quality_score"] * 0.7 +
            result["back"]["quality_score"] * 0.3
        )
        result["combined_suitable"] = (
            result["front"]["is_suitable"] and
            result["back"]["is_suitable"]
        )
    else:
        result["combined_score"] = result["front"]["quality_score"]
        result["combined_suitable"] = result["front"]["is_suitable"]
        result["back_missing"] = True
        result["recommendations"] = ["Provide back image for complete grading analysis"]
    
    result["ready_for_grading"] = result["combined_suitable"]
    
    return result


def generate_image_hash(image_data: str) -> str:
    """Generate a hash for image caching."""
    return hashlib.md5(image_data.encode()).hexdigest()[:16]


# =============================================================================
# IMAGE CACHE
# =============================================================================

_grading_cache: Dict[str, Dict] = {}

def get_cached_grade(image_hash: str) -> Optional[Dict]:
    """Get cached grading result if available."""
    return _grading_cache.get(image_hash)

def cache_grade(image_hash: str, result: Dict):
    """Cache a grading result."""
    _grading_cache[image_hash] = {
        "result": result,
        "cached_at": datetime.now().isoformat(),
    }
    # Limit cache size
    if len(_grading_cache) > 100:
        oldest = min(_grading_cache.keys(), key=lambda k: _grading_cache[k]["cached_at"])
        del _grading_cache[oldest]


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
    back_image_data: Optional[str] = None,
    back_image_url: Optional[str] = None,
    raw_value: float = 10.0,
    card_name: Optional[str] = None,
    validate_quality: bool = True,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Main grading function with image quality validation.
    
    Args:
        image_data: Base64-encoded front image data
        image_url: URL to front card image
        back_image_data: Base64-encoded back image data (optional)
        back_image_url: URL to back card image (optional)
        raw_value: Estimated raw (ungraded) card value
        card_name: Optional card name for reference
        validate_quality: Whether to check image quality first
        use_cache: Whether to use cached results
    
    Returns:
        Complete grading analysis with predicted grades and values
    """
    
    # No image provided - return template/standards info
    if not image_url and not image_data:
        return {
            "success": True,
            "mode": "template",
            "message": "No image provided. Here's how to take perfect photos for grading.",
            "photo_template": {
                "front": get_photo_template("front"),
                "back": get_photo_template("back"),
            },
            "grading_standards": {
                "PSA": {k: {"name": v["name"], "description": v["description"]} 
                       for k, v in PSA_GRADES.items()},
                "criteria": GRADING_CRITERIA,
                "pokemon_specific": POKEMON_SPECIFIC,
            },
        }
    
    # Determine front image source
    front_is_url = bool(image_url)
    front_image = image_url or image_data
    
    # Check cache first
    if use_cache:
        image_hash = generate_image_hash(front_image)
        cached = get_cached_grade(image_hash)
        if cached:
            result = cached["result"].copy()
            result["from_cache"] = True
            result["cached_at"] = cached["cached_at"]
            return result
    
    # Validate image quality if requested
    quality_result = None
    if validate_quality:
        # Validate front image
        quality_result = analyze_image_quality(front_image, front_is_url)
        
        # If back image provided, validate it too
        if back_image_data or back_image_url:
            back_is_url = bool(back_image_url)
            back_image = back_image_url or back_image_data
            back_quality = analyze_image_quality(back_image, back_is_url)
            quality_result = {
                "front": quality_result,
                "back": back_quality,
                "combined_score": int(quality_result["quality_score"] * 0.7 + back_quality["quality_score"] * 0.3),
                "ready_for_grading": quality_result["is_suitable"] and back_quality["is_suitable"],
            }
        
        # If image quality is too poor, return early with recommendations
        front_quality = quality_result.get("front", quality_result) if isinstance(quality_result.get("front"), dict) else quality_result
        if not front_quality.get("is_suitable", True):
            return {
                "success": False,
                "mode": "quality_check_failed",
                "message": "Image quality is insufficient for accurate grading",
                "image_quality": quality_result,
                "photo_template": get_photo_template("front"),
                "recommendations": front_quality.get("recommendations", []),
            }
    
    # Analyze front image with AI
    analysis = analyze_image_with_ai(front_image, is_url=front_is_url)
    
    # Analyze back image if provided
    back_analysis = None
    if back_image_data or back_image_url:
        back_is_url = bool(back_image_url)
        back_image = back_image_url or back_image_data
        back_analysis = analyze_image_with_ai(back_image, is_url=back_is_url)
    
    # Calculate values
    predicted_grades = analysis.get("predicted_grades", {"PSA": 7, "CGC": 7, "BGS": 7})
    
    # Adjust grades based on back if available
    if back_analysis:
        back_grades = back_analysis.get("predicted_grades", {})
        # Back centering can affect PSA grade significantly
        if back_grades:
            for company in predicted_grades:
                if company in back_grades:
                    # Use the lower of front/back grades (worst case)
                    predicted_grades[company] = min(
                        predicted_grades[company],
                        back_grades.get(company, predicted_grades[company])
                    )
    
    value_analysis = calculate_estimated_value(raw_value, predicted_grades)
    
    result = {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "card_name": card_name or analysis.get("card_identified", "Unknown"),
        "card_type": analysis.get("card_type", "unknown"),
        
        # Image quality (if validated)
        "image_quality": quality_result,
        
        # Subgrades
        "subgrades": {
            "front": analysis.get("subgrades", {}),
            "back": back_analysis.get("subgrades", {}) if back_analysis else None,
        },
        "centering_estimate": {
            "front": analysis.get("centering_estimate", "unknown"),
            "back": back_analysis.get("centering_estimate", "unknown") if back_analysis else None,
        },
        
        # Defects
        "defects_found": {
            "front": analysis.get("defects_found", []),
            "back": back_analysis.get("defects_found", []) if back_analysis else [],
        },
        "defect_count": len(analysis.get("defects_found", [])) + (
            len(back_analysis.get("defects_found", [])) if back_analysis else 0
        ),
        
        # Predicted grades
        "predicted_grades": predicted_grades,
        "grade_confidence": analysis.get("grade_confidence", 0.5),
        
        # Value analysis
        "value_analysis": value_analysis,
        "worth_grading": value_analysis.get("recommendation", {}).get("roi_percent", 0) > 20,
        
        # Notes
        "notes": analysis.get("notes", ""),
        "recommendations": analysis.get("recommendations", ""),
        
        # Analysis details
        "front_analysis": analysis,
        "back_analysis": back_analysis,
        "has_back_image": back_analysis is not None,
        
        # Grading criteria reference
        "grading_criteria_used": list(GRADING_CRITERIA.keys()),
        
        # Demo mode flag
        "demo_mode": analysis.get("demo_mode", False),
    }
    
    # Cache result
    if use_cache:
        cache_grade(image_hash, result)
    
    return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def check_image_quality(image_data: str = None, image_url: str = None) -> Dict[str, Any]:
    """Quick check if an image is suitable for grading."""
    if image_url:
        return analyze_image_quality(image_url, is_url=True)
    elif image_data:
        return analyze_image_quality(image_data, is_url=False)
    else:
        return {"error": "No image provided"}


def get_grading_template() -> Dict[str, Any]:
    """Get the complete photo template for both front and back."""
    return {
        "front": get_photo_template("front"),
        "back": get_photo_template("back"),
        "ideal_specs": IDEAL_SPECS,
    }


# =============================================================================
# MAIN - Handle stdin JSON or command line
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Card Grading Tool")
    parser.add_argument("--template", action="store_true", help="Get photo template/guide")
    parser.add_argument("--check-quality", action="store_true", help="Check image quality only")
    parser.add_argument("--image-url", help="URL to front card image")
    parser.add_argument("--back-url", help="URL to back card image")
    parser.add_argument("--value", type=float, default=10.0, help="Raw card value estimate")
    parser.add_argument("--name", help="Card name")
    parser.add_argument("--no-validate", action="store_true", help="Skip quality validation")
    parser.add_argument("--no-cache", action="store_true", help="Don't use cache")
    
    args = parser.parse_args()
    
    # Template mode
    if args.template:
        print(json.dumps(get_grading_template(), indent=2))
        sys.exit(0)
    
    # Read from stdin if available
    input_data = ""
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
    
    try:
        data = json.loads(input_data) if input_data.strip() else {}
    except json.JSONDecodeError:
        data = {}
    
    # Extract parameters (CLI args override JSON)
    image_data = data.get("image_data") or data.get("image_base64")
    image_url = args.image_url or data.get("image_url")
    back_image_data = data.get("back_image_data") or data.get("back_image_base64")
    back_image_url = args.back_url or data.get("back_image_url")
    raw_value = args.value or float(data.get("raw_value", 10.0))
    card_name = args.name or data.get("card_name")
    
    # Quality check only mode
    if args.check_quality:
        result = check_image_quality(image_data, image_url)
        print(json.dumps(result, indent=2))
        sys.exit(0)
    
    # Run grading
    result = grade_card(
        image_data=image_data,
        image_url=image_url,
        back_image_data=back_image_data,
        back_image_url=back_image_url,
        raw_value=raw_value,
        card_name=card_name,
        validate_quality=not args.no_validate,
        use_cache=not args.no_cache,
    )
    
    print(json.dumps(result, indent=2))
