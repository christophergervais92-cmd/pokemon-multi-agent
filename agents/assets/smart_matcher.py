#!/usr/bin/env python3
"""
Smart Asset Matcher

Matches video clips to scripts based on keywords and context.
"""
import re
from typing import Dict, List, Optional
from collections import Counter

from agents.assets.asset_manager import AssetManager
from agents.utils.logger import get_logger

logger = get_logger("smart_matcher")


class SmartMatcher:
    """
    Intelligent asset matching based on script content.
    
    Features:
    - Keyword extraction from scripts
    - Context-aware clip selection
    - Duration-based matching
    - Diversity balancing (avoid repetition)
    """
    
    def __init__(self, asset_manager: Optional[AssetManager] = None):
        """
        Initialize smart matcher.
        
        Args:
            asset_manager: AssetManager instance (creates new if None)
        """
        self.asset_manager = asset_manager or AssetManager()
        logger.info("Smart matcher initialized")
    
    def match_assets(
        self,
        script: str,
        keywords: List[str],
        location: Optional[str] = None,
        target_duration: float = 30.0,
        min_clips: int = 3,
        max_clips: int = 7
    ) -> List[Dict]:
        """
        Match video assets to script content.
        
        Args:
            script: Video script text
            keywords: Extracted keywords
            location: Specific location to match
            target_duration: Target total duration in seconds
            min_clips: Minimum number of clips
            max_clips: Maximum number of clips
        
        Returns:
            List of matched asset dictionaries with scores
        """
        logger.info(f"Matching assets for {location or 'any location'}")
        
        # Extract additional keywords from script
        script_keywords = self._extract_keywords(script)
        all_keywords = list(set(keywords + script_keywords))
        
        logger.debug(f"Keywords: {all_keywords}")
        
        # Search for matching assets
        candidates = self.asset_manager.search_assets(
            location=location,
            tags=all_keywords,
            min_duration=3.0,  # At least 3 seconds
            limit=100
        )
        
        if not candidates:
            # Fallback: get any assets from location
            logger.warning(f"No keyword matches, using location fallback")
            candidates = self.asset_manager.search_assets(
                location=location,
                min_duration=3.0,
                limit=100
            )
        
        if not candidates:
            # Final fallback: get any assets
            logger.warning("No location matches, using random fallback")
            candidates = self.asset_manager.search_assets(
                min_duration=3.0,
                limit=100
            )
        
        if not candidates:
            logger.error("No assets found in database!")
            return []
        
        # Score each asset
        scored_assets = []
        for asset in candidates:
            score = self._score_asset(asset, all_keywords, location)
            scored_assets.append({
                'asset': asset,
                'score': score
            })
        
        # Sort by score (descending)
        scored_assets.sort(key=lambda x: x['score'], reverse=True)
        
        # Select clips to match target duration
        selected = self._select_clips(
            scored_assets,
            target_duration,
            min_clips,
            max_clips
        )
        
        logger.info(f"Matched {len(selected)} clips totaling ~{target_duration}s")
        
        return selected
    
    def _extract_keywords(self, script: str) -> List[str]:
        """Extract keywords from script text."""
        keywords = []
        
        # Convert to lowercase
        text = script.lower()
        
        # Location keywords
        locations = ['mongolia', 'nepal', 'papua new guinea', 'altai', 'kathmandu', 'himalayas']
        for loc in locations:
            if loc in text:
                keywords.append(loc)
        
        # Activity keywords
        activities = [
            'hunting', 'hunt', 'eagle', 'falcon', 'bird',
            'festival', 'celebrate', 'celebration', 'ceremony',
            'cooking', 'cook', 'food', 'meal', 'fire',
            'dancing', 'dance', 'music', 'sing', 'singing',
            'craft', 'weaving', 'making', 'building',
            'traditional', 'ancient', 'sacred', 'ritual',
            'family', 'village', 'community', 'tribe',
            'mountain', 'valley', 'river', 'forest', 'nature',
            'horse', 'yak', 'animal', 'livestock',
            'clothing', 'costume', 'dress', 'wear'
        ]
        
        for activity in activities:
            if activity in text:
                keywords.append(activity)
        
        # Return unique keywords
        return list(set(keywords))
    
    def _score_asset(self, asset: Dict, keywords: List[str], location: Optional[str]) -> float:
        """
        Score asset based on relevance.
        
        Scoring factors:
        - Location match: +10
        - Keyword matches: +5 per match
        - Low usage count: +3
        - Good duration (5-15s): +2
        """
        score = 0.0
        
        # Location match
        if location and asset.get('location') == location:
            score += 10.0
        
        # Keyword matches
        asset_tags = set(t.lower() for t in asset.get('tags', []))
        keyword_set = set(k.lower() for k in keywords)
        matches = asset_tags.intersection(keyword_set)
        score += len(matches) * 5.0
        
        # Prefer less-used assets (for diversity)
        usage_count = asset.get('usage_count', 0)
        if usage_count == 0:
            score += 3.0
        elif usage_count < 5:
            score += 2.0
        
        # Prefer medium-length clips (easier to work with)
        duration = asset.get('duration')
        if duration:
            if 5.0 <= duration <= 15.0:
                score += 2.0
            elif 3.0 <= duration < 5.0:
                score += 1.0
        
        return score
    
    def _select_clips(
        self,
        scored_assets: List[Dict],
        target_duration: float,
        min_clips: int,
        max_clips: int
    ) -> List[Dict]:
        """
        Select optimal set of clips to match target duration.
        
        Strategy:
        1. Start with highest-scored clips
        2. Balance total duration close to target
        3. Ensure minimum diversity
        """
        selected = []
        total_duration = 0.0
        
        for item in scored_assets:
            asset = item['asset']
            duration = asset.get('duration', 5.0) or 5.0  # Default 5s if unknown
            
            # Stop if we have enough clips and duration
            if len(selected) >= min_clips and total_duration >= target_duration * 0.9:
                break
            
            # Don't exceed max clips
            if len(selected) >= max_clips:
                break
            
            # Don't go way over target duration (unless we're below min_clips)
            if len(selected) >= min_clips and total_duration + duration > target_duration * 1.5:
                # Try to find a shorter clip
                continue
            
            selected.append({
                'id': asset['id'],
                'filename': asset['filename'],
                'filepath': asset['filepath'],
                'duration': duration,
                'location': asset.get('location'),
                'tags': asset.get('tags', []),
                'score': item['score']
            })
            
            total_duration += duration
        
        # If we don't have minimum clips, add more
        if len(selected) < min_clips:
            remaining = [item for item in scored_assets 
                        if item['asset']['id'] not in [s['id'] for s in selected]]
            
            for item in remaining[:min_clips - len(selected)]:
                asset = item['asset']
                duration = asset.get('duration', 5.0) or 5.0
                
                selected.append({
                    'id': asset['id'],
                    'filename': asset['filename'],
                    'filepath': asset['filepath'],
                    'duration': duration,
                    'location': asset.get('location'),
                    'tags': asset.get('tags', []),
                    'score': item['score']
                })
                
                total_duration += duration
        
        logger.info(f"Selected {len(selected)} clips, total duration: {total_duration:.1f}s")
        
        return selected
    
    def match_for_topic(self, topic_data: Dict) -> List[Dict]:
        """
        Convenience method to match assets for a topic.
        
        Args:
            topic_data: Dictionary from TopicGenerator
        
        Returns:
            List of matched assets
        """
        return self.match_assets(
            script=topic_data.get('script', ''),
            keywords=topic_data.get('keywords', []),
            location=topic_data.get('location'),
            target_duration=topic_data.get('duration', 30.0)
        )


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    import json
    
    matcher = SmartMatcher()
    
    # Test script
    script = """Watch this! In Mongolia's Altai Mountains, eagle hunters train golden eagles 
    to hunt foxes and rabbits. This tradition dates back 4,000 years. Follow for more!"""
    
    keywords = ['mongolia', 'hunting', 'eagle', 'traditional', 'mountains']
    
    # Match assets
    matches = matcher.match_assets(
        script=script,
        keywords=keywords,
        location='Mongolia',
        target_duration=30.0
    )
    
    print(f"\nMatched {len(matches)} clips:")
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match['filename']} ({match['duration']:.1f}s) - Score: {match['score']:.1f}")
        print(f"   Tags: {', '.join(match['tags'])}")
