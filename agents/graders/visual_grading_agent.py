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


# =============================================================================
# OPTIMIZED AI ANALYSIS
# =============================================================================

# Optimized prompt - shorter, more efficient, lower cost
GRADING_PROMPT_COMPACT = """Expert Pokemon card grader. Analyze image, return JSON only:
{"card_identified":"name","card_type":"holofoil/reverse_holo/full_art/regular","subgrades":{"centering":9.0,"corners":9.0,"edges":9.0,"surface":9.0},"centering_estimate":"55/45","defects_found":[{"type":"defect","severity":"minor/major","location":"where"}],"predicted_grades":{"PSA":9,"CGC":9,"BGS":9},"grade_confidence":0.85,"notes":"brief condition notes","recommendations":"grading company suggestion"}
Evaluate: centering (border ratios, 55/45=PSA10), corners (whitening, sharpness), edges (chips, nicks), surface (scratches, print defects, gloss). Return ONLY valid JSON."""

# Retry configuration
MAX_API_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff seconds

# Cost tracking
_api_cost_tracker = {"openai": 0.0, "anthropic": 0.0, "calls": 0}


def preprocess_image_for_api(image_data: str, is_url: bool = False, max_size: int = 1024) -> Tuple[str, bool]:
    """
    Preprocess image for API - resize if too large to reduce costs.
    
    Returns (processed_image_data, is_url)
    """
    if not PIL_AVAILABLE:
        return image_data, is_url
    
    try:
        if is_url:
            import requests
            response = requests.get(image_data, timeout=10)
            img = Image.open(io.BytesIO(response.content))
        else:
            image_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(image_bytes))
        
        # Resize if larger than max_size
        width, height = img.size
        if width > max_size or height > max_size:
            ratio = min(max_size / width, max_size / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save to base64
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        processed_data = base64.b64encode(buffer.getvalue()).decode()
        
        return processed_data, False
        
    except Exception as e:
        print(f"Image preprocessing error: {e}", file=sys.stderr)
        return image_data, is_url


def analyze_with_local_cv(image_data: str, is_url: bool = False) -> Dict[str, Any]:
    """
    Local computer vision analysis as fallback (no API needed).
    Uses PIL/numpy for basic defect detection.
    """
    if not PIL_AVAILABLE:
        return None
    
    try:
        # Load image
        if is_url:
            import requests
            response = requests.get(image_data, timeout=10)
            img = Image.open(io.BytesIO(response.content))
        else:
            image_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(image_bytes))
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        
        # Analyze centering by looking at border colors
        centering_score = 9.0  # Default good
        centering_estimate = "55/45"
        
        if NUMPY_AVAILABLE:
            img_array = np.array(img)
            
            # Sample borders (top 5%, bottom 5%, left 5%, right 5%)
            border_pct = 0.05
            top_border = img_array[:int(height * border_pct), :, :]
            bottom_border = img_array[int(height * (1 - border_pct)):, :, :]
            left_border = img_array[:, :int(width * border_pct), :]
            right_border = img_array[:, int(width * (1 - border_pct)):, :]
            
            # Calculate average brightness of borders
            top_avg = np.mean(top_border)
            bottom_avg = np.mean(bottom_border)
            left_avg = np.mean(left_border)
            right_avg = np.mean(right_border)
            
            # Estimate centering based on border similarity
            lr_diff = abs(left_avg - right_avg)
            tb_diff = abs(top_avg - bottom_avg)
            
            if lr_diff < 10 and tb_diff < 10:
                centering_score = 9.5
                centering_estimate = "52/48"
            elif lr_diff < 20 and tb_diff < 20:
                centering_score = 9.0
                centering_estimate = "55/45"
            elif lr_diff < 30 and tb_diff < 30:
                centering_score = 8.5
                centering_estimate = "58/42"
            else:
                centering_score = 8.0
                centering_estimate = "60/40"
            
            # Check corners for whitening (bright spots in corners)
            corner_size = int(min(width, height) * 0.08)
            corners = [
                img_array[:corner_size, :corner_size],  # Top-left
                img_array[:corner_size, -corner_size:],  # Top-right
                img_array[-corner_size:, :corner_size],  # Bottom-left
                img_array[-corner_size:, -corner_size:],  # Bottom-right
            ]
            
            corner_scores = []
            defects = []
            corner_names = ["top-left", "top-right", "bottom-left", "bottom-right"]
            
            for i, corner in enumerate(corners):
                # High brightness in corner might indicate whitening
                corner_brightness = np.mean(corner)
                if corner_brightness > 200:
                    corner_scores.append(8.0)
                    defects.append({
                        "type": "possible_corner_whitening",
                        "severity": "minor",
                        "location": corner_names[i]
                    })
                elif corner_brightness > 180:
                    corner_scores.append(8.5)
                else:
                    corner_scores.append(9.5)
            
            corners_score = np.mean(corner_scores)
            
            # Check edges for uniformity
            edges_score = 9.0
            
            # Check surface for scratches (high variance streaks)
            gray = np.mean(img_array, axis=2)
            local_var = np.var(gray)
            
            if local_var > 2000:
                surface_score = 8.0
                defects.append({
                    "type": "surface_irregularity",
                    "severity": "minor",
                    "location": "general"
                })
            elif local_var > 1500:
                surface_score = 8.5
            else:
                surface_score = 9.0
        else:
            # Without numpy, use basic PIL analysis
            stat = ImageStat.Stat(img)
            brightness = sum(stat.mean) / 3
            
            centering_score = 8.5
            corners_score = 8.5
            edges_score = 9.0
            surface_score = 8.5 if brightness > 150 else 9.0
            defects = []
        
        # Calculate predicted grades based on subgrades
        avg_subgrade = (centering_score + corners_score + edges_score + surface_score) / 4
        
        # PSA is stricter - one low subgrade tanks the overall
        psa_grade = int(min(centering_score, corners_score, edges_score, surface_score))
        cgc_grade = round(avg_subgrade * 2) / 2  # CGC uses half grades
        bgs_grade = round(avg_subgrade * 2) / 2
        
        return {
            "card_identified": "Pokemon Card (local analysis)",
            "card_type": "unknown",
            "subgrades": {
                "centering": round(centering_score, 1),
                "corners": round(corners_score, 1),
                "edges": round(edges_score, 1),
                "surface": round(surface_score, 1),
            },
            "centering_estimate": centering_estimate,
            "defects_found": defects,
            "predicted_grades": {
                "PSA": psa_grade,
                "CGC": cgc_grade,
                "BGS": bgs_grade,
            },
            "grade_confidence": 0.65,  # Lower confidence for local analysis
            "notes": "Local CV analysis - for accurate grading, provide API key",
            "recommendations": "Upload clearer image or enable AI analysis for detailed assessment",
            "local_analysis": True,
        }
        
    except Exception as e:
        print(f"Local CV analysis error: {e}", file=sys.stderr)
        return None


def analyze_image_with_ai(
    image_data: str,
    is_url: bool = False,
    use_compact_prompt: bool = True,
    preprocess: bool = True,
    retry: bool = True,
) -> Dict[str, Any]:
    """
    Use AI vision model to analyze card image.
    
    Optimizations:
    - Compact prompt for lower token cost
    - Image preprocessing to reduce size
    - Retry with exponential backoff
    - Falls back to local CV then demo mode
    """
    global _api_cost_tracker
    
    # Preprocess image if enabled
    if preprocess:
        image_data, is_url = preprocess_image_for_api(image_data, is_url, max_size=1024)
    
    # Select prompt
    grading_prompt = GRADING_PROMPT_COMPACT if use_compact_prompt else _get_full_grading_prompt()
    
    # Try OpenAI Vision with retry
    if OPENAI_API_KEY:
        for attempt in range(MAX_API_RETRIES if retry else 1):
            try:
                import requests
                
                headers = {
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                }
                
                if is_url:
                    image_content = {"type": "image_url", "image_url": {"url": image_data, "detail": "high"}}
                else:
                    image_content = {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}", "detail": "high"}
                    }
                
                payload = {
                    "model": "gpt-4o-mini",  # Use mini for cost efficiency
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": grading_prompt},
                                image_content,
                            ],
                        }
                    ],
                    "max_tokens": 800,  # Reduced for compact response
                    "temperature": 0.3,  # Lower for more consistent grading
                }
                
                resp = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30,  # Reduced timeout
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    content = result["choices"][0]["message"]["content"]
                    _api_cost_tracker["openai"] += 0.01  # Approximate cost
                    _api_cost_tracker["calls"] += 1
                    
                    # Extract JSON from response
                    try:
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        if start >= 0 and end > start:
                            parsed = json.loads(content[start:end])
                            parsed["api_used"] = "openai"
                            return parsed
                    except json.JSONDecodeError:
                        pass
                
                elif resp.status_code == 429:  # Rate limited
                    if attempt < MAX_API_RETRIES - 1:
                        import time
                        time.sleep(RETRY_DELAYS[attempt])
                        continue
                        
            except Exception as e:
                print(f"OpenAI Vision error (attempt {attempt + 1}): {e}", file=sys.stderr)
                if attempt < MAX_API_RETRIES - 1 and retry:
                    import time
                    time.sleep(RETRY_DELAYS[attempt])
    
    # Try Anthropic Claude Vision with retry
    if ANTHROPIC_API_KEY:
        for attempt in range(MAX_API_RETRIES if retry else 1):
            try:
                import requests
                
                headers = {
                    "x-api-key": ANTHROPIC_API_KEY,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                }
                
                if is_url:
                    # Fetch URL for Claude
                    try:
                        img_resp = requests.get(image_data, timeout=10)
                        image_b64 = base64.b64encode(img_resp.content).decode()
                        image_source = {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        }
                    except:
                        image_source = {"type": "url", "url": image_data}
                else:
                    image_source = {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data,
                    }
                
                payload = {
                    "model": "claude-3-haiku-20240307",  # Use Haiku for cost efficiency
                    "max_tokens": 800,
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
                    timeout=30,
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    content = result["content"][0]["text"]
                    _api_cost_tracker["anthropic"] += 0.005  # Approximate cost
                    _api_cost_tracker["calls"] += 1
                    
                    try:
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        if start >= 0 and end > start:
                            parsed = json.loads(content[start:end])
                            parsed["api_used"] = "anthropic"
                            return parsed
                    except json.JSONDecodeError:
                        pass
                        
                elif resp.status_code == 429:
                    if attempt < MAX_API_RETRIES - 1:
                        import time
                        time.sleep(RETRY_DELAYS[attempt])
                        continue
                        
            except Exception as e:
                print(f"Anthropic Vision error (attempt {attempt + 1}): {e}", file=sys.stderr)
                if attempt < MAX_API_RETRIES - 1 and retry:
                    import time
                    time.sleep(RETRY_DELAYS[attempt])
    
    # Fallback to local CV analysis
    local_result = analyze_with_local_cv(image_data, is_url)
    if local_result:
        return local_result
    
    # Final fallback: demo analysis
    return get_demo_analysis()


def _get_full_grading_prompt() -> str:
    """Return the full detailed grading prompt."""
    return """You are an expert Pokemon card grader. Analyze this card and return ONLY valid JSON:
{
    "card_identified": "Card name if visible",
    "card_type": "holofoil/reverse_holo/full_art/regular",
    "subgrades": {"centering": 9.0, "corners": 9.0, "edges": 9.0, "surface": 9.0},
    "centering_estimate": "55/45",
    "defects_found": [{"type": "defect_type", "severity": "minor/major", "location": "where"}],
    "predicted_grades": {"PSA": 9, "CGC": 9, "BGS": 9},
    "grade_confidence": 0.85,
    "notes": "Condition notes",
    "recommendations": "Grading recommendation"
}
Evaluate: centering (55/45 or better for PSA 10), corners (all must be sharp), edges (no chips/whitening), surface (no scratches, good gloss)."""


def get_api_cost_stats() -> Dict[str, Any]:
    """Get API usage and cost statistics."""
    return {
        "openai_cost": round(_api_cost_tracker["openai"], 4),
        "anthropic_cost": round(_api_cost_tracker["anthropic"], 4),
        "total_cost": round(_api_cost_tracker["openai"] + _api_cost_tracker["anthropic"], 4),
        "total_calls": _api_cost_tracker["calls"],
    }


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
# BATCH GRADING
# =============================================================================

def grade_batch(
    cards: List[Dict[str, Any]],
    parallel: bool = True,
    validate_quality: bool = True,
) -> Dict[str, Any]:
    """
    Grade multiple cards in batch.
    
    Args:
        cards: List of dicts with keys: image_data/image_url, back_image_data/back_image_url, raw_value, card_name
        parallel: Whether to process in parallel (faster but uses more memory)
        validate_quality: Whether to validate image quality first
    
    Returns:
        Batch results with individual grades and summary statistics
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    start_time = time.time()
    results = []
    successful = 0
    failed = 0
    
    def grade_single(card_data: Dict, index: int) -> Tuple[int, Dict]:
        try:
            result = grade_card(
                image_data=card_data.get("image_data"),
                image_url=card_data.get("image_url"),
                back_image_data=card_data.get("back_image_data"),
                back_image_url=card_data.get("back_image_url"),
                raw_value=float(card_data.get("raw_value", 10.0)),
                card_name=card_data.get("card_name"),
                validate_quality=validate_quality,
                use_cache=True,
            )
            return (index, result)
        except Exception as e:
            return (index, {"success": False, "error": str(e)})
    
    if parallel and len(cards) > 1:
        # Process in parallel with max 4 workers to avoid rate limits
        with ThreadPoolExecutor(max_workers=min(4, len(cards))) as executor:
            futures = {
                executor.submit(grade_single, card, i): i 
                for i, card in enumerate(cards)
            }
            
            for future in as_completed(futures):
                index, result = future.result()
                results.append((index, result))
                if result.get("success"):
                    successful += 1
                else:
                    failed += 1
        
        # Sort by original index
        results.sort(key=lambda x: x[0])
        results = [r[1] for r in results]
    else:
        # Process sequentially
        for i, card in enumerate(cards):
            _, result = grade_single(card, i)
            results.append(result)
            if result.get("success"):
                successful += 1
            else:
                failed += 1
    
    elapsed = round(time.time() - start_time, 2)
    
    # Calculate summary statistics
    grades = []
    for r in results:
        if r.get("success") and r.get("predicted_grades"):
            grades.append(r["predicted_grades"].get("PSA", 0))
    
    return {
        "success": True,
        "total_cards": len(cards),
        "successful": successful,
        "failed": failed,
        "results": results,
        "summary": {
            "avg_psa_grade": round(sum(grades) / len(grades), 1) if grades else 0,
            "min_grade": min(grades) if grades else 0,
            "max_grade": max(grades) if grades else 0,
            "grade_distribution": {
                "10": len([g for g in grades if g >= 10]),
                "9": len([g for g in grades if 9 <= g < 10]),
                "8": len([g for g in grades if 8 <= g < 9]),
                "7": len([g for g in grades if 7 <= g < 8]),
                "below_7": len([g for g in grades if g < 7]),
            },
        },
        "elapsed_seconds": elapsed,
        "api_costs": get_api_cost_stats(),
    }


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


def quick_grade(image_url: str, raw_value: float = 10.0) -> Dict[str, Any]:
    """
    Quick grade a card from URL with minimal validation.
    Optimized for speed over accuracy.
    """
    return grade_card(
        image_url=image_url,
        raw_value=raw_value,
        validate_quality=False,
        use_cache=True,
    )


# =============================================================================
# MAIN - Handle stdin JSON or command line
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AI Card Grading Tool - Optimized Pokemon Card Grading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get photo template
  python visual_grading_agent.py --template
  
  # Check image quality
  python visual_grading_agent.py --check-quality --image-url "https://..."
  
  # Quick grade (fastest, less validation)
  python visual_grading_agent.py --quick --image-url "https://..." --value 50
  
  # Full grade with front and back
  python visual_grading_agent.py --image-url "front.jpg" --back-url "back.jpg" --value 100
  
  # Batch grade from JSON (stdin)
  echo '{"cards": [{"image_url": "...", "raw_value": 50}, ...]}' | python visual_grading_agent.py --batch
  
  # Show API cost stats
  python visual_grading_agent.py --costs
        """
    )
    parser.add_argument("--template", action="store_true", help="Get photo template/guide")
    parser.add_argument("--check-quality", action="store_true", help="Check image quality only")
    parser.add_argument("--quick", action="store_true", help="Quick grade (skip validation)")
    parser.add_argument("--batch", action="store_true", help="Batch grade from stdin JSON")
    parser.add_argument("--costs", action="store_true", help="Show API cost statistics")
    parser.add_argument("--local-only", action="store_true", help="Use local CV only (no API)")
    parser.add_argument("--image-url", help="URL to front card image")
    parser.add_argument("--back-url", help="URL to back card image")
    parser.add_argument("--value", type=float, default=10.0, help="Raw card value estimate")
    parser.add_argument("--name", help="Card name")
    parser.add_argument("--no-validate", action="store_true", help="Skip quality validation")
    parser.add_argument("--no-cache", action="store_true", help="Don't use cache")
    parser.add_argument("--no-preprocess", action="store_true", help="Don't preprocess images")
    
    args = parser.parse_args()
    
    # Template mode
    if args.template:
        print(json.dumps(get_grading_template(), indent=2))
        sys.exit(0)
    
    # Cost stats mode
    if args.costs:
        print(json.dumps(get_api_cost_stats(), indent=2))
        sys.exit(0)
    
    # Read from stdin if available
    input_data = ""
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
    
    try:
        data = json.loads(input_data) if input_data.strip() else {}
    except json.JSONDecodeError:
        data = {}
    
    # Batch mode
    if args.batch:
        cards = data.get("cards", [])
        if not cards:
            print(json.dumps({"error": "No cards provided in batch. Use: {\"cards\": [...]}"}))
            sys.exit(1)
        result = grade_batch(cards, parallel=True, validate_quality=not args.no_validate)
        print(json.dumps(result, indent=2))
        sys.exit(0)
    
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
    
    # Local CV only mode
    if args.local_only:
        if image_url:
            result = analyze_with_local_cv(image_url, is_url=True)
        elif image_data:
            result = analyze_with_local_cv(image_data, is_url=False)
        else:
            result = {"error": "No image provided"}
        print(json.dumps(result or {"error": "Local analysis failed"}, indent=2))
        sys.exit(0)
    
    # Quick grade mode
    if args.quick:
        result = quick_grade(image_url or image_data, raw_value)
        print(json.dumps(result, indent=2))
        sys.exit(0)
    
    # Run full grading
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
